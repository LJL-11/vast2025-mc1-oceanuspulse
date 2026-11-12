<script setup>
import { computed, onMounted, ref, shallowRef } from 'vue'
import ChartPanel from '../components/ChartPanel.vue'
import AppIcon from '../components/AppIcon.vue'
import RecordPlate from '../components/RecordPlate.vue'
import JournalPager from '../components/JournalPager.vue'
import { CHART_GRID, CHART_MUTED, formatCount } from '../lib/palette'

const props = defineProps({
  dataUrl: {
    type: String,
    default: () => `${import.meta.env.BASE_URL}data/processed/rising_star.json`,
  },
})
const data = shallowRef(null)
const loading = ref(true)
const error = ref('')
const selectedAct = ref(null)
const careerMetric = ref('cumulative_works')
const validationCard = ref(null)

const COLORS = ['#236890', '#a86238', '#28817c']
const dimensions = [
  { key: 'mentor', label: '导师', color: '#2d719f' },
  { key: 'momentum', label: '动量', color: '#318b86' },
  { key: 'quality', label: '质量', color: '#b87842' },
  { key: 'collaboration', label: '合作', color: '#557c9b' },
  { key: 'influence', label: '影响力', color: '#ae665d' },
  { key: 'prestige', label: '厂牌', color: '#667c55' },
]
const careerMetrics = [
  { key: 'cumulative_works', label: '累计作品' },
  { key: 'cumulative_notable', label: '上榜作品' },
  { key: 'cumulative_hits', label: '已知年份登榜' },
]
const predictions = computed(() => data.value?.predictions ?? [])
const leaderboard = computed(() => (data.value?.leaderboard ?? []).slice(0, 12))
const candidate = computed(() => predictions.value.find(item => item.act_id === selectedAct.value) ?? predictions.value[0])
const comparison = computed(() => {
  const artists = data.value?.comparison ?? []
  if (!candidate.value?.timeline?.length) return artists
  const referenceId = predictions.value[0]?.act_id
  return artists.map(artist => artist.act_id === referenceId ? candidate.value : artist)
})
const meta = computed(() => data.value?.meta ?? {})
const validation = computed(() => data.value?.validation ?? {})
const cv = computed(() => validation.value.cross_validation ?? {})
const featureLabels = computed(() => new Map((data.value?.features ?? []).map(item => [item.key, item.label])))
const recordYears = computed(() => [...new Set(predictions.value.flatMap(
  item => (item.timeline ?? []).map(row => row.year),
))].sort((a, b) => a - b))
const recordPeak = computed(() => Math.max(1, ...predictions.value.flatMap(
  item => (item.timeline ?? []).map(row => row.works ?? 0),
)))
const recordCareerMax = computed(() => Math.max(1, ...predictions.value.flatMap(
  item => (item.timeline ?? []).map(row => row.cumulative_works ?? 0),
)))
const labelOf = key => featureLabels.value.get(key) ?? key

function decimal(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : '—'
}
function percent(value) {
  return Number.isFinite(value) ? (value * 100).toFixed(0) + '%' : '未计算'
}
function activeYears(item) {
  return item.debut === item.last_active ? item.debut + ' 年' : item.debut + '—' + item.last_active + ' 年'
}
function chooseCandidate(id) {
  if (predictions.value.some(item => item.act_id === id)) selectedAct.value = id
}
function openValidation() {
  if (!validationCard.value) return
  validationCard.value.open = true
  validationCard.value.scrollIntoView({ block: 'start' })
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(props.dataUrl)
    if (!response.ok) throw new Error('HTTP ' + response.status)
    data.value = await response.json()
    selectedAct.value = predictions.value[0]?.act_id ?? null
  } catch {
    error.value = '预测数据未就绪。请在仓库根目录运行 python pipeline/features.py，再重新加载。'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const trajectoryOption = computed(() => {
  const years = [...new Set(comparison.value.flatMap(artist => (artist.timeline ?? []).map(row => row.year)))].sort((a, b) => a - b)
  return {
    animationDuration: 250,
    color: COLORS,
    tooltip: { trigger: 'axis', renderMode: 'richText', confine: true },
    legend: { type: 'scroll', top: 0, textStyle: { color: CHART_MUTED, fontSize: 12 } },
    grid: { left: 42, right: 20, top: 44, bottom: 33 },
    xAxis: { type: 'category', data: years, axisLabel: { color: CHART_MUTED, fontSize: 12, hideOverlap: true }, axisTick: { show: false } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: CHART_MUTED, fontSize: 12 }, splitLine: { lineStyle: { color: CHART_GRID } } },
    series: comparison.value.map((artist, index) => {
      const yearly = new Map((artist.timeline ?? []).map(row => [row.year, row]))
      return {
        type: 'line', name: artist.name, step: 'end', showSymbol: true, symbolSize: 5,
        lineStyle: { width: 2.25 }, emphasis: { focus: 'series' },
        areaStyle: index === 0 ? { opacity: .095 } : undefined,
        data: years.map(year => yearly.get(year)?.[careerMetric.value] ?? null),
      }
    }),
  }
})

const radarOption = computed(() => ({
  animationDuration: 250,
  color: COLORS,
  tooltip: { renderMode: 'richText', confine: true },
  legend: { type: 'scroll', bottom: 0, textStyle: { color: CHART_MUTED, fontSize: 12 } },
  radar: {
    radius: '58%', center: ['50%', '47%'], splitNumber: 4,
    indicator: dimensions.map(dimension => ({ name: dimension.label, max: 100 })),
    axisName: { color: '#36536c', fontSize: 13 },
    splitLine: { lineStyle: { color: ['#cbdde9'] } },
    axisLine: { lineStyle: { color: '#cbdde9' } },
    splitArea: { areaStyle: { color: ['#f7fbfd', '#edf5fa'] } },
  },
  series: [{
    type: 'radar',
    data: predictions.value.map((item, index) => ({
      actId: item.act_id, name: item.name,
      value: dimensions.map(dimension => item.strength_percentiles?.[dimension.key] ?? null),
      symbolSize: item.act_id === selectedAct.value ? 6 : 3,
      lineStyle: { width: item.act_id === selectedAct.value ? 2.7 : 1.3, color: COLORS[index % COLORS.length] },
      itemStyle: { color: COLORS[index % COLORS.length] },
      areaStyle: { opacity: item.act_id === selectedAct.value ? .17 : .05 },
    })),
  }],
}))

const leaderboardOption = computed(() => {
  const rows = [...leaderboard.value].reverse()
  return {
    animationDuration: 220,
    tooltip: {
      trigger: 'axis', renderMode: 'richText', confine: true,
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const row = rows[params[0].dataIndex]
        return row.name + '\n综合分 ' + decimal(row.score) + '\n' + (row.had_hit ? '已有登榜记录' : '无登榜记录')
      },
    },
    grid: { left: 119, right: 42, top: 8, bottom: 23 },
    xAxis: { type: 'value', max: 100, splitLine: { lineStyle: { color: CHART_GRID } }, axisLabel: { color: CHART_MUTED, fontSize: 11 } },
    yAxis: {
      type: 'category', data: rows.map(row => row.name),
      axisLabel: { color: CHART_MUTED, fontSize: 12, width: 107, overflow: 'truncate', interval: 0 },
      axisLine: { show: false }, axisTick: { show: false },
    },
    series: [{
      type: 'bar', barMaxWidth: 12,
      data: rows.map(row => ({
        value: row.score, actId: row.act_id,
        itemStyle: { color: row.act_id === selectedAct.value ? '#236890' : row.had_hit ? '#c6d4de' : '#74a7bf', borderRadius: [0, 4, 4, 0] },
      })),
      label: { show: true, position: 'right', fontSize: 11, color: CHART_MUTED },
    }],
  }
})
</script>

<template>
  <div class="atlas-analysis atlas-rising">
    <div v-if="loading || error" class="op-state" :class="{ error }" role="status">
      <template v-if="error">{{ error }} <button type="button" class="atlas-button" @click="load">重新加载</button></template>
      <template v-else>正在读取候选档案…</template>
    </div>
    <template v-else>
      <header class="journal-opening">
        <span class="journal-folio" aria-label="第 03 章">03</span>
        <div class="journal-lede">
          <h1>Oceanus Folk 的下一代</h1>
          <p v-if="predictions.length"><strong>{{ predictions[0].name }}</strong> 以 {{ decimal(predictions[0].score) }} 分居首，在重采样中有 {{ percent(predictions[0].bootstrap_rank1_share) }} 排在首位。</p>
          <p v-else>依据观测截点以前的作品与合作记录比较候选。</p>
        </div>
        <aside class="journal-margin" aria-label="预测范围">
          <p><strong>{{ meta.snapshot_year }} 年</strong>观测截点</p>
          <p><strong>{{ formatCount(meta.reference_acts) }} 位</strong>Oceanus Folk 参照对象</p>
        </aside>
      </header>

      <section v-if="predictions.length" class="atlas-record-shelf" aria-labelledby="atlas-record-heading" data-visual>
        <header class="journal-figure-head">
          <h2 id="atlas-record-heading">候选唱片内页</h2>
          <p>外圈刻纹随年度作品量起伏。内圈每点是一格百分位，三页共用同一尺度。</p>
        </header>
        <div class="atlas-candidate-grid" role="group" aria-label="选择新星候选">
          <button v-for="(item, index) in predictions" :key="item.act_id" type="button" class="atlas-record" data-wave-surface
            :aria-pressed="item.act_id === selectedAct" :style="{ '--record-ink': COLORS[index % COLORS.length] }"
            @click="chooseCandidate(item.act_id)">
            <span class="atlas-record-name">
              <span class="atlas-record-rank">第 {{ item.rank }} 位</span>
              <strong>{{ item.name }}</strong>
              <span>{{ activeYears(item) }}有作品活动</span>
            </span>
            <RecordPlate :artist="item" :dimensions="dimensions" :years="recordYears"
              :yearly-max="recordPeak" :cumulative-max="recordCareerMax" />
            <span class="journal-record-footer">
              <span>重采样首位 <strong>{{ percent(item.bootstrap_rank1_share) }}</strong></span>
              <span>档案<AppIcon name="arrow" :size="15" /></span>
            </span>
          </button>
        </div>
        <div class="journal-record-weights" aria-label="综合分的六维权重">
          <span>评分权重</span>
          <span v-for="dimension in dimensions" :key="dimension.key">
            <i :style="{ background: dimension.color }" />{{ dimension.label }} {{ percent(meta.composite_weights?.[dimension.key]) }}
          </span>
        </div>
      </section>
      <p v-else class="op-state">当前模型结果没有可展示的候选。</p>

      <aside class="journal-model-band" aria-label="预测与回测说明">
        <div>
          <h2>预测如何读</h2>
          <p>综合分是六维百分位的加权比较。重采样首位比例衡量排名稳定性，未来五年的实际登榜结果待观测。</p>
        </div>
        <div class="journal-model-backtest">
          <span>历史回测 AUC <strong>{{ decimal(cv.auc, 3) }}</strong></span>
          <span>回测样本 <strong>{{ formatCount(cv.n_samples) }}</strong></span>
          <button class="atlas-inline" type="button" @click="openValidation">查看检验和系数<AppIcon name="arrow" :size="15" /></button>
        </div>
      </aside>

      <div class="journal-interlude">
        <h2>把候选放回职业轨迹</h2>
        <p>上榜作品按发行年累积，表示作品曾被热门榜单收录。已知年份登榜按原始榜单年份计，缺失年份保持未知。</p>
      </div>
      <div class="op-grid atlas-graph-grid atlas-rising-main">
        <section class="op-card">
          <header>
            <div><h3>两位参照与所选候选</h3><p>用同一年份和尺度对照三位艺人的职业轨迹</p></div>
            <div class="atlas-segments" role="group" aria-label="职业轨迹指标">
              <button v-for="metric in careerMetrics" :key="metric.key" type="button"
                :aria-pressed="careerMetric === metric.key" @click="careerMetric = metric.key">{{ metric.label }}</button>
            </div>
          </header>
          <ChartPanel v-if="comparison.length" :option="trajectoryOption" height="292px" />
          <p v-else class="op-state">没有可对比的职业轨迹。</p>
        </section>
        <aside v-if="candidate" class="op-card atlas-candidate-detail" aria-label="候选档案">
          <div class="atlas-inspector-top"><span>候选档案</span><span>第 {{ candidate.rank }} 位</span></div>
          <h2>{{ candidate.name }}</h2>
          <div class="atlas-model-stats">
            <div><span>Logistic 模型输出</span><strong>{{ decimal(candidate.model_probability, 3) }}</strong></div>
            <div><span>重采样获首比例</span><strong>{{ percent(candidate.bootstrap_rank1_share) }}</strong></div>
          </div>
          <h3>六维百分位</h3>
          <dl class="atlas-dimension-grid">
            <div v-for="dimension in dimensions" :key="dimension.key">
              <dt><i :style="{ background: dimension.color }" />{{ dimension.label }}</dt>
              <dd>{{ decimal(candidate.strength_percentiles?.[dimension.key], 0) }}</dd>
            </div>
          </dl>
          <details class="atlas-candidate-evidence">
            <summary>查看成员与推荐依据</summary>
            <p v-if="candidate.member_names?.length">{{ candidate.member_names.join('、') }}</p>
            <ul><li v-for="line in candidate.evidence" :key="line">{{ line }}</li></ul>
          </details>
        </aside>
      </div>

      <div class="op-grid even atlas-secondary-grid">
        <section class="op-card">
          <header><h3>候选能力对比</h3><p>参照群体内的百分位</p></header>
          <ChartPanel v-if="predictions.length" :option="radarOption" height="295px"
            @chart-click="params => chooseCandidate(params.data?.actId)" />
          <p v-else class="op-state">没有可对比的候选。</p>
        </section>
        <section class="op-card">
          <header><h3>Oceanus Folk 综合分排行</h3><p>深蓝为所选候选，灰色为已有登榜记录</p></header>
          <ChartPanel v-if="leaderboard.length" :option="leaderboardOption" height="295px"
            @chart-click="params => chooseCandidate(params.data?.actId)" />
          <p v-else class="op-state">没有可用的排行记录。</p>
        </section>
      </div>

      <details ref="validationCard" class="op-card atlas-validation">
        <summary>历史回溯与统计检验</summary>
        <p>综合分来自六维百分位加权。Logistic 模型基于历史五年回溯，预测期暂无真实结果。</p>
        <div class="op-grid even">
          <div class="op-scroll">
            <table class="op-table">
              <thead><tr><th>特征</th><th>正 / 负均值</th><th>p 值</th><th>FDR q 值</th></tr></thead>
              <tbody><tr v-for="row in validation.univariate?.tests ?? []" :key="row.feature">
                <td>{{ labelOf(row.feature) }}</td><td>{{ decimal(row.mean_positive) }} / {{ decimal(row.mean_negative) }}</td>
                <td>{{ row.p_value.toExponential(1) }}</td><td>{{ decimal(row.p_fdr, 3) }}</td>
              </tr></tbody>
            </table>
          </div>
          <div class="op-scroll">
            <table class="op-table">
              <thead><tr><th>Logistic 特征</th><th>系数</th><th>优势比</th></tr></thead>
              <tbody><tr v-for="row in validation.coefficients ?? []" :key="row.feature">
                <td>{{ labelOf(row.feature) }}</td><td>{{ decimal(row.coefficient, 3) }}</td><td>{{ decimal(row.odds_ratio, 3) }}</td>
              </tr></tbody>
            </table>
          </div>
        </div>
      </details>
      <JournalPager module="rising" />
    </template>
  </div>
</template>
