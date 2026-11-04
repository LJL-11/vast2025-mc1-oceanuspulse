<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dataUrl: {
    type: String,
    default: () => `${import.meta.env.BASE_URL}data/processed/rising_star.json`,
  },
})

const data = ref(null)
const loading = ref(true)
const error = ref('')
const trajectoryEl = ref(null)
const radarEl = ref(null)
const leaderboardEl = ref(null)

const charts = []
const COLORS = ['#1a5fb4', '#e67e22', '#16a085']

const predictions = computed(() => data.value?.predictions || [])
const comparison = computed(() => data.value?.comparison || [])
const validation = computed(() => data.value?.validation || {})
const meta = computed(() => data.value?.meta || {})
const leaderboard = computed(() => (data.value?.leaderboard || []).slice(0, 12))

const cv = computed(() => validation.value.cross_validation || {})
const univariate = computed(() => (validation.value.univariate?.tests || []).slice(0, 6))
const coefficients = computed(() => (validation.value.coefficients || []).slice(0, 6))

const featureLabels = computed(() => {
  const map = {}
  for (const item of data.value?.features || []) map[item.key] = item.label
  return map
})

function labelOf(key) {
  return featureLabels.value[key] || key
}

function pct(value) {
  return `${Number(value).toFixed(2)}%`
}

function prob(value) {
  return Number(value).toFixed(3)
}

function scoreTone(score) {
  if (score >= 75) return 'high'
  if (score >= 60) return 'mid'
  return 'low'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(props.dataUrl)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    data.value = await response.json()
    await nextTick()
    renderCharts()
  } catch (err) {
    error.value = `无法读取 ${props.dataUrl}。请先在仓库根目录运行 python pipeline/features.py。`
  } finally {
    loading.value = false
  }
}

function buildTrajectoryOption() {
  const artists = comparison.value
  const years = new Set()
  for (const artist of artists) {
    for (const row of artist.timeline || []) years.add(row.year)
  }
  const xAxis = [...years].sort((a, b) => a - b)
  const series = []
  artists.forEach((artist, index) => {
    const byYear = new Map((artist.timeline || []).map((row) => [row.year, row]))
    const cumulativeNotable = xAxis.map((year) => byYear.get(year)?.cumulative_notable ?? null)
    const cumulativeHits = xAxis.map((year) => byYear.get(year)?.cumulative_hits ?? null)
    series.push({
      name: `${artist.name} · 累计上榜`,
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2.4, color: COLORS[index % COLORS.length] },
      itemStyle: { color: COLORS[index % COLORS.length] },
      data: cumulativeNotable,
    })
    series.push({
      name: `${artist.name} · 累计登榜`,
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 1.6, type: 'dashed', color: COLORS[index % COLORS.length] },
      itemStyle: { color: COLORS[index % COLORS.length] },
      data: cumulativeHits,
    })
  })
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 44, right: 18, top: 28, bottom: 58 },
    xAxis: {
      type: 'category',
      data: xAxis,
      axisLabel: { fontSize: 10 },
      axisLine: { lineStyle: { color: '#ddd' } },
    },
    yAxis: {
      type: 'value',
      name: '累计数量',
      nameTextStyle: { fontSize: 11, color: '#888' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { fontSize: 10 },
    },
    series,
  }
}

function buildRadarOption() {
  const items = predictions.value
  return {
    backgroundColor: 'transparent',
    tooltip: {},
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    radar: {
      radius: '62%',
      center: ['50%', '46%'],
      indicator: [
        { name: '导师', max: 100 },
        { name: '动量', max: 100 },
        { name: '质量', max: 100 },
        { name: '合作', max: 100 },
        { name: '影响力', max: 100 },
        { name: '厂牌', max: 100 },
      ],
      axisName: { fontSize: 11, color: '#555' },
      splitArea: { areaStyle: { color: ['#fafafa', '#f3f7fd'] } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 4,
        data: items.map((item, index) => ({
          name: item.name,
          value: [
            item.strength_percentiles?.mentor ?? 0,
            item.strength_percentiles?.momentum ?? 0,
            item.strength_percentiles?.quality ?? 0,
            item.strength_percentiles?.collaboration ?? 0,
            item.strength_percentiles?.influence ?? 0,
            item.strength_percentiles?.prestige ?? 0,
          ],
          lineStyle: { width: 2, color: COLORS[index % COLORS.length] },
          itemStyle: { color: COLORS[index % COLORS.length] },
          areaStyle: { opacity: 0.08 },
        })),
      },
    ],
  }
}

function buildLeaderboardOption() {
  const rows = [...leaderboard.value].reverse()
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = rows[params[0].dataIndex]
        return `${item.name}<br/>综合分：${item.score}<br/>模型概率：${prob(item.model_probability)}<br/>是否已登榜：${item.had_hit ? '是' : '否'}`
      },
    },
    grid: { left: 128, right: 28, top: 12, bottom: 24 },
    xAxis: {
      type: 'value',
      max: 100,
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.name),
      axisLabel: { fontSize: 11, width: 116, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barWidth: 12,
        data: rows.map((row) => ({
          value: row.score,
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: row.had_hit ? '#c9d3df' : '#1a5fb4',
          },
        })),
        label: { show: true, position: 'right', fontSize: 10, formatter: '{c}' },
      },
    ],
  }
}

function ensureChart(element) {
  if (!element) return null
  let chart = echarts.getInstanceByDom(element)
  if (!chart) {
    chart = echarts.init(element)
    charts.push(chart)
  }
  return chart
}

function renderCharts() {
  if (!data.value) return
  ensureChart(trajectoryEl.value)?.setOption(buildTrajectoryOption(), true)
  ensureChart(radarEl.value)?.setOption(buildRadarOption(), true)
  ensureChart(leaderboardEl.value)?.setOption(buildLeaderboardOption(), true)
}

function resizeCharts() {
  for (const chart of charts) chart.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  for (const chart of charts) chart.dispose()
  charts.length = 0
})

watch(data, () => nextTick(renderCharts))
</script>

<template>
  <section class="rising-star">
    <header class="page-header">
      <div>
        <h2>模块三 · Rising Star 画像与预测</h2>
        <p class="subtitle">
          数据快照 {{ meta.snapshot_year }} · 预测窗口
          {{ (meta.prediction_window || []).join('–') }} · Oceanus Folk 下一代新星
        </p>
      </div>
      <div class="kpis">
        <div class="kpi">
          <span class="kpi-value">{{ cv.auc ? cv.auc.toFixed(3) : '—' }}</span>
          <span class="kpi-label">5 折 AUC</span>
        </div>
        <div class="kpi">
          <span class="kpi-value">{{ meta.reference_acts ?? '—' }}</span>
          <span class="kpi-label">参照 act</span>
        </div>
        <div class="kpi">
          <span class="kpi-value">{{ predictions.length }}</span>
          <span class="kpi-label">预测新星</span>
        </div>
      </div>
    </header>

    <p v-if="loading" class="state">加载中…</p>
    <p v-else-if="error" class="state error">{{ error }}</p>

    <template v-else>
      <section class="prediction-grid">
        <article
          v-for="item in predictions"
          :key="item.act_id"
          class="prediction-card"
          :class="scoreTone(item.score)"
        >
          <div class="card-head">
            <span class="rank">#{{ item.rank }}</span>
            <div class="card-title">
              <h3>{{ item.name }}</h3>
              <p>{{ item.primary_genre || 'Oceanus Folk' }} · {{ item.debut }}–{{ item.last_active }}</p>
            </div>
            <div class="score">
              <strong>{{ item.score }}</strong>
              <span>综合分</span>
            </div>
          </div>

          <div class="metric-row">
            <span>模型概率 {{ prob(item.model_probability) }}</span>
            <span>Bootstrap 第一名 {{ pct((item.bootstrap_rank1_share || 0) * 100) }}</span>
          </div>

          <div class="strength-bars">
            <div v-for="(value, key) in item.strength_percentiles" :key="key" class="bar-row">
              <span class="bar-label">{{ labelOf(key) || key }}</span>
              <div class="bar-track"><div class="bar-fill" :style="{ width: `${value}%` }" /></div>
              <span class="bar-value">{{ value.toFixed(0) }}</span>
            </div>
          </div>

          <ul class="evidence">
            <li v-for="line in item.evidence" :key="line">{{ line }}</li>
          </ul>

          <div class="members">
            <span class="members-label">成员</span>
            <span>{{ item.member_names.join('、') }}</span>
          </div>
        </article>
      </section>

      <section class="chart-grid">
        <article class="chart-card wide">
          <header>
            <h3>三位艺人的职业轨迹</h3>
            <p>实线：累计上榜作品 · 虚线：累计登榜作品</p>
          </header>
          <div ref="trajectoryEl" class="chart chart-lg" />
        </article>

        <article class="chart-card">
          <header>
            <h3>Top3 能力雷达</h3>
            <p>各维度为 2040 年 Oceanus Folk 参照群体的百分位</p>
          </header>
          <div ref="radarEl" class="chart chart-lg" />
        </article>
      </section>

      <section class="chart-grid">
        <article class="chart-card">
          <header>
            <h3>2040 年 Oceanus Folk 综合分排行</h3>
            <p>蓝色：未登榜候选 · 灰色：已登榜艺人</p>
          </header>
          <div ref="leaderboardEl" class="chart chart-lg" />
        </article>

        <article class="chart-card">
          <header>
            <h3>统计检验</h3>
            <p>Mann–Whitney U + BH-FDR · Logistic 系数</p>
          </header>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>特征</th><th>正/负均值</th><th>p</th><th>q</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in univariate" :key="row.feature">
                  <td>{{ labelOf(row.feature) }}</td>
                  <td>{{ row.mean_positive.toFixed(2) }} / {{ row.mean_negative.toFixed(2) }}</td>
                  <td>{{ row.p_value.toExponential(1) }}</td>
                  <td>{{ row.p_fdr.toFixed(3) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>模型特征</th><th>系数</th><th>OR</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in coefficients" :key="row.feature">
                  <td>{{ labelOf(row.feature) }}</td>
                  <td>{{ row.coefficient.toFixed(3) }}</td>
                  <td>{{ row.odds_ratio.toFixed(3) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <footer class="note">
        <p>
          说明：综合分是 6 个维度百分位的加权和，权重见
          <code>pipeline/features.py</code>；Logistic 模型仅作独立验证。预测窗口内没有真值，
          验证采用 2040 年前的历史 5 年回溯。
        </p>
      </footer>
    </template>
  </section>
</template>

<style scoped>
.rising-star {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}
.subtitle {
  margin: 6px 0 0;
  color: var(--c-muted);
  font-size: 13px;
}
.kpis {
  display: flex;
  gap: 18px;
}
.kpi {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 68px;
}
.kpi-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--c-primary);
}
.kpi-label {
  font-size: 11px;
  color: var(--c-muted);
}
.state {
  padding: 32px;
  text-align: center;
  color: var(--c-muted);
  background: #fff;
  border: 1px dashed var(--c-border);
  border-radius: 10px;
}
.state.error {
  color: #b42318;
  border-color: #f3c4c0;
  background: #fff7f6;
}
.prediction-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}
.prediction-card {
  background: #fff;
  border: 1px solid var(--c-border);
  border-top: 4px solid var(--c-border);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.prediction-card.high { border-top-color: #1a5fb4; }
.prediction-card.mid { border-top-color: #e67e22; }
.prediction-card.low { border-top-color: #16a085; }
.card-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.rank {
  font-size: 13px;
  font-weight: 700;
  color: var(--c-primary);
  padding-top: 2px;
}
.card-title {
  flex: 1;
}
.card-title h3 {
  margin: 0;
  font-size: 16px;
}
.card-title p {
  margin: 3px 0 0;
  font-size: 11px;
  color: var(--c-muted);
}
.score {
  text-align: right;
}
.score strong {
  display: block;
  font-size: 24px;
  color: var(--c-primary);
  line-height: 1;
}
.score span {
  font-size: 10px;
  color: var(--c-muted);
}
.metric-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--c-muted);
}
.strength-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.bar-row {
  display: grid;
  grid-template-columns: 54px 1fr 26px;
  gap: 6px;
  align-items: center;
  font-size: 10px;
  color: var(--c-muted);
}
.bar-track {
  height: 5px;
  background: #eef1f5;
  border-radius: 999px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #7aa7e0, #1a5fb4);
  border-radius: 999px;
}
.bar-value {
  text-align: right;
}
.evidence {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #444;
  line-height: 1.5;
}
.members {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--c-muted);
  border-top: 1px dashed var(--c-border);
  padding-top: 8px;
}
.members-label {
  color: #999;
  flex-shrink: 0;
}
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.chart-card {
  background: #fff;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 14px 16px;
  min-width: 0;
}
.chart-card header h3 {
  margin: 0;
  font-size: 14px;
}
.chart-card header p {
  margin: 3px 0 0;
  font-size: 11px;
  color: var(--c-muted);
}
.chart {
  width: 100%;
}
.chart-lg {
  height: 300px;
}
.table-wrap {
  max-height: 210px;
  overflow: auto;
  margin-top: 10px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
th,
td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid #f1f1f1;
  white-space: nowrap;
}
th {
  color: var(--c-muted);
  font-weight: 500;
  position: sticky;
  top: 0;
  background: #fff;
}
.note {
  color: var(--c-muted);
  font-size: 11px;
  line-height: 1.7;
}
@media (max-width: 900px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .page-header {
    align-items: flex-start;
  }
}
</style>
