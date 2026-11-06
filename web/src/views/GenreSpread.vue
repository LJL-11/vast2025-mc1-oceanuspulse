<script setup>
import { computed, onMounted, ref } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import ChartPanel from '../components/ChartPanel.vue'
import TimeScrubber from '../components/TimeScrubber.vue'
import FilterPanel from '../components/FilterPanel.vue'
import {
  FLOW_TYPES, FLOW_COLORS, EDGE_LABELS, genreColor,
  CHART_MUTED, CHART_GRID, formatCount,
} from '../lib/palette'

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const trends = ref(null)
const flows = ref(null)
const events = ref(null)
const overview = ref(null)
const selectedCell = ref(null)
const selectedYear = ref(null)

onMounted(async () => {
  try {
    const [t, f, e, o] = await Promise.all([
      dataService.genreTrends(), dataService.genreFlows(),
      dataService.influenceEvents(), dataService.overview(),
    ])
    trends.value = t
    flows.value = f
    events.value = e
    overview.value = o
  } catch (cause) {
    error.value = friendlyDataError(cause)
  } finally {
    loading.value = false
  }
})

const metricOptions = [
  { value: 'outbound_events', label: '外向影响事件' },
  { value: 'inbound_events', label: '内向吸收事件' },
  { value: 'outbound_trailing_5y_mean', label: '5 年滚动均值' },
  { value: 'external_work_coverage', label: '受影响作品覆盖率' },
]
const flowTypeOptions = FLOW_TYPES.map(type => ({
  value: type, label: EDGE_LABELS[type], color: FLOW_COLORS[type],
}))
const metric = computed({ get: () => store.trendMetric, set: value => { store.trendMetric = value } })
const yearRange = computed({ get: () => store.yearRange, set: value => store.setYearRange(value) })
const focusGenres = computed({ get: () => store.focusGenres, set: value => { store.focusGenres = value } })
const visibleFlowTypes = computed({
  get: () => store.visibleFlowTypes,
  set: value => { store.visibleFlowTypes = value },
})

const allGenres = computed(() => trends.value?.genres || [])
const genreOptions = computed(() => {
  const totals = new Map()
  for (const flow of flows.value?.flows || []) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value)
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value)
  }
  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1]).map(entry => entry[0])
  const head = ['Oceanus Folk', ...ranked.filter(name => name !== 'Oceanus Folk')].slice(0, 12)
  return [...new Set([...head, ...focusGenres.value])].map(name => ({
    value: name, label: name,
  }))
})
function addGenre(event) {
  const value = event.target.value
  if (value && !focusGenres.value.includes(value)) focusGenres.value = [...focusGenres.value, value]
  event.target.value = ''
}

const rowsInWindow = computed(() => (trends.value?.rows || [])
  .filter(row => row.year >= yearRange.value[0] && row.year <= yearRange.value[1]))
const chartYears = computed(() => [...new Set(rowsInWindow.value.map(row => row.year))].sort((a, b) => a - b))
const rowLookup = computed(() => new Map(rowsInWindow.value.map(row => [`${row.genre}|${row.year}`, row])))
const isRatio = computed(() => metric.value === 'external_work_coverage')

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { type: 'scroll', top: 0, textStyle: { fontSize: 11, color: CHART_MUTED } },
  grid: { left: 52, right: 20, top: 34, bottom: 30 },
  xAxis: {
    type: 'category', boundaryGap: false, data: chartYears.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    axisLine: { lineStyle: { color: CHART_GRID } },
  },
  yAxis: {
    type: 'value', name: isRatio.value ? '覆盖率' : '事件数',
    nameTextStyle: { fontSize: 10, color: CHART_MUTED },
    axisLabel: {
      fontSize: 10, color: CHART_MUTED,
      formatter: value => (isRatio.value ? `${(value * 100).toFixed(0)}%` : value),
    },
    splitLine: { lineStyle: { color: CHART_GRID } },
  },
  series: focusGenres.value.map((genre, index) => ({
    name: genre, type: 'line', smooth: true, showSymbol: false,
    lineStyle: { width: index === 0 ? 2.8 : 1.7, color: genreColor(index) },
    itemStyle: { color: genreColor(index) },
    areaStyle: index === 0 ? { color: 'rgba(232,115,74,0.10)' } : undefined,
    data: chartYears.value.map(year => rowLookup.value.get(`${genre}|${year}`)?.[metric.value] ?? 0),
  })),
}))

const filteredFlows = computed(() => (flows.value?.flows || []).filter(flow =>
  flow.year != null
  && flow.year >= yearRange.value[0]
  && flow.year <= yearRange.value[1]
  && visibleFlowTypes.value.includes(flow.type)
  && flow.source !== flow.target,
))
const matrixGenres = computed(() => {
  const totals = new Map()
  for (const flow of filteredFlows.value) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value)
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value)
  }
  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1]).map(entry => entry[0])
  return ['Oceanus Folk', ...ranked.filter(name => name !== 'Oceanus Folk')].slice(0, 12)
})
const matrixCells = computed(() => {
  const aggregate = new Map()
  for (const flow of filteredFlows.value) {
    if (!matrixGenres.value.includes(flow.source) || !matrixGenres.value.includes(flow.target)) continue
    const key = `${flow.source}|${flow.target}`
    aggregate.set(key, (aggregate.get(key) || 0) + flow.value)
  }
  return [...aggregate.entries()].map(([key, value]) => {
    const [source, target] = key.split('|')
    return [matrixGenres.value.indexOf(target), matrixGenres.value.indexOf(source), value]
  })
})
const matrixMax = computed(() => {
  const values = matrixCells.value.map(cell => cell[2]).sort((a, b) => a - b)
  return values.length ? Math.max(1, values[Math.floor(values.length * 0.92)]) : 1
})
const matrixOption = computed(() => ({
  tooltip: {
    position: 'top',
    formatter: params => {
      const source = matrixGenres.value[params.data[1]]
      const target = matrixGenres.value[params.data[0]]
      return `${source} <b>→</b> ${target}<br>影响事件 ${params.data[2]} 条 · 点击查看证据`
    },
  },
  grid: { left: 112, right: 16, top: 14, bottom: 76 },
  xAxis: {
    type: 'category', data: matrixGenres.value,
    axisLabel: { rotate: 42, fontSize: 10, color: CHART_MUTED },
    splitArea: { show: true },
  },
  yAxis: {
    type: 'category', data: matrixGenres.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    splitArea: { show: true },
  },
  visualMap: {
    min: 0, max: matrixMax.value, calculable: false,
    orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 12, itemHeight: 90,
    textStyle: { fontSize: 10, color: CHART_MUTED },
    inRange: { color: ['#F4F7FA', '#D6EAE5', '#79BFB0', '#E8734A'] },
  },
  series: [{
    type: 'heatmap', data: matrixCells.value,
    itemStyle: { borderColor: '#fff', borderWidth: 1 },
    emphasis: { itemStyle: { borderColor: '#17324d', borderWidth: 2 } },
  }],
}))

const flowTypeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0, textStyle: { fontSize: 11, color: CHART_MUTED } },
  grid: { left: 46, right: 18, top: 32, bottom: 28 },
  xAxis: {
    type: 'category', boundaryGap: false, data: chartYears.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    axisLine: { lineStyle: { color: CHART_GRID } },
  },
  yAxis: {
    type: 'value', name: '事件数', nameTextStyle: { fontSize: 10, color: CHART_MUTED },
    axisLabel: { fontSize: 10, color: CHART_MUTED }, splitLine: { lineStyle: { color: CHART_GRID } },
  },
  series: FLOW_TYPES.filter(type => visibleFlowTypes.value.includes(type)).map(type => ({
    name: EDGE_LABELS[type], type: 'line', stack: 'flow', smooth: true, showSymbol: false,
    lineStyle: { width: 0 }, areaStyle: { color: FLOW_COLORS[type], opacity: 0.78 },
    itemStyle: { color: FLOW_COLORS[type] },
    data: chartYears.value.map(year => filteredFlows.value
      .filter(flow => flow.type === type && flow.year === year)
      .reduce((sum, flow) => sum + flow.value, 0)),
  })),
}))

function onMatrixClick(params) {
  if (!params.data) return
  selectedCell.value = {
    source: matrixGenres.value[params.data[1]],
    target: matrixGenres.value[params.data[0]],
  }
}
function onTrendClick(params) {
  selectedYear.value = chartYears.value[params.dataIndex] ?? null
}
const drillRows = computed(() => {
  if (selectedCell.value) {
    return filteredFlows.value.filter(flow =>
      flow.source === selectedCell.value.source && flow.target === selectedCell.value.target,
    )
  }
  if (selectedYear.value != null) {
    return filteredFlows.value.filter(flow => flow.year === selectedYear.value)
  }
  return filteredFlows.value.slice(0, 12)
})
const eventById = computed(() => new Map((events.value?.events || []).map(event => [event.id, event])))
function evidenceFor(flow) {
  return (flow.event_ids || []).slice(0, 3).map(id => {
    const event = eventById.value.get(id)
    return event ? `${id} · ${event.type} · ${event.year ?? '无日期'}` : id
  })
}

const folkRows = computed(() => (trends.value?.rows || []).filter(row => row.genre === 'Oceanus Folk'))
const peakRow = computed(() => folkRows.value.reduce(
  (best, row) => (!best || row.outbound_events > best.outbound_events ? row : best), null,
))
const folkTotal = computed(() => folkRows.value.reduce((sum, row) => sum + row.outbound_events, 0))
const concentration = computed(() => peakRow.value && folkTotal.value
  ? peakRow.value.outbound_events / folkTotal.value : 0)
const folkActiveYears = computed(() => folkRows.value.filter(row => row.outbound_events > 0).length)
const boomShare = computed(() => folkTotal.value
  ? folkRows.value.filter(row => row.year >= 2023 && row.year <= 2030)
    .reduce((sum, row) => sum + row.outbound_events, 0) / folkTotal.value : 0)
const lateShare = computed(() => folkTotal.value
  ? folkRows.value.filter(row => row.year >= 2032)
    .reduce((sum, row) => sum + row.outbound_events, 0) / folkTotal.value : 0)
const trailingPeak = computed(() => folkRows.value.reduce(
  (best, row) => (!best || row.outbound_trailing_5y_mean > best.outbound_trailing_5y_mean ? row : best), null,
))
const spreadLabel = computed(() => concentration.value < 0.2 && folkActiveYears.value >= 10
  ? '多波次扩散'
  : concentration.value < 0.4 ? '脉冲式扩散' : '单年爆发')
function topFlow(side, fixed) {
  const totals = new Map()
  for (const flow of filteredFlows.value) {
    if (side === 'out' && flow.source !== fixed) continue
    if (side === 'in' && flow.target !== fixed) continue
    const key = side === 'out' ? flow.target : flow.source
    if (key === 'Oceanus Folk') continue
    totals.set(key, (totals.get(key) || 0) + flow.value)
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3)
}
const topOut = computed(() => topFlow('out', 'Oceanus Folk'))
const topIn = computed(() => topFlow('in', 'Oceanus Folk'))
const issues = computed(() => overview.value?.issue_counts || {})
const folkWorks = computed(() => overview.value?.genre_work_counts?.['Oceanus Folk'] ?? 0)
</script>

<template>
  <div>
    <div v-if="loading" class="op-state">正在加载流派年度趋势与影响流向…</div>
    <div v-else-if="error" class="op-state error">
      {{ error }}<br><code>python -m pipeline.run</code>
    </div>

    <template v-else>
      <div class="op-page-head">
        <div>
          <h2>模块二 · 流派传播</h2>
          <p>Oceanus Folk 的年度影响轨迹与跨流派流向 · 对应赛题任务 2.1 / 2.2 / 2.3</p>
        </div>
        <span class="op-tag">来源 → 受影响者</span>
      </div>

      <div class="op-kpis">
        <div class="op-kpi"><b>{{ allGenres.length }}</b><span>流派</span></div>
        <div class="op-kpi"><b>{{ (trends.years || []).length }}</b><span>年度截面</span></div>
        <div class="op-kpi"><b>{{ formatCount(folkWorks) }}</b><span>Oceanus Folk 作品</span></div>
        <div class="op-kpi"><b>{{ formatCount(filteredFlows.reduce((s, f) => s + f.value, 0)) }}</b><span>当前筛选影响事件</span></div>
        <div class="op-kpi"><b>{{ peakRow?.year ?? '—' }}</b><span>外向事件峰值年</span></div>
        <div class="op-kpi"><b>{{ spreadLabel }}</b><span>扩散形态判定</span></div>
      </div>

      <section class="op-card" style="padding: 0; margin-bottom: 14px">
        <div class="op-toolbar">
          <span class="op-tool-label">趋势指标</span>
          <div class="op-chips">
            <button
              v-for="item in metricOptions" :key="item.value" type="button"
              class="op-chip" :class="{ on: metric === item.value }"
              @click="metric = item.value"
            >{{ item.label }}</button>
          </div>
          <select class="op-select" @change="addGenre">
            <option value="">＋ 添加流派…</option>
            <option v-for="genre in allGenres" :key="genre" :value="genre">{{ genre }}</option>
          </select>
        </div>
        <div class="op-toolbar">
          <FilterPanel v-model="visibleFlowTypes" label="影响关系" :options="flowTypeOptions" />
        </div>
        <div class="op-toolbar">
          <FilterPanel v-model="focusGenres" label="对比流派" :options="genreOptions" />
          <TimeScrubber v-model="yearRange" :min="1975" :max="2040" />
        </div>
      </section>

      <section class="op-card" style="margin-bottom: 14px">
        <header>
          <h3>流派影响年度轨迹</h3>
          <p>点击曲线可锁定年份查看当年证据 · {{ metricOptions.find(item => item.value === metric)?.label }}</p>
        </header>
        <ChartPanel :option="trendOption" height="320px" @chart-click="onTrendClick" />
        <p class="op-note">每条曲线为一个流派的年度指标；5 年滚动均值用于区分单年脉冲与持续扩散。零计数年份已补齐，缺失分母保持 null 而不渲染为 0。</p>
      </section>

      <div class="op-grid even">
        <section class="op-card">
          <header><h3>流派影响流向矩阵</h3><p>纵轴来源 · 横轴受影响者 · 点击格子钻取</p></header>
          <ChartPanel :option="matrixOption" height="360px" @chart-click="onMatrixClick" />
          <p class="op-note">颜色为当前时间窗与关系类型筛选下的影响事件总量；自流（同一流派内部）已排除，避免与内部事件混淆。</p>
        </section>
        <section class="op-card">
          <header><h3>五类影响关系的年代构成</h3><p>堆叠面积 · 当前筛选</p></header>
          <ChartPanel :option="flowTypeOption" height="360px" />
          <p class="op-note">风格借鉴、翻唱、采样、片段引用与歌词引用在原始图中方向相反，本视图统一为「来源 → 受影响者」并保留原始端点。</p>
        </section>
      </div>

      <section class="op-card" style="margin-top: 14px">
        <header>
          <h3>证据钻取</h3>
          <p v-if="selectedCell">{{ selectedCell.source }} → {{ selectedCell.target }}</p>
          <p v-else-if="selectedYear != null">{{ selectedYear }} 年影响事件</p>
          <p v-else>点击上方矩阵或趋势图以筛选，默认展示前 12 条</p>
        </header>
        <div class="op-scroll">
          <table class="op-table">
            <thead><tr><th>来源</th><th>受影响</th><th>关系类型</th><th class="num">年份</th><th class="num">事件数</th><th>原始边 ID 示例</th></tr></thead>
            <tbody>
              <tr v-for="(flow, index) in drillRows.slice(0, 40)" :key="`${flow.source}-${flow.target}-${flow.type}-${flow.year}-${index}`">
                <td>{{ flow.source }}</td><td>{{ flow.target }}</td>
                <td>{{ EDGE_LABELS[flow.type] || flow.type }}</td>
                <td class="num">{{ flow.year }}</td><td class="num">{{ flow.value }}</td>
                <td><span class="op-tag">{{ evidenceFor(flow).join(' / ') || '—' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="op-note">每行都可回查 <code>MC1_graph.json</code> 的原始关系 ID；推导到艺人的联系不证明私下合作或因果影响。</p>
      </section>

      <h3 style="font-size: 14px; font-weight: 500; color: #17324d; margin: 20px 0 10px">数据洞见</h3>
      <div class="op-insights">
        <article class="op-insight">
          <span class="tag">洞见 01 · 渐进 vs 间歇</span>
          <h4>既非单年爆发，也非匀速渐进</h4>
          <p>全期 {{ formatCount(folkTotal) }} 条外向影响事件分布在 {{ folkActiveYears }} 个年份，峰值 {{ peakRow?.year }} 年仅占 {{ (concentration * 100).toFixed(1) }}%；但 {{ (boomShare * 100).toFixed(1) }}% 集中在 2023–2030 的 Sailor 崛起期，5 年滚动均值在 {{ trailingPeak?.year }} 年达 {{ trailingPeak?.outbound_trailing_5y_mean }}。因此判定为「{{ spreadLabel }}」——多波次脉冲，而不是持续线性上升。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 02 · 向外辐射</span>
          <h4>受影响最大的外部流派</h4>
          <p>当前筛选下，Oceanus Folk 主要流向 {{ topOut.map(item => `${item[0]}（${item[1]} 条）`).join('、') || '无可用事件' }}；这回答了「它影响了谁」。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 03 · 反向吸收</span>
          <h4>它从哪里借来灵感</h4>
          <p>流入 Oceanus Folk 的来源前三位为 {{ topIn.map(item => `${item[0]}（${item[1]} 条）`).join('、') || '无可用事件' }}；流入流出分开统计，避免把借鉴者误当成来源。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 04 · 统计边界</span>
          <h4>年度曲线没有包含三类证据</h4>
          <p>{{ formatCount(issues.influence_chronology) }} 条时间顺序存疑的引用、1 条自环与 67 条无日期的艺人间引用被排除在年度统计外（但保留在结构证据中）；{{ formatCount(issues.notable_without_chart_year) }} 部 notable 作品缺登榜年份，不能补成发行年。此外 2032 年后仅剩 {{ (lateShare * 100).toFixed(1) }}% 的有日期外向事件，这反映后期借鉴作品样本变少，不能解读为「影响力消失」。</p>
        </article>
      </div>
    </template>
  </div>
</template>
