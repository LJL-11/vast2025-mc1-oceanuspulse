<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import ChartPanel from '../components/ChartPanel.vue'
import GenreCarta from '../components/GenreCarta.vue'
import GenreChronicle from '../components/GenreChronicle.vue'
import JournalPager from '../components/JournalPager.vue'
import TimeScrubber from '../components/TimeScrubber.vue'
import FilterPanel from '../components/FilterPanel.vue'
import AppIcon from '../components/AppIcon.vue'
import { FLOW_TONES } from '../lib/atlas'
import {
  FLOW_TYPES, FLOW_COLORS, EDGE_LABELS, genreColor,
  CHART_MUTED, CHART_GRID, formatCount,
} from '../lib/palette'

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const trends = ref(null)
const flows = ref(null)
const overview = ref(null)
const selectedCell = ref(null)
const selectedYear = ref(null)
const selectedGenre = ref('')
const trendMode = ref('spread')
const showAllLanes = ref(store.focusGenres.length < 2)
const evidencePanel = ref(null)

onMounted(async () => {
  try {
    const [t, f, o] = await Promise.all([
      dataService.genreTrends(), dataService.genreFlows(),
      dataService.overview(),
    ])
    trends.value = t
    flows.value = f
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
  series: (focusGenres.value.length ? focusGenres.value : [featuredGenre.value]).map((genre, index) => ({
    name: genre, type: 'line', showSymbol: chartYears.value.length < 5, symbolSize: 6,
    lineStyle: { width: index === 0 ? 2.8 : 1.7, color: genreColor(index) },
    itemStyle: { color: genreColor(index) },
    areaStyle: index === 0 ? { color: 'rgba(232,115,74,0.10)' } : undefined,
    data: chartYears.value.map(year => rowLookup.value.get(`${genre}|${year}`)?.[metric.value] ?? null),
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
  return [...new Set([...focusGenres.value, 'Oceanus Folk', ...ranked])].slice(0, 12)
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
    position: 'top', renderMode: 'richText',
    formatter: params => {
      const source = matrixGenres.value[params.data[1]]
      const target = matrixGenres.value[params.data[0]]
      return `${source} → ${target}\n${params.data[2]} 条引用 · 点击查看证据`
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
    inRange: { color: ['#eff5f8', '#c2dbe9', '#6ca9c2', '#21577d'] },
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
    name: EDGE_LABELS[type], type: 'line', stack: 'flow', showSymbol: false,
    lineStyle: { width: 0 }, areaStyle: { color: FLOW_COLORS[type], opacity: 0.78 },
    itemStyle: { color: FLOW_COLORS[type] },
    data: chartYears.value.map(year => filteredFlows.value
      .filter(flow => flow.type === type && flow.year === year)
      .reduce((sum, flow) => sum + flow.value, 0)),
  })),
}))

function onMatrixClick(params) {
  if (!params.data) return
  choosePair(matrixGenres.value[params.data[1]], matrixGenres.value[params.data[0]])
}
function onTrendClick(params) {
  selectedCell.value = null
  selectedYear.value = chartYears.value[params.dataIndex] ?? null
  selectedGenre.value = params.seriesName
}
function chooseMapYear({ year, genre }) {
  selectedCell.value = null
  selectedYear.value = year
  selectedGenre.value = genre
}
function choosePair(source, target, year = null) {
  if (year == null || year !== selectedYear.value) selectedGenre.value = ''
  selectedYear.value = year
  selectedCell.value = { source, target }
}
function clearEvidence() {
  selectedCell.value = null
  selectedYear.value = null
  selectedGenre.value = ''
}
watch([yearRange, focusGenres, visibleFlowTypes, metric], clearEvidence)
watch(focusGenres, genres => { if (genres.length > 1) showAllLanes.value = false })
const drillRows = computed(() => {
  if (selectedCell.value) {
    return filteredFlows.value.filter(flow =>
      flow.source === selectedCell.value.source && flow.target === selectedCell.value.target
      && (selectedYear.value == null || flow.year === selectedYear.value),
    )
  }
  if (selectedYear.value != null) {
    return filteredFlows.value.filter(flow => flow.year === selectedYear.value &&
      (!selectedGenre.value || (metric.value === 'inbound_events' ? flow.target : flow.source) === selectedGenre.value))
  }
  return filteredFlows.value.slice(0, 12)
})

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
function topFlow(side, fixed, year = null) {
  const totals = new Map()
  for (const flow of filteredFlows.value) {
    if (year != null && flow.year !== year) continue
    if (side === 'out' && flow.source !== fixed) continue
    if (side === 'in' && flow.target !== fixed) continue
    const key = side === 'out' ? flow.target : flow.source
    if (key === fixed) continue
    totals.set(key, (totals.get(key) || 0) + flow.value)
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3)
}
const topOut = computed(() => topFlow('out', 'Oceanus Folk'))
const topIn = computed(() => topFlow('in', 'Oceanus Folk'))
const featuredGenre = computed(() => focusGenres.value[0] || 'Oceanus Folk')
const featuredOut = computed(() => topFlow('out', featuredGenre.value))
const featuredIn = computed(() => topFlow('in', featuredGenre.value))
const lensGenre = computed(() => selectedGenre.value || selectedCell.value?.source || featuredGenre.value)
const lensOut = computed(() => topFlow('out', lensGenre.value, selectedYear.value))
const lensIn = computed(() => topFlow('in', lensGenre.value, selectedYear.value))
const allLaneNames = computed(() => {
  const focus = featuredGenre.value
  const affinity = new Map()
  for (const flow of flows.value?.flows ?? []) {
    if (flow.source === flow.target || (flow.source !== focus && flow.target !== focus)) continue
    const peer = flow.source === focus ? flow.target : flow.source
    affinity.set(peer, (affinity.get(peer) ?? 0) + flow.value)
  }
  const ranked = allGenres.value.filter(name => name !== focus)
    .sort((a, b) => (affinity.get(b) ?? 0) - (affinity.get(a) ?? 0) || a.localeCompare(b))
  const left = ranked.filter((_, index) => index % 2 === 0).reverse()
  const right = ranked.filter((_, index) => index % 2 === 1)
  return [...left, focus, ...right]
})
const focusedLanes = computed(() => {
  if (focusGenres.value.length > 1) return focusGenres.value
  return [...new Set([featuredGenre.value, ...featuredOut.value.map(row => row[0]), ...featuredIn.value.map(row => row[0])])].slice(0, 6)
})
const laneGenres = computed(() => showAllLanes.value ? allLaneNames.value : focusedLanes.value)
const makeTrack = genre => ({
  name: genre,
  colorIndex: Math.max(0, allGenres.value.indexOf(genre)),
  rows: chartYears.value.map(year => ({
    year, value: rowLookup.value.get(genre + '|' + year)?.[metric.value] ?? null,
  })),
})
const scoreTracks = computed(() => laneGenres.value.map(makeTrack))
const spreadTracks = computed(() => focusedLanes.value.map(makeTrack))
const issues = computed(() => overview.value?.issue_counts || {})
const folkWorks = computed(() => overview.value?.genre_work_counts?.['Oceanus Folk'] ?? 0)
</script>

<template>
  <div class="atlas-analysis atlas-genre">
    <div v-if="loading" class="op-state">正在加载流派年度趋势与影响流向…</div>
    <div v-else-if="error" class="op-state error">
      {{ error }}<br><code>python -m pipeline.run</code>
    </div>

    <template v-else>
      <header class="journal-opening">
        <span class="journal-folio" aria-label="第 02 章">02</span>
        <div class="journal-lede">
          <h1>Oceanus Folk 的传播年代</h1>
          <p v-if="peakRow && folkTotal">全期外向引用中，<strong>{{ (boomShare * 100).toFixed(1) }}%</strong> 集中在 2023—2030 年，最高的一年是 {{ peakRow.year }} 年。</p>
          <p v-else>沿年代比较各流派的外向引用与灵感来源。</p>
        </div>
        <aside class="journal-margin" aria-label="当前年代谱口径">
          <p><strong>{{ allGenres.length }} 种</strong>可探索流派</p>
          <p><strong>{{ formatCount(filteredFlows.reduce((s, f) => s + f.value, 0)) }} 条</strong>当前筛选的跨流派引用</p>
        </aside>
      </header>

      <details class="op-card atlas-filter-card atlas-genre-filters">
        <summary><span>调整地图筛选</span><small>{{ yearRange.join('—') }} · {{ metricOptions.find(item => item.value === metric)?.label }}</small></summary>
        <div class="op-toolbar">
          <span class="op-tool-label">趋势指标</span>
          <div class="op-chips">
            <button
              v-for="item in metricOptions" :key="item.value" type="button"
              class="op-chip" :class="{ on: metric === item.value }"
              :aria-pressed="metric === item.value"
              @click="metric = item.value"
            >{{ item.label }}</button>
          </div>
          <select class="op-select" aria-label="添加对比流派" @change="addGenre">
            <option value="">＋ 添加流派…</option>
            <option v-for="genre in allGenres" :key="genre" :value="genre">{{ genre }}</option>
          </select>
        </div>
        <div class="op-toolbar">
          <FilterPanel v-model="visibleFlowTypes" label="引用关系类型" :options="flowTypeOptions" />
        </div>
        <div class="op-toolbar">
          <TimeScrubber v-model="yearRange" :min="overview.year_fields.release_year.min" :max="overview.meta.cutoff_year" />
          <details class="atlas-comparison-filter">
            <summary>对比流派 · {{ focusGenres.length }} 个</summary>
            <FilterPanel v-model="focusGenres" :label="null" :options="genreOptions" />
          </details>
        </div>
      </details>

      <div class="op-grid atlas-graph-grid atlas-genre-main">
        <section class="journal-spread-board">
          <header class="journal-figure-head">
            <div>
              <h2>{{ trendMode === 'spread' ? '跨页年代谱' : trendMode === 'map' ? '跨流派年代地图' : '年度传播轨迹' }}</h2>
              <p>{{ trendMode === 'line' ? '折线连接已观察的年度值' : '色带厚度表示年度指标，弧线指向受影响的流派' }}</p>
            </div>
            <div class="atlas-segments" role="group" aria-label="传播图表形式">
              <button type="button" :aria-pressed="trendMode === 'spread'" @click="trendMode = 'spread'">年代谱</button>
              <button type="button" :aria-pressed="trendMode === 'map'" @click="trendMode = 'map'">年代地图</button>
              <button type="button" :aria-pressed="trendMode === 'line'" @click="trendMode = 'line'">年度曲线</button>
            </div>
          </header>
          <GenreChronicle v-if="trendMode === 'spread'" :tracks="spreadTracks" :years="chartYears" :flows="filteredFlows"
            :featured-genre="featuredGenre" :selected-year="selectedYear" :selected-genre="selectedGenre || selectedCell?.source"
            :ratio="isRatio" @select-year="chooseMapYear" @inspect="evidencePanel?.scrollIntoView({ block: 'start' })"
            @select-flow="flow => choosePair(flow.source, flow.target, flow.year)" />
          <template v-else-if="trendMode === 'map'">
            <GenreCarta :tracks="scoreTracks" :years="chartYears" :flows="filteredFlows"
              :featured-genre="featuredGenre" :selected-year="selectedYear" :selected-genre="selectedGenre || selectedCell?.source"
              :ratio="isRatio" @select-year="chooseMapYear" @inspect="evidencePanel?.scrollIntoView({ block: 'start' })"
              @select-flow="flow => choosePair(flow.source, flow.target, flow.year)" />
            <div class="atlas-map-caption">
              <span>拖动浏览 · Ctrl + 滚轮缩放 · 点选色带和弧线查看证据</span>
              <button type="button" class="atlas-inline" :aria-pressed="showAllLanes" @click="showAllLanes = !showAllLanes">
                <AppIcon :name="showAllLanes ? 'flow' : 'expand'" :size="15" />
                {{ showAllLanes ? '聚焦对比流派' : '查看全部 ' + allGenres.length + ' 个流派' }}
              </button>
            </div>
          </template>
          <ChartPanel v-else :option="trendOption" height="400px" @chart-click="onTrendClick" />
        </section>
        <aside class="op-card atlas-genre-relationships journal-relation-index">
          <div>
            <div class="atlas-inspector-top"><span>双向关系</span><span>{{ selectedYear ?? yearRange.join('—') }} 年</span></div>
            <h2>{{ lensGenre }}</h2>
            <button v-if="selectedCell || selectedYear != null" type="button" class="atlas-inline"
              @click="evidencePanel?.scrollIntoView({ block: 'start' })">查看筛选证据<AppIcon name="arrow" :size="15" /></button>
          </div>
          <div v-for="(entries, side) in { in: lensIn, out: lensOut }" :key="side" class="atlas-flow-list">
            <h3><i :style="{ background: FLOW_TONES[side] }" />{{ side === 'in' ? '灵感流入' : '影响流出' }}</h3>
            <button v-for="[name, count] in entries" :key="name" type="button" class="atlas-flow-row"
              @click="side === 'in' ? choosePair(name, lensGenre, selectedYear) : choosePair(lensGenre, name, selectedYear)">
              <span>{{ name }}</span><strong>{{ count }}</strong><AppIcon name="arrow" :size="14" />
            </button>
            <p v-if="!entries.length" class="atlas-subtle">当前范围无记录</p>
          </div>
        </aside>
      </div>

      <div class="journal-interlude">
        <h2>核对影响从哪里来</h2>
        <p>矩阵的行是来源，列是受影响流派。点选流派对、年份或弧线，下面会列出对应的原始关系。</p>
      </div>
      <div class="op-grid even">
        <section class="op-card">
          <header><h3>流派影响流向矩阵</h3><p>纵轴来源 · 横轴受影响者 · 点击格子钻取</p></header>
          <ChartPanel v-if="matrixCells.length" :option="matrixOption" height="360px" @chart-click="onMatrixClick" />
          <p v-else class="op-state">当前筛选下没有可显示的跨流派关系。</p>
          <p class="op-note">颜色为当前时间窗与关系类型筛选下的影响事件总量；自流（同一流派内部）已排除，避免与内部事件混淆。</p>
        </section>
        <section class="op-card">
          <header><h3>五类影响关系的年代构成</h3><p>堆叠面积 · 当前筛选</p></header>
          <ChartPanel v-if="filteredFlows.length" :option="flowTypeOption" height="360px" />
          <p v-else class="op-state">当前筛选下没有可汇总的引用。</p>
          <p class="op-note">风格借鉴、翻唱、采样、片段引用与歌词引用在原始图中方向相反，本视图统一为「来源 → 受影响者」并保留原始端点。</p>
        </section>
      </div>

      <section ref="evidencePanel" class="op-card atlas-evidence-panel">
        <header>
          <h3>证据钻取</h3>
          <p v-if="selectedCell">{{ selectedCell.source }} → {{ selectedCell.target }}{{ selectedYear != null ? ' · ' + selectedYear : '' }}</p>
          <p v-else-if="selectedYear != null">{{ selectedGenre }} · {{ selectedYear }} 年的引用</p>
          <p v-else>点击上方矩阵或趋势图以筛选，默认展示前 12 条</p>
          <button v-if="selectedCell || selectedYear != null" type="button" class="atlas-inline" @click="clearEvidence">清除定位</button>
        </header>
        <div class="op-scroll">
          <table class="op-table">
            <thead><tr><th>来源</th><th>受影响</th><th>关系类型</th><th class="num">年份</th><th class="num">事件数</th><th>原始边 ID 示例</th></tr></thead>
            <tbody>
              <tr v-for="(flow, index) in drillRows.slice(0, 40)" :key="`${flow.source}-${flow.target}-${flow.type}-${flow.year}-${index}`">
                <td>{{ flow.source }}</td><td>{{ flow.target }}</td>
                <td>{{ EDGE_LABELS[flow.type] || flow.type }}</td>
                <td class="num">{{ flow.year }}</td><td class="num">{{ flow.value }}</td>
                <td><code>{{ flow.event_ids.slice(0, 3).join(' / ') || '—' }}</code></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!drillRows.length" class="atlas-subtle">当前时间窗与关系类型下没有匹配的引用。</p>
        <p class="op-note">每行都可回查 <code>MC1_graph.json</code> 的原始关系 ID；推导到艺人的联系不证明私下合作或因果影响。</p>
      </section>

      <div class="journal-interlude"><h2>读图笔记</h2></div>
      <div class="op-insights journal-notes">
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
      <JournalPager module="genre" />
    </template>
  </div>
</template>
