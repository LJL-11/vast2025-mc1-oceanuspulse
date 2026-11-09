<script setup>
import { computed, defineComponent, h, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import TimeScrubber from '../components/TimeScrubber.vue'
import AppIcon from '../components/AppIcon.vue'
import {
  FLOW_TYPES, FLOW_COLORS, EDGE_LABELS, NODE_LABELS, genreColor, GENRE_PALETTE,
  CHART_GRID, formatCount,
} from '../lib/palette'
const CHART_MUTED = '#536b82'

// Module-local event bridge: shared ChartPanel and other modules retain their contract.
const ChartPanel = defineComponent({
  props: { option: Object, height: { type: String, default: '340px' }, label: String },
  emits: ['chart-click', 'chart-zoom'],
  setup(props, { emit }) {
    const host = ref(null)
    let chart, observer
    const render = () => {
      if (!chart) return
      const selected = chart.getOption()?.legend?.[0]?.selected
      const legend = props.option.legend ? { ...props.option.legend, ...(selected ? { selected } : {}) } : undefined
      chart.setOption({ ...props.option, textStyle: { fontFamily: getComputedStyle(host.value).fontFamily }, legend, series: props.option.series.map(s => ({ ...s, animationDuration: 180, animationDurationUpdate: 180, ...(s.type === 'sankey' ? { animation: false } : {}) })), animation: !window.matchMedia('(prefers-reduced-motion: reduce)').matches, animationDuration: 180 }, { notMerge: true })
    }
    onMounted(() => {
      chart = echarts.init(host.value)
      chart.on('click', p => {
        // ECharts line paths have a series but no point index between symbols.
        if (props.option.dataZoom && p.seriesType === 'line' && p.dataIndex == null && p.event) {
          const [index] = chart.convertFromPixel({ gridIndex: 0 }, [p.event.offsetX, p.event.offsetY])
          const year = props.option.xAxis.data[Math.round(index)]
          if (year != null) emit('chart-click', { ...p, name: String(year) })
          return
        }
        emit('chart-click', p)
      })
      chart.on('mouseover', p => {
        if (p.seriesType !== 'heatmap') return
        chart.dispatchAction({ type: 'downplay' })
        const data = props.option.series[0].data
        const indices = data.flatMap((d, i) => d.value[0] === p.value[0] || d.value[1] === p.value[1] ? [i] : [])
        chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: indices })
      })
      chart.on('globalout', () => chart.dispatchAction({ type: 'downplay' }))
      chart.on('datazoom', () => {
        const zoom = chart.getOption().dataZoom?.[0]
        if (zoom) emit('chart-zoom', { start: zoom.start, end: zoom.end })
      })
      observer = new ResizeObserver(() => chart.resize())
      observer.observe(host.value)
      render()
    })
    watch(() => props.option, render)
    onActivated(() => nextTick(() => chart?.resize()))
    onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
    return () => h('div', { ref: host, class: 'op-chart', role: 'img', 'aria-label': props.label, style: { height: props.height } })
  },
})

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const trends = ref(null)
const flows = ref(null)
const events = ref(null)
const overview = ref(null)
const selectedCell = ref(null)
const selectedYear = ref(null)
const evidencePage = ref(1)
const showAllGenres = ref(false)
const evidenceEl = ref(null)
const selectedTrendGenre = ref(null)
const selectedRelation = ref(null)
const genreSearch = ref('')
const matrixSearch = ref('')
const matrixSort = ref('volume')
const matrixLocked = ref(false)
const lockedGenres = ref([])
const fixedScale = ref(false)
const compositionMode = ref('count')
const zoomRange = ref({ start: 0, end: 100 })
const evidenceSearch = ref('')
const evidenceSort = ref('count')
const pageSize = ref(12)
const expandedFlow = ref(null)
const nodeMap = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const notice = ref('')
let noticeTimer
function showNotice(message, persistent = false) {
  clearTimeout(noticeTimer)
  notice.value = message
  if (!persistent) noticeTimer = setTimeout(() => { notice.value = '' }, 3500)
}
onBeforeUnmount(() => clearTimeout(noticeTimer))
const yearError = ref('')
const trendEl = ref(null)
const matrixEl = ref(null)
const overlayMean = ref(false)
const matrixView = ref('matrix')
const tooltipStyle = { backgroundColor: '#fff', borderColor: '#e2e8f0', padding: 12, textStyle: { color: '#243d56', fontSize: 13 }, extraCssText: 'box-shadow:0 8px 28px #17324d18;border-radius:8px', confine: true }
function clearDrill() { selectedCell.value = null; selectedYear.value = null; selectedTrendGenre.value = null; selectedRelation.value = null; evidencePage.value = 1; expandedFlow.value = null }
function resetFilters() {
  yearRange.value = [1975, 2040]
  visibleFlowTypes.value = [...FLOW_TYPES]
  focusGenres.value = ['Oceanus Folk']
  metric.value = 'outbound_events'
  zoomRange.value = { start: 0, end: 100 }
  yearError.value = ''
  evidenceSearch.value = ''
  genreSearch.value = ''
  matrixSearch.value = ''
  clearDrill()
}
function scrollTo(el) { el?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }) }
function scrollToEvidence() { scrollTo(evidenceEl.value) }
function setYear(which, event) {
  const value = Number(event.target.value)
  const next = [...yearRange.value]; next[which] = value
  if (!event.target.value || !Number.isInteger(value) || value < 1975 || value > 2040 || next[0] > next[1]) {
    yearError.value = '请输入 1975–2040 的整数年份，起始年不能晚于结束年。'
    event.target.value = yearRange.value[which]
    return
  }
  yearError.value = ''; yearRange.value = next
}
function toggleGenre(genre) {
  if (focusGenres.value.includes(genre)) {
    if (focusGenres.value.length > 1) focusGenres.value = focusGenres.value.filter(g => g !== genre)
  } else focusGenres.value = [...focusGenres.value, genre]
}
function toggleRelation(type) {
  const selected = visibleFlowTypes.value.includes(type)
  if (selected && visibleFlowTypes.value.length === 1) return
  visibleFlowTypes.value = selected ? visibleFlowTypes.value.filter(t => t !== type) : [...visibleFlowTypes.value, type]
}
const searchedGenres = computed(() => allGenres.value.filter(g => g.toLowerCase().includes(genreSearch.value.toLowerCase())))
// Reserve coral for the focal genre so comparison lines cannot reuse its color.
const colorForGenre = genre => genreColor(genre === 'Oceanus Folk' ? 0
  : 1 + allGenres.value.filter(g => g !== 'Oceanus Folk').indexOf(genre) % (GENRE_PALETTE.length - 1))

async function loadData() {
  loading.value = true; error.value = ''
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
}
onMounted(loadData)

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
const rowsInWindow = computed(() => (trends.value?.rows || [])
  .filter(row => row.year >= yearRange.value[0] && row.year <= yearRange.value[1]))
const chartYears = computed(() => [...new Set(rowsInWindow.value.map(row => row.year))].sort((a, b) => a - b))
const rowLookup = computed(() => new Map(rowsInWindow.value.map(row => [`${row.genre}|${row.year}`, row])))
const isRatio = computed(() => metric.value === 'external_work_coverage')
const zoomYears = computed(() => {
  const n = chartYears.value.length - 1
  return [chartYears.value[Math.round(n * zoomRange.value.start / 100)], chartYears.value[Math.round(n * zoomRange.value.end / 100)]]
})
function applyZoom() { if (zoomYears.value[0] != null) yearRange.value = [...zoomYears.value] }
function selectYear(value) {
  if (!value) return clearDrill()
  const year = Number(value)
  if (chartYears.value.includes(year)) onTrendClick({ name: year, seriesName: focusGenres.value[0] })
}

function peakMarker(genre) {
  if (genre !== focusGenres.value[0]) return
  const peak = rowsInWindow.value.reduce((best, row) =>
    row.genre === genre && row[metric.value] > 0 && (!best || row[metric.value] > best[metric.value]) ? row : best, null)
  if (!peak) return
  const value = peak[metric.value]
  const label = isRatio.value ? `${(value * 100).toFixed(1)}%` : `${value} 条`
  const color = colorForGenre(genre)
  const index = chartYears.value.indexOf(peak.year)
  const align = index === 0 ? 'left' : index === chartYears.value.length - 1 ? 'right' : 'center'
  return {
    symbol: 'circle', symbolSize: 12,
    itemStyle: { color, borderColor: '#fff', borderWidth: 2, shadowColor: color + '55', shadowBlur: 5 },
    label: {
      show: true, position: 'top', distance: 8, align,
      backgroundColor: '#193b50', borderRadius: 7, padding: [7, 10],
      formatter: `{year|${peak.year}}  {value|${label}}`,
      rich: { year: { color: '#dce6ed', fontSize: 11 }, value: { color: '#fff', fontSize: 12, fontWeight: 600 } },
    },
    data: [{ name: String(peak.year), coord: [String(peak.year), value], value }],
  }
}

const trendOption = computed(() => ({
  tooltip: { ...tooltipStyle, trigger: 'axis', axisPointer: { type: 'line', snap: true, lineStyle: { color: '#8298aa', type: 'dashed', width: 1 } }, formatter: params => {
    const year = Number(params[0]?.axisValue)
    const heading = metricOptions.find(item => item.value === metric.value)?.label || ''
    const rows = params.map(p => {
      const row = rowLookup.value.get(`${p.seriesName}|${year}`)
      const value = p.value == null ? '—' : isRatio.value ? `${(p.value * 100).toFixed(2)}%` : `${formatCount(p.value)} 条`
      const basis = isRatio.value && row ? `<small>${row.all_external_work_releases > 0 ? `${row.external_influenced_work_count} / ${row.all_external_work_releases} 部外部作品` : '当年无可用分母'}</small>` : ''
      return `<div class="trend-tip-row"><span>${p.marker}${echarts.format.encodeHTML(p.seriesName)}</span><b>${value}</b>${basis}</div>`
    }).join('')
    return `<div class="trend-tip"><div class="trend-tip-title"><strong>${year} 年</strong><span>${heading}</span></div>${rows}</div>`
  } },
  legend: { type: 'scroll', top: 8, right: 24, width: '68%', itemWidth: 22, itemHeight: 8, itemGap: 20, textStyle: { fontSize: 12, color: '#476477' } },
  grid: { left: 48, right: 24, top: 56, bottom: 78 },
  dataZoom: [
    { type: 'inside', ...zoomRange.value, zoomOnMouseWheel: 'ctrl' },
    {
      type: 'slider', ...zoomRange.value, left: 48, right: 24, height: 26, bottom: 8,
      borderColor: '#e2eaf0', backgroundColor: '#f5f8fa', fillerColor: 'rgba(38, 93, 121, .08)',
      dataBackground: { lineStyle: { color: '#87a2ad' }, areaStyle: { color: '#d9e3e7' } },
      selectedDataBackground: { lineStyle: { color: '#577a89' }, areaStyle: { color: '#bacdd5' } },
      handleSize: '105%', handleStyle: { color: '#fff', borderColor: '#6b8795', borderWidth: 1.5, shadowBlur: 3, shadowColor: '#193b501a' },
      moveHandleStyle: { color: '#b8cbd6' },
      textStyle: { color: CHART_MUTED }, brushSelect: false,
    },
  ],
  xAxis: {
    type: 'category', boundaryGap: false, data: chartYears.value,
    axisLabel: { fontSize: 11, color: '#748999', hideOverlap: true, margin: 14 },
    axisTick: { show: false }, axisLine: { lineStyle: { color: '#bbcbd3' } },
  },
  yAxis: {
    type: 'value', name: isRatio.value ? '覆盖率' : '事件数',
    nameTextStyle: { fontSize: 12, color: CHART_MUTED },
    axisLabel: {
      fontSize: 12, color: CHART_MUTED,
      formatter: value => (isRatio.value ? `${(value * 100).toFixed(0)}%` : value),
    },
    splitNumber: 4, splitLine: { lineStyle: { color: '#e6edf2', type: [3, 4] } },
  },
  series: [...focusGenres.value.map((genre) => ({
    name: genre, type: 'line', smooth: false, symbol: 'emptyCircle', symbolSize: 7,
    showSymbol: zoomYears.value[1] - zoomYears.value[0] <= 12 && focusGenres.value.length <= 4,
    triggerLineEvent: true,
    emphasis: { focus: 'series' },
    lineStyle: { width: genre === focusGenres.value[0] ? 3 : 1.8, cap: 'round', join: 'round', color: colorForGenre(genre) },
    itemStyle: { color: colorForGenre(genre) },
    areaStyle: genre === focusGenres.value[0] && focusGenres.value.length === 1 ? {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: colorForGenre(genre) + '52' },
        { offset: .65, color: colorForGenre(genre) + '19' },
        { offset: 1, color: colorForGenre(genre) + '04' },
      ]),
    } : undefined,
    markPoint: peakMarker(genre),
    markLine: selectedTrendGenre.value && selectedYear.value != null ? { silent: true, symbol: 'none', lineStyle: { color: '#5470c6', type: 'dashed' }, data: [{ xAxis: String(selectedYear.value) }], label: { formatter: String(selectedYear.value) } } : undefined,
    data: chartYears.value.map(year => rowLookup.value.get(`${genre}|${year}`)?.[metric.value] ?? (isRatio.value ? null : 0)),
  })), ...(overlayMean.value && metric.value === 'outbound_events' ? focusGenres.value.map(genre => ({ name: `${genre} · 5年均值`, type: 'line', showSymbol: false, lineStyle: { color: colorForGenre(genre), type: 'dashed', width: 2 }, itemStyle: { color: colorForGenre(genre) }, data: chartYears.value.map(y => rowLookup.value.get(`${genre}|${y}`)?.outbound_trailing_5y_mean ?? null) })) : [])],
}))

const allCrossFlows = computed(() => (flows.value?.flows || []).filter(flow => flow.year != null && flow.source !== flow.target))
const filteredFlows = computed(() => allCrossFlows.value.filter(flow =>
  flow.year != null
  && flow.year >= yearRange.value[0]
  && flow.year <= yearRange.value[1]
  && visibleFlowTypes.value.includes(flow.type)
  && flow.source !== flow.target,
))
const matrixGenres = computed(() => {
  if (matrixLocked.value) return lockedGenres.value
  const totals = new Map()
  for (const flow of filteredFlows.value) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value)
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value)
  }
  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(entry => entry[0])
  let names = showAllGenres.value ? [...allGenres.value] : ['Oceanus Folk', ...ranked.filter(name => name !== 'Oceanus Folk')].slice(0, 12)
  if (matrixSort.value === 'name') names.sort((a, b) => a.localeCompare(b))
  return names
})
function toggleMatrixLock() { if (!matrixLocked.value) lockedGenres.value = [...matrixGenres.value]; matrixLocked.value = !matrixLocked.value }
const matrixCells = computed(() => {
  const aggregate = new Map()
  for (const flow of filteredFlows.value) {
    if (!matrixGenres.value.includes(flow.source) || !matrixGenres.value.includes(flow.target)) continue
    const key = `${flow.source}|${flow.target}`
    aggregate.set(key, (aggregate.get(key) || 0) + flow.value)
  }
  return matrixGenres.value.flatMap((source, y) => matrixGenres.value.map((target, x) => {
    const value = source === target ? '-' : aggregate.get(`${source}|${target}`) || 0
    const selected = selectedCell.value?.source === source && selectedCell.value?.target === target
    const matches = !matrixSearch.value || [source, target].some(n => n.toLowerCase().includes(matrixSearch.value.toLowerCase()))
    return { value: [x, y, value], itemStyle: { opacity: matches ? 1 : 0.18, borderColor: selected ? '#e8734a' : '#fff', borderWidth: selected ? 3 : 1 } }
  }))
})
const fullMatrixMax = computed(() => {
  const totals = new Map()
  for (const f of allCrossFlows.value) { const key = `${f.source}|${f.target}`; totals.set(key, (totals.get(key) || 0) + f.value) }
  return Math.max(1, ...totals.values())
})
const matrixMax = computed(() => {
  return fixedScale.value ? fullMatrixMax.value : Math.max(1, ...matrixCells.value.map(cell => Number(cell.value[2]) || 0))
})
const matrixOption = computed(() => ({
  tooltip: {
    ...tooltipStyle,
    position: 'top',
    formatter: params => {
      const [x, y, value] = params.value
      const source = matrixGenres.value[y], target = matrixGenres.value[x]
      return `${source} <b>→</b> ${target}<br>${source === target ? '同流派内部关系未纳入' : `影响事件 ${value} 条 · 点击查看证据`}`
    },
  },
  grid: { left: 136, right: 14, top: 12, bottom: 112 },
  xAxis: {
    type: 'category', data: matrixGenres.value,
    axisLabel: { rotate: 42, fontSize: 12, color: CHART_MUTED, interval: 'auto', width: 103, overflow: 'truncate' },
    axisTick: { show: false }, axisLine: { show: false },
    splitArea: { show: true },
  },
  yAxis: {
    type: 'category', data: matrixGenres.value,
    axisLabel: { fontSize: 12, color: CHART_MUTED, width: 124, overflow: 'truncate' },
    axisTick: { show: false }, axisLine: { show: false },
    splitArea: { show: true },
  },
  visualMap: {
    min: 0, max: matrixMax.value, calculable: false,
    orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 12, itemHeight: 90,
    text: [`${matrixMax.value} 条`, '少'], textStyle: { fontSize: 12, color: CHART_MUTED },
    inRange: { color: ['#f0f5f8', '#cbdfe8', '#8fb7c9', '#4d859f', '#214c65'] },
  },
  series: [{
    type: 'heatmap', data: matrixCells.value,
    label: { show: !showAllGenres.value, fontSize: 12, formatter: p => Number(p.value[2]) >= matrixMax.value * 0.15 ? p.value[2] : '' },
    itemStyle: { borderColor: '#fff', borderWidth: 1 },
    emphasis: { itemStyle: { borderColor: '#17324d', borderWidth: 2 } },
  }],
}))
const sankeyOption = computed(() => {
  const list = filteredFlows.value.filter(f => f.source === 'Oceanus Folk' || f.target === 'Oceanus Folk')
  const links = new Map()
  for (const f of list) {
    const source = f.target === 'Oceanus Folk' ? `in:${f.source}` : 'Oceanus Folk'
    const target = f.source === 'Oceanus Folk' ? `out:${f.target}` : 'Oceanus Folk'
    const key = `${source}|${target}`
    if (!links.has(key)) links.set(key, { source, target, value: 0, actualSource: f.source, actualTarget: f.target })
    links.get(key).value += f.value
  }
  const edges = [...links.values()]
  const nodes = [...new Set(edges.flatMap(e => [e.source, e.target]))].map(name => ({ name, itemStyle: { color: name === 'Oceanus Folk' ? '#e8734a' : name.startsWith('in:') ? '#2a9d8f' : '#5470c6' } }))
  return { tooltip: { ...tooltipStyle, formatter: p => p.dataType === 'edge' ? `${p.data.actualSource} → ${p.data.actualTarget}<br>${p.data.value} 条事件 · 点击查看证据` : p.name.replace(/^(in:|out:)/, '') }, series: [{ type: 'sankey', left: 10, right: 151, top: 12, bottom: 12, nodeWidth: 12, nodeGap: 12, data: nodes, links: edges, emphasis: { focus: 'adjacency' }, lineStyle: { color: 'source', opacity: .24, curveness: .5 }, label: { color: '#40566c', fontSize: 12, formatter: p => p.name.replace(/^(in:|out:)/, '') } }] }
})
function onFlowClick(p) { if (p.dataType === 'edge') { clearDrill(); selectedCell.value = { source: p.data.actualSource, target: p.data.actualTarget } } }

const compositionCounts = computed(() => {
  const totals = new Map()
  for (const f of filteredFlows.value) { const key = `${f.year}|${f.type}`; totals.set(key, (totals.get(key) || 0) + f.value) }
  return totals
})
const yearTotals = computed(() => new Map(chartYears.value.map(year => [year, FLOW_TYPES.reduce((sum, type) => sum + (compositionCounts.value.get(`${year}|${type}`) || 0), 0)])))
const flowTypeOption = computed(() => ({
  tooltip: { ...tooltipStyle, trigger: 'axis', axisPointer: { type: 'line' }, formatter: params => {
    const year = Number(params[0]?.axisValue)
    const total = yearTotals.value.get(year) || 0
    return `${year} 年 · 当前所选关系合计 ${total} 条<br>` + params.map(p => {
      const count = compositionCounts.value.get(`${year}|${FLOW_TYPES.find(t => EDGE_LABELS[t] === p.seriesName)}`) || 0
      return `${p.marker}${p.seriesName}：${count} 条 · ${total ? (count / total * 100).toFixed(1) + '%' : '无事件'}`
    }).join('<br>')
  } },
  legend: { type: 'scroll', top: 0, left: 'center', width: '90%', textStyle: { fontSize: 12, color: CHART_MUTED } },
  grid: { left: 46, right: 18, top: 48, bottom: 36 },
  xAxis: {
    type: 'category', boundaryGap: false, data: chartYears.value,
    axisLabel: { fontSize: 12, color: CHART_MUTED, hideOverlap: true },
    axisLine: { lineStyle: { color: CHART_GRID } },
  },
  yAxis: {
    type: 'value', name: compositionMode.value === 'share' ? '所选关系占比' : '事件数', max: compositionMode.value === 'share' ? 100 : undefined, nameTextStyle: { fontSize: 12, color: CHART_MUTED },
    axisLabel: { fontSize: 12, color: CHART_MUTED, formatter: v => compositionMode.value === 'share' ? `${v}%` : v }, splitLine: { lineStyle: { color: CHART_GRID } },
  },
  series: FLOW_TYPES.filter(type => visibleFlowTypes.value.includes(type)).map(type => ({
    name: EDGE_LABELS[type], type: 'line', stack: 'flow', smooth: false, showSymbol: false,
    emphasis: { focus: 'series' },
    lineStyle: { width: 1 }, areaStyle: { color: FLOW_COLORS[type], opacity: 0.72 },
    itemStyle: { color: FLOW_COLORS[type] },
    data: chartYears.value.map(year => {
      const count = compositionCounts.value.get(`${year}|${type}`) || 0
      return compositionMode.value === 'share' ? (yearTotals.value.get(year) ? count / yearTotals.value.get(year) * 100 : null) : count
    }),
  })),
}))

function onMatrixClick(params) {
  if (!params.value || params.value[0] === params.value[1]) return
  clearDrill()
  selectedCell.value = {
    source: matrixGenres.value[params.value[1]],
    target: matrixGenres.value[params.value[0]],
  }
}
function onTrendClick(params) {
  const year = Number(params.name) || chartYears.value[params.dataIndex]
  if (!chartYears.value.includes(year) || !params.seriesName) return
  clearDrill()
  selectedYear.value = year
  selectedTrendGenre.value = { genre: params.seriesName.replace(' · 5年均值', ''), side: metric.value === 'inbound_events' ? 'in' : 'out', rolling: metric.value === 'outbound_trailing_5y_mean' || params.seriesName.endsWith(' · 5年均值') }
}
function onCompositionClick(params) { clearDrill(); selectedYear.value = Number(params.name) || null; selectedRelation.value = FLOW_TYPES.find(t => EDGE_LABELS[t] === params.seriesName) || null }
const evidenceFilters = computed(() => {
  const trend = selectedTrendGenre.value
  const year = selectedYear.value
  const cell = selectedCell.value
  const relations = trend ? FLOW_TYPES : visibleFlowTypes.value
  return {
    analysisYears: [...yearRange.value],
    eventYears: year == null ? [...yearRange.value] : [trend?.rolling ? Math.max(1975, year - 4) : year, year],
    relations: selectedRelation.value ? relations.filter(type => type === selectedRelation.value) : [...relations],
    source: cell?.source || (trend?.side === 'out' ? trend.genre : null),
    target: cell?.target || (trend?.side === 'in' ? trend.genre : null),
    trendMetric: trend ? (trend.rolling ? 'outbound_trailing_5y_mean' : metric.value) : null,
    search: evidenceSearch.value.trim(),
    sort: evidenceSort.value,
  }
})
const scopeText = computed(() => {
  const f = evidenceFilters.value
  return [
    `分析年份 ${f.analysisYears.join('–')}`,
    `证据年份 ${f.eventYears[0] === f.eventYears[1] ? f.eventYears[0] : f.eventYears.join('–')}`,
    f.relations.length === FLOW_TYPES.length ? '全部五类关系' : f.relations.map(t => EDGE_LABELS[t]).join('、'),
    f.source && `来源 ${f.source}`, f.target && `去向 ${f.target}`,
    f.trendMetric && metricOptions.find(m => m.value === f.trendMetric)?.label,
    f.search && `搜索“${f.search}”`, f.sort === 'year' ? '年份降序' : '事件数降序',
  ].filter(Boolean).join(' · ')
})
const drillRows = computed(() => {
  const f = evidenceFilters.value
  const query = f.search.toLowerCase()
  return allCrossFlows.value.filter(row =>
    row.year >= f.eventYears[0] && row.year <= f.eventYears[1] && f.relations.includes(row.type)
    && (!f.source || row.source === f.source) && (!f.target || row.target === f.target)
    && (!query || `${row.source} ${row.target} ${EDGE_LABELS[row.type]} ${row.year} ${row.event_ids.join(' ')}`.toLowerCase().includes(query))
  ).sort((a, b) => f.sort === 'year' ? b.year - a.year || b.value - a.value : b.value - a.value || b.year - a.year)
})
const pageCount = computed(() => Math.max(1, Math.ceil(drillRows.value.length / pageSize.value)))
const pageRows = computed(() => drillRows.value.slice((evidencePage.value - 1) * pageSize.value, evidencePage.value * pageSize.value))
const eventTotal = computed(() => filteredFlows.value.reduce((s, f) => s + f.value, 0))
const folkWindowTotals = computed(() => rowsInWindow.value.reduce((totals, row) => {
  if (row.genre === 'Oceanus Folk') {
    totals.inbound += row.inbound_events
    totals.outbound += row.outbound_events
  }
  return totals
}, { inbound: 0, outbound: 0 }))
function jumpToPage(event) {
  const page = Number(event.target.value)
  if (Number.isInteger(page) && event.target.value) evidencePage.value = Math.min(pageCount.value, Math.max(1, page))
  event.target.value = evidencePage.value
}
watch(evidencePage, () => { expandedFlow.value = null })
watch(yearRange, clearDrill, { deep: true })
watch(visibleFlowTypes, () => { if (!selectedTrendGenre.value) clearDrill() }, { deep: true })
watch([metric, focusGenres], () => { if (selectedTrendGenre.value) clearDrill() }, { deep: true })
watch(yearRange, () => { zoomRange.value = { start: 0, end: 100 } }, { deep: true })
watch([drillRows, pageSize], () => { evidencePage.value = 1; expandedFlow.value = null })
watch([showAllGenres, matrixSort], () => { matrixLocked.value = false })
const eventById = computed(() => new Map((events.value?.events || []).map(event => [event.id, event])))
const flowKey = f => `${f.source}|${f.target}|${f.type}|${f.year}`
async function expandFlow(flow) {
  const key = flowKey(flow)
  expandedFlow.value = expandedFlow.value === key ? null : key
  if (!expandedFlow.value || nodeMap.value || detailLoading.value) return
  detailLoading.value = true; detailError.value = ''
  try { const data = await dataService.nodeIndex(); nodeMap.value = new Map(data.nodes.map(n => [n.id, n])) }
  catch (e) { detailError.value = friendlyDataError(e) }
  finally { detailLoading.value = false }
}
function entity(id) { const n = nodeMap.value?.get(id); return n ? `${n.display_name || n.name}（${NODE_LABELS[n.type] || n.type} · #${id}）` : `实体 #${id}` }
async function copyText(value) {
  try { await navigator.clipboard.writeText(value); showNotice('已复制到剪贴板。') }
  catch { showNotice('复制失败，请手动复制。', true) }
}
const conditionSummary = computed(() => [selectedCell.value ? `${selectedCell.value.source || '任意来源'} → ${selectedCell.value.target || '任意去向'}` : '', selectedYear.value ? `${selectedTrendGenre.value?.rolling ? Math.max(1975, selectedYear.value - 4) + '–' : ''}${selectedYear.value} 年` : '', selectedTrendGenre.value ? `${selectedTrendGenre.value.genre} · ${selectedTrendGenre.value.side === 'in' ? '流入' : '流出'} · 全部关系` : '', selectedRelation.value ? EDGE_LABELS[selectedRelation.value] : ''].filter(Boolean).join(' · '))
function removeCellCondition(key) {
  const next = { ...selectedCell.value, [key]: null }
  selectedCell.value = next.source || next.target ? next : null
}
function exportEvidence() {
  const payload = { scope: scopeText.value, filters: evidenceFilters.value, search: evidenceFilters.value.search, direction: '来源 → 受影响者', groups: drillRows.value }
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' }))
  const a = document.createElement('a'); a.href = url; a.download = 'OceanusPulse-流派传播证据.json'; a.click(); URL.revokeObjectURL(url)
  showNotice(`已导出 ${formatCount(drillRows.value.length)} 组证据。`)
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
async function locatePeak() {
  if (peakRow.value.year < yearRange.value[0] || peakRow.value.year > yearRange.value[1]) yearRange.value = [1975, 2040]
  metric.value = 'outbound_events'
  focusGenres.value = ['Oceanus Folk']
  zoomRange.value = { start: 0, end: 100 }
  evidenceSearch.value = ''
  await nextTick()
  onTrendClick({ name: peakRow.value.year, seriesName: 'Oceanus Folk' })
  scrollTo(trendEl.value)
}
async function locateBoom() {
  yearRange.value = [2023, 2030]; metric.value = 'outbound_events'; focusGenres.value = ['Oceanus Folk']
  await nextTick(); scrollTo(trendEl.value)
}
function locateFlow(side, name) {
  evidenceSearch.value = ''
  clearDrill(); selectedCell.value = side === 'out' ? { source: 'Oceanus Folk', target: name } : { source: name, target: 'Oceanus Folk' }
  scrollToEvidence()
}
</script>

<template>
  <div class="genre-workspace">
    <div v-if="loading" class="genre-loading" role="status" aria-busy="true"><p>正在加载流派年度趋势与影响流向…</p><div class="genre-skeleton" /><div class="genre-skeleton chart" /></div>
    <div v-else-if="error" class="op-state error">
      {{ error }}<br><code>python -m pipeline.run</code><p><button class="op-btn" @click="loadData">重新加载数据</button></p>
    </div>

    <template v-else>
      <header class="genre-mast">
        <div>
          <h2><span lang="en">Oceanus Folk</span> 的跨流派影响</h2>
          <p class="genre-dataset">全期覆盖 {{ (trends.years || []).length }} 年、{{ allGenres.length }} 个流派，收录 {{ formatCount(folkWorks) }} 部 Oceanus Folk 作品。</p>
          <button v-if="peakRow" class="genre-peak" @click="locatePeak"><strong>{{ peakRow.year }}</strong> 年外向影响最高，共 {{ peakRow.outbound_events }} 条 <span aria-hidden="true">↗</span></button>
        </div>
        <div class="genre-tally" role="status">
          <span class="genre-scope">{{ yearRange.join('–') }} · Oceanus Folk · 全部五类关系</span>
          <dl class="genre-focal-totals">
            <div><dt>外向影响</dt><dd>{{ formatCount(folkWindowTotals.outbound) }}<small> 条</small></dd></div>
            <div><dt>内向吸收</dt><dd>{{ formatCount(folkWindowTotals.inbound) }}<small> 条</small></dd></div>
          </dl>
        </div>
      </header>

      <section class="genre-filters" aria-label="分析范围">
        <div class="genre-period">
          <div class="genre-filter-line genre-year-inputs">
            <h3>年份</h3>
            <input type="number" aria-label="起始年份" :value="yearRange[0]" min="1975" :max="yearRange[1]" :aria-invalid="!!yearError" :aria-describedby="yearError ? 'genre-year-error' : undefined" @change="setYear(0, $event)">
            <span>至</span>
            <input type="number" aria-label="结束年份" :value="yearRange[1]" :min="yearRange[0]" max="2040" :aria-invalid="!!yearError" :aria-describedby="yearError ? 'genre-year-error' : undefined" @change="setYear(1, $event)">
          </div>
          <TimeScrubber v-model="yearRange" :min="1975" :max="2040" />
          <p v-if="yearError" id="genre-year-error" class="genre-form-error" role="alert">{{ yearError }}</p>
        </div>
        <button class="genre-reset" @click="resetFilters"><AppIcon name="reset" :size="14" />重置筛选</button>
      </section>

      <section ref="trendEl" class="op-card genre-trend" aria-labelledby="genre-trend-title">
        <header class="genre-trend-header">
          <div class="genre-trend-heading"><span class="genre-trend-icon" aria-hidden="true"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4v16h18M6 15l4-5 4 3 6-8"/><path d="M16 5h4v4"/></svg></span><div><h3 id="genre-trend-title">流派影响年度轨迹</h3><p>沿时间追踪影响的发生、积累与扩散</p></div></div>
          <div class="genre-segment" role="group" aria-label="趋势指标">
            <button v-for="item in metricOptions" :key="item.value" :aria-pressed="metric === item.value" :class="{ on: metric === item.value }" @click="metric = item.value">{{ item.label }}</button>
          </div>
        </header>
        <div class="genre-trend-toolbar">
        <details class="genre-picker">
          <summary><AppIcon name="plus" :size="15" /><span>对比流派</span><strong>{{ focusGenres.length === 1 ? focusGenres[0] : focusGenres.length + ' 个流派' }}</strong><span class="genre-picker-chevron" aria-hidden="true">⌄</span></summary>
          <div class="genre-picker-body">
            <label>搜索流派 <input v-model="genreSearch" type="search" placeholder="流派名称" class="op-input"></label>
            <button class="op-btn" @click="focusGenres = ['Oceanus Folk']">恢复主流派</button>
            <button class="op-btn" @click="focusGenres = [...allGenres]">对比全部流派</button>
            <div class="op-chips">
              <button v-for="genre in searchedGenres" :key="genre" class="op-chip" :class="{ on: focusGenres.includes(genre) }" :aria-pressed="focusGenres.includes(genre)" @click="toggleGenre(genre)">{{ genre }}</button>
            </div>
            <p v-if="!searchedGenres.length">没有匹配的流派。</p>
          </div>
        </details>
        <div class="genre-inline-tools"><label v-if="metric === 'outbound_events'" class="genre-mean-toggle"><input v-model="overlayMean" type="checkbox"><span>叠加 5 年均值</span></label><label class="genre-year-locator">定位年份 <select :value="selectedTrendGenre ? selectedYear ?? '' : ''" aria-label="定位年份" class="op-select" @change="selectYear($event.target.value)"><option value="">选择年份</option><option v-for="y in chartYears" :key="y" :value="String(y)">{{ y }}</option></select></label></div>
        </div>
        <div class="genre-trend-canvas">
          <div class="genre-chart-caption"><span>{{ metricOptions.find(item => item.value === metric)?.label }}</span><span>全部五类关系 · {{ chartYears.length }} 年</span></div>
          <ChartPanel :option="trendOption" label="流派年度指标折线图，可通过定位年份控件查看证据" height="360px" @chart-click="onTrendClick" @chart-zoom="zoomRange = $event" />
        </div>
        <div class="genre-chart-foot"><div class="genre-observation"><AppIcon name="expand" :size="15" /><span>观察范围 <strong>{{ zoomYears[0] }}–{{ zoomYears[1] }}</strong><small>缩放仅作用于当前图表</small></span></div><div class="genre-actions"><button class="op-btn genre-apply-window" :disabled="zoomRange.start === 0 && zoomRange.end === 100" @click="applyZoom">应用为分析时间窗<AppIcon name="arrow" :size="14" /></button><button class="op-btn genre-restore-window" @click="zoomRange = {start: 0, end: 100}"><AppIcon name="reset" :size="14" />恢复观察范围</button><button v-if="selectedTrendGenre && selectedYear" class="op-btn" @click="scrollToEvidence">查看 {{ selectedYear }} 年证据</button></div></div>
        <div v-if="selectedTrendGenre" class="genre-selection" role="status"><span>{{ conditionSummary }} · {{ drillRows.reduce((s,r) => s + r.value, 0) }} 条事件{{ selectedTrendGenre.rolling ? '（五年原始事件，曲线值为均值）' : '' }}</span><button class="op-btn" @click="clearDrill">清除定位</button></div>
        <aside class="genre-trend-fact">
          <div class="genre-insight-copy"><span class="genre-insight-icon"><AppIcon name="flow" :size="20" /></span><div><h4>Oceanus Folk 的{{ spreadLabel }}</h4><p>全期 {{ formatCount(folkTotal) }} 条外向事件中，<strong>{{ (boomShare * 100).toFixed(1) }}%</strong> 集中在 2023–2030 年。</p></div></div>
          <button class="genre-text-button" @click="locateBoom">探索 2023–2030<AppIcon name="arrow" :size="16" /></button>
        </aside>
      </section>

      <section class="genre-network-head" aria-label="流向与关系筛选">
        <div><h3>跨流派关系</h3><p>{{ yearRange.join('–') }} · 全网 {{ formatCount(eventTotal) }} 条事件</p></div>
        <div class="genre-relations">
          <div class="genre-filter-line"><span>筛选流向、关系构成及其证据</span><button v-if="visibleFlowTypes.length < FLOW_TYPES.length" class="genre-text-button" @click="visibleFlowTypes = [...FLOW_TYPES]">全选关系</button></div>
          <div class="op-chips"><button v-for="item in flowTypeOptions" :key="item.value" class="op-chip" :class="{ on: visibleFlowTypes.includes(item.value) }" :disabled="visibleFlowTypes.length === 1 && visibleFlowTypes.includes(item.value)" :aria-pressed="visibleFlowTypes.includes(item.value)" @click="toggleRelation(item.value)"><span class="dot" :style="{ background: item.color }" />{{ item.label }}</button></div>
        </div>
      </section>
      <div class="op-grid even">
        <section ref="matrixEl" class="op-card genre-matrix">
          <header><div class="genre-panel-heading"><span class="genre-panel-icon"><AppIcon name="flow" :size="23" /></span><div><h3>{{ matrixView === 'matrix' ? '流派影响流向矩阵' : 'Oceanus Folk 的影响流向' }}</h3><p>{{ matrixView === 'matrix' ? '纵轴为来源，横轴为受影响流派。' : '两侧分别统计流入与流出事件。' }}</p></div></div><div class="genre-segment" role="group" aria-label="流向视图"><button :aria-pressed="matrixView === 'matrix'" :class="{on: matrixView === 'matrix'}" @click="matrixView = 'matrix'">矩阵</button><button :aria-pressed="matrixView === 'sankey'" :class="{on: matrixView === 'sankey'}" @click="matrixView = 'sankey'">主流派流向</button></div></header>
          <div v-if="matrixView === 'matrix'" class="genre-inline-tools"><label>排序 <select v-model="matrixSort" class="op-select"><option value="volume">按事件量</option><option value="name">按名称</option></select></label><button class="op-btn" :aria-pressed="matrixLocked" @click="toggleMatrixLock">{{ matrixLocked ? '解锁顺序' : '锁定顺序' }}</button><label><input v-model="fixedScale" type="checkbox">固定全期色阶</label><button class="op-btn" :aria-pressed="showAllGenres" @click="showAllGenres = !showAllGenres">{{ showAllGenres ? '显示重点 12 类' : '展开全部 26 类' }}</button><label>查找流派 <input v-model="matrixSearch" type="search" class="op-input" placeholder="突出对应行与列"></label></div>
          <div v-if="matrixView === 'sankey'" class="genre-flow-sides"><span>影响来源</span><span>影响去向</span></div>
          <div class="genre-matrix-scroll"><div :class="{ 'genre-matrix-all': showAllGenres && matrixView === 'matrix' }"><ChartPanel v-if="matrixView === 'matrix'" :option="matrixOption" label="流派影响热力矩阵，纵轴为来源，横轴为受影响流派" :height="showAllGenres ? '640px' : '410px'" @chart-click="onMatrixClick" /><ChartPanel v-else :option="sankeyOption" label="来源流派到 Oceanus Folk 再到去向流派的桑基图" height="500px" @chart-click="onFlowClick" /></div></div>
          <div v-if="!filteredFlows.length || (matrixView === 'sankey' && !sankeyOption.series[0].links.length)" class="genre-empty">{{ matrixView === 'sankey' ? '当前范围没有 Oceanus Folk 的跨流派事件，请调整时间窗或关系类型。' : '当前范围没有跨流派事件，请调整时间窗或关系类型。' }}</div>
          <div v-if="selectedCell" class="genre-selection"><span>{{ selectedCell.source || '任意来源' }} → {{ selectedCell.target || '任意去向' }}</span><button class="op-btn" @click="scrollToEvidence">查看证据 ↓</button><button class="op-btn" @click="clearDrill">清除</button></div>
          <p class="op-note">{{ matrixView === 'matrix' ? '深色表示更多事件，最浅色表示 0；对角线留空，表示同流派内部关系未纳入。锁定顺序可固定跨时段对照的位置。' : '点击连线可查看这一对流派的事件。' }}</p>
          <div class="genre-rankings">
            <p class="genre-rank-caption">Oceanus Folk · 事件数前三位</p>
            <div class="genre-rank-columns">
              <article v-for="group in [{ side: 'in', title: '主要影响来源', rows: topIn }, { side: 'out', title: '主要影响去向', rows: topOut }]" :key="group.side">
                <h4>{{ group.title }}</h4>
                <ol>
                  <li v-for="[name, count] in group.rows" :key="name">
                    <button class="genre-rank" :aria-label="`查看${name}的${group.title}证据，${count}条`" @click="locateFlow(group.side, name)">
                      <span>{{ name }}</span><strong>{{ formatCount(count) }}</strong>
                    </button>
                  </li>
                </ol>
                <p v-if="!group.rows.length" class="genre-help">这段时间没有对应事件。</p>
              </article>
            </div>
          </div>
        </section>
        <section class="op-card genre-composition">
          <header><div class="genre-panel-heading"><span class="genre-panel-icon"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4v16h18M7 16v-4m5 4V8m5 8V5" /></svg></span><div><h3>五类影响关系的年代构成</h3><p>全网跨流派事件，按受影响作品发行年统计。</p></div></div><div class="genre-segment" role="group" aria-label="关系构成指标"><button :class="{on: compositionMode === 'count'}" :aria-pressed="compositionMode === 'count'" @click="compositionMode = 'count'">事件数量</button><button :class="{on: compositionMode === 'share'}" :aria-pressed="compositionMode === 'share'" @click="compositionMode = 'share'">关系占比</button></div></header>
          <ChartPanel :option="flowTypeOption" label="五类关系的年度堆叠面积图，支持数量与占比切换" height="410px" @chart-click="onCompositionClick" />
          <div class="genre-inline-tools"><label>查看全年证据 <select :value="selectedTrendGenre ? '' : selectedYear ?? ''" class="op-select" aria-label="关系构成年份证据" @change="clearDrill(); selectedYear = Number($event.target.value) || null"><option value="">选择年份</option><option v-for="y in chartYears" :key="y" :value="y">{{ y }}</option></select></label></div>
          <p class="op-note">占比以当年当前所选关系的事件总量为分母；无事件年份留空。图例只隐藏显示，不改变筛选分母。点击面积区域定位年份与关系。</p>
          <p class="op-note">风格借鉴、翻唱、采样、片段引用与歌词引用在原始图中方向相反，本视图统一为「来源 → 受影响者」并保留原始端点。</p>
        </section>
      </div>

      <section ref="evidenceEl" class="op-card genre-evidence">
        <header>
          <div class="genre-panel-heading"><span class="genre-panel-icon"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5" /></svg></span><div><h3>事件明细</h3><p>{{ formatCount(drillRows.length) }} 组记录，共 {{ formatCount(drillRows.reduce((sum, row) => sum + row.value, 0)) }} 条原始事件</p></div></div>
          <div class="genre-actions"><span class="genre-action-status" role="status">{{ notice }}</span><button class="op-btn" @click="copyText(scopeText)">复制条件</button><button class="op-btn genre-primary" :disabled="!drillRows.length" @click="exportEvidence"><AppIcon name="download" :size="15" />导出筛选证据</button><button v-if="conditionSummary" class="op-btn" @click="clearDrill">清除定位</button></div>
        </header>
        <p class="genre-evidence-scope">{{ scopeText }}</p>
        <div v-if="conditionSummary" class="genre-selection" role="status"><button v-if="selectedCell?.source" class="op-chip on" @click="removeCellCondition('source')">来源 {{ selectedCell.source }} ×</button><button v-if="selectedCell?.target" class="op-chip on" @click="removeCellCondition('target')">去向 {{ selectedCell.target }} ×</button><button v-if="selectedYear" class="op-chip on" @click="selectedYear = null">{{ selectedTrendGenre?.rolling ? Math.max(1975, selectedYear - 4) + '–' : '' }}{{ selectedYear }} 年 ×</button><button v-if="selectedTrendGenre" class="op-chip on" @click="selectedTrendGenre = null">{{ selectedTrendGenre.genre }} · {{ selectedTrendGenre.side === 'in' ? '流入' : '流出' }} ×</button><button v-if="selectedRelation" class="op-chip on" @click="selectedRelation = null">{{ EDGE_LABELS[selectedRelation] }} ×</button><span v-if="selectedTrendGenre">全部关系口径，独立于上方关系筛选</span></div>
        <div class="genre-inline-tools genre-table-tools"><label>搜索证据 <input v-model="evidenceSearch" type="search" class="op-input" placeholder="流派、关系、年份或边 ID"></label><label>排序 <select v-model="evidenceSort" class="op-select"><option value="count">事件数降序</option><option value="year">年份降序</option></select></label><button v-if="evidenceSearch" class="op-btn" @click="evidenceSearch = ''">清除搜索</button></div>
        <div class="op-scroll">
          <table class="op-table">
            <thead><tr><th scope="col" class="genre-detail-col">明细</th><th scope="col">来源</th><th scope="col">受影响流派</th><th scope="col">关系类型</th><th scope="col" class="num">年份</th><th scope="col" class="num">事件数</th></tr></thead>
            <tbody>
              <template v-for="flow in pageRows" :key="flowKey(flow)"><tr>
                <td class="genre-edge"><button class="genre-expand" :aria-label="expandedFlow === flowKey(flow) ? '收起明细' : `展开 ${flow.event_ids.length} 条事件：${flow.source} → ${flow.target}，${flow.year}`" :aria-expanded="expandedFlow === flowKey(flow)" @click="expandFlow(flow)"><span aria-hidden="true">›</span></button></td>
                <td>{{ flow.source }}</td><td>{{ flow.target }}<small class="genre-mobile-type">{{ EDGE_LABELS[flow.type] || flow.type }}</small></td>
                <td><span class="genre-relation"><i :style="{ background: FLOW_COLORS[flow.type] }" />{{ EDGE_LABELS[flow.type] || flow.type }}</span></td>
                <td class="num">{{ flow.year }}</td><td class="num">{{ flow.value }}</td>
              </tr>
              <tr v-if="expandedFlow === flowKey(flow)" class="genre-detail-row"><td colspan="6"><div class="genre-detail"><p v-if="detailLoading" role="status">正在按需加载作品与艺人名称…</p><div v-else-if="detailError" role="alert"><p>{{ detailError }}</p><button class="op-btn" @click="expandedFlow = null; expandFlow(flow)">重试实体加载</button></div><template v-else><p>展示方向：影响来源 → 受影响作品；原始引用边方向：借鉴者 → 来源。年份以受影响作品发行年为依据。</p><article v-for="id in flow.event_ids" :key="id" class="genre-event"><template v-if="eventById.get(id)"><div><b>{{ entity(eventById.get(id).source) }}</b><span class="genre-help">影响来源</span></div><span aria-hidden="true">→</span><div><b>{{ entity(eventById.get(id).target) }}</b><span class="genre-help">受影响实体 · {{ eventById.get(id).year }} 年</span></div><div class="genre-event-id"><code>{{ id }}</code><span>原始方向 #{{ eventById.get(id).raw_source }} → #{{ eventById.get(id).raw_target }}</span><button class="op-btn" @click="copyText(id)">复制 ID</button></div></template><p v-else>未找到事件 {{ id }}，请核对数据版本。</p></article></template></div></td></tr></template>
              <tr v-if="!drillRows.length"><td colspan="6" class="genre-empty">当前定位与关系筛选下没有事件。可清除定位，或调整分析范围。</td></tr>
            </tbody>
          </table>
        </div>
        <div class="genre-pagination"><span>{{ drillRows.length ? (evidencePage - 1) * pageSize + 1 : 0 }}–{{ Math.min(evidencePage * pageSize, drillRows.length) }} / {{ formatCount(drillRows.length) }} 组</span><div class="genre-actions"><label>每页 <select v-model="pageSize" class="op-select"><option :value="12">12 组</option><option :value="24">24 组</option><option :value="48">48 组</option></select></label><button class="op-btn" :disabled="evidencePage === 1" @click="evidencePage--">上一页</button><label>第 <input class="genre-page-number" type="number" aria-label="跳转页码" min="1" :max="pageCount" :value="evidencePage" @change="jumpToPage" @keydown.enter="$event.target.blur()"> / {{ pageCount }} 页</label><button class="op-btn" :disabled="evidencePage >= pageCount" @click="evidencePage++">下一页</button></div></div>
        <p class="op-note">展开一行可核对作品、引用方向和 <code>MC1_graph.json</code> 中的原始边 ID。</p>
      </section>

      <details class="genre-method">
        <summary>统计口径与数据缺口</summary>
        <dl>
          <dt>事件方向</dt><dd>来源 → 受影响者，只统计跨流派事件。引用记录无法证实艺人之间有私下合作。</dd>
          <dt>5 年滚动均值</dt><dd>取当年和之前四年的外向事件均值，数据起点按可用年数计算。明细列出窗口内的原始事件。</dd>
          <dt>受影响作品覆盖率</dt><dd>受影响的外部作品去重数 ÷ 当年外部流派发行作品数。分母缺失时留空。</dd>
          <dt>筛选范围</dt><dd>趋势图和从趋势图打开的证据涵盖全部关系。流向矩阵、关系构成和对应明细按所选关系统计。图内缩放后，点击“应用为分析时间窗”可同步其他视图。</dd>
          <dt>年度样本</dt><dd>年度统计排除了 {{ formatCount(issues.influence_chronology) }} 条时间顺序存疑的引用、1 条自环和 67 条无日期的艺人引用。结构数据保留这些记录。{{ formatCount(issues.notable_without_chart_year) }} 部上榜作品缺少登榜年份。</dd>
          <dt>扩散形态</dt><dd>全期有外向事件的年份共 {{ folkActiveYears }} 个。峰值年占 {{ (concentration * 100).toFixed(1) }}%，五年均值在 {{ trailingPeak?.year }} 年达到 {{ trailingPeak?.outbound_trailing_5y_mean }} 条。</dd>
          <dt>后期样本</dt><dd>2032 年及以后的记录占有日期外向事件的 {{ (lateShare * 100).toFixed(1) }}%。后期样本较少，判断长期影响时需结合其他证据。</dd>
        </dl>
      </details>
    </template>
  </div>
</template>

<style scoped>
.genre-workspace {
  font-family: "Segoe UI", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.6;
  --genre-display: "Noto Serif SC", "Songti SC", "STSong", Georgia, "SimSun", serif;
  --genre-blue: #3859ac; --genre-line: #dce4ed; --genre-muted: #536b82; --genre-surface: #f6f8fc; --genre-radius: 12px; color: #263e56; }
.genre-workspace ::selection { background: #cbdafa; color: #17324d; }
.genre-workspace input, .genre-workspace select { caret-color: var(--genre-blue); }
.genre-workspace .op-btn, .genre-workspace .op-input, .genre-workspace .op-select, .genre-workspace .op-chip { min-height: 32px; font-size: 13px; }
.genre-workspace .op-input { max-width: 100%; }
.genre-workspace .op-btn:disabled:hover { border-color: var(--genre-line); }
.genre-workspace section { scroll-margin-top: 24px; }
.genre-text-button { appearance: none; border: 0; padding: 6px 0; background: transparent; cursor: pointer; color: var(--genre-blue); font-size: 13px; text-align: left; text-decoration: underline; text-underline-offset: 4px; }
.genre-text-button:hover { color: #17324d; }
.genre-inline-tools { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 0 0 16px; font-size: 13px; }
.genre-inline-tools label { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.genre-inline-tools input[type=checkbox] { accent-color: var(--genre-blue); width: 16px; height: 16px; }
.genre-year-inputs input { width: 92px; padding: 6px 8px; font: inherit; border: 1px solid var(--genre-line); border-radius: 6px; color: #17324d; }
.genre-form-error { color: #a52f36; padding: 0 20px; font-size: 13px; }
.genre-picker summary { color: var(--genre-blue); cursor: pointer; font-size: 13px; min-height: 24px; }
.genre-picker-body { padding-top: 16px; display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.genre-picker-body > .op-chips { flex-basis: 100%; }
.genre-picker label { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.genre-workspace .genre-evidence > .genre-selection { margin-bottom: 16px; }
.genre-workspace .op-table td { font-variant-numeric: tabular-nums; font-size: 14px; line-height: 1.5; }
.genre-workspace .op-table th { color: #425d78; font-size: 13px; }
.genre-detail-row > td { padding: 0 !important; }
.genre-detail { padding: 16px; background: #f3f6fb; white-space: normal; }
.genre-detail p { margin-top: 0; font-size: 13px; color: #425d78; }
.genre-event { display: grid; grid-template-columns: minmax(0,1fr) 20px minmax(0,1fr) minmax(170px,.8fr); align-items: center; gap: 12px; padding: 16px 0; border-top: 1px solid #d9e2ed; }
.genre-event b { font-size: 13px; font-weight: 500; overflow-wrap: anywhere; }
.genre-event .genre-help { display: block; }
.genre-event-id { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; font-size: 12px; }
.genre-event-id code { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
.genre-method { margin-top: 24px; padding: 20px 0; border-top: 1px solid var(--genre-line); font-size: 13px; color: #425d78; scroll-margin-top: 24px; }
.genre-method summary { cursor: pointer; font-size: 16px; font-weight: 600; color: #17324d; }
.genre-method dl { display: grid; grid-template-columns: 150px 1fr; gap: 12px 24px; }
.genre-method dt { font-weight: 600; }
.genre-method dd { margin: 0; max-width: 80ch; }
.genre-skeleton { height: 100px; border-radius: 12px; background: #e7edf5; margin: 16px 0; }
.genre-skeleton.chart { height: 340px; }
.genre-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.genre-workspace .op-card { border-radius: var(--genre-radius); box-shadow: none; padding: 24px; }
.genre-workspace .op-card h3, .genre-network-head h3 { font-size: clamp(18px, 1.3vw, 21px); font-weight: 600; line-height: 1.45; }
.genre-workspace .op-card header { align-items: center; margin-bottom: 18px; }
.genre-workspace .op-card header p { font-size: 12px; margin-top: 5px; color: #718396; }
.genre-workspace :deep(.op-tool-label) { color: #546a81; font-size: 12px; min-width: 48px; }
.genre-workspace :deep(.op-chip) { border-radius: 5px; padding: 5px 10px; color: #60758b; }
.genre-workspace :deep(.op-chip.on) { background: #edf2ff; color: #3859ac; border-color: #c5d2f1; }
.genre-workspace :deep(.op-scrubber input) { accent-color: #5470c6; }
.genre-workspace .op-btn { border-radius: 5px; font-size: 12px; white-space: nowrap; }
.genre-workspace .op-btn:disabled { opacity: .4; cursor: default; }
.genre-workspace button:focus-visible, .genre-workspace :deep(button:focus-visible) { outline: 2px solid #5470c6; outline-offset: 3px; }
.genre-help, .genre-workspace .op-note, .genre-workspace .genre-pagination { color: var(--genre-muted); font-size: 13px; }
.genre-segment { display: flex; gap: 3px; padding: 4px; background: #f1f4f8; border-radius: 7px; flex-wrap: wrap; }
.genre-segment button { border: none; background: transparent; color: #60758b; font-size: 12px; padding: 7px 12px; border-radius: 5px; cursor: pointer; }
.genre-segment button.on { background: white; color: #3859ac; box-shadow: 0 1px 4px #17324d14; font-weight: 600; }
.genre-trend { margin-bottom: 18px; }
.genre-trend :deep(.trend-tip) { min-width: 170px; font-variant-numeric: tabular-nums; }
.genre-trend :deep(.trend-tip-title), .genre-trend :deep(.trend-tip-row) { display: grid; grid-template-columns: 1fr auto; align-items: baseline; gap: 3px 16px; }
.genre-trend :deep(.trend-tip-title) { padding-bottom: 7px; border-bottom: 1px solid #dce5e9; }
.genre-trend :deep(.trend-tip-title span), .genre-trend :deep(.trend-tip-row small) { font-size: 12px; color: #536b82; }
.genre-trend :deep(.trend-tip-row) { padding-top: 6px; }
.genre-trend :deep(.trend-tip-row small) { grid-column: 1 / -1; }
.genre-chart-foot { display: flex; justify-content: space-between; align-items: center; gap: 10px; font-size: 13px; color: var(--genre-muted); margin-top: 8px; flex-wrap: wrap; }
.genre-workspace .op-note { margin: 12px 0 0; line-height: 1.7; }
.genre-workspace .op-grid { gap: 18px; }
.genre-matrix-scroll { overflow-x: auto; }
.genre-matrix-all { min-width: 760px; }
.genre-selection { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; background: #eff4ff; padding: 9px 12px; border-radius: 6px; color: #3859ac; font-size: 12px; }
.genre-evidence { margin-top: 18px; scroll-margin-top: 24px; }
.genre-workspace .op-table { font-size: 12px; }
.genre-workspace .op-table th { background: #f6f8fc; padding: 12px; font-weight: 600; white-space: nowrap; }
.genre-workspace .op-table td { padding: 11px 12px; }
.genre-workspace .op-table tbody tr:hover { background: #f5f8ff; }
.genre-workspace .op-table tbody tr:nth-child(even) { background: #fbfcfe; }
.genre-relation { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.genre-relation i { height: 6px; width: 6px; border-radius: 50%; }
.genre-pagination { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-top: 14px; flex-wrap: wrap; font-size: 11px; color: #718396; }
.genre-empty { text-align: center; padding: 24px !important; font-size: 12px; color: #718396; }
.genre-workspace .op-card header p { color: var(--genre-muted); font-size: 13px; }
.genre-workspace .genre-segment button { font-size: 13px; min-height: 32px; }
.genre-workspace .op-btn { font-size: 13px; }
.genre-workspace :deep(.op-chip) { font-size: 13px; }
.genre-workspace .op-chart { min-width: 0; }
.genre-workspace .genre-evidence .genre-selection { font-size: 12px; }

.genre-mast { display: flex; justify-content: space-between; align-items: center; gap: 24px; padding: 12px 0 22px; border-bottom: 2px solid #253e56; }
.genre-mast h2 { margin: 0; color: #19354b; font-family: var(--genre-display); font-size: clamp(25px, 2.4vw, 37px); font-weight: 600; line-height: 1.3; text-wrap: balance; }
.genre-mast h2 span { white-space: nowrap; }
.genre-dataset { margin: 8px 0 6px; font-size: 15px; color: #4e6375; line-height: 1.5; }
.genre-peak, .genre-reset { border: 0; background: transparent; padding: 4px 0; color: #325779; cursor: pointer; font: inherit; font-size: 13px; }
.genre-peak span { margin-left: 3px; }
.genre-peak:hover, .genre-reset:hover { text-decoration: underline; text-underline-offset: 3px; }
.genre-tally { display: grid; flex-shrink: 0; min-width: 188px; padding-left: 24px; border-left: 1px solid #bdcbd6; }
.genre-tally > span { color: #40596f; font-size: 13px; }
.genre-tally .genre-scope { font-size: 12px; margin-top: 4px; }
.genre-filters { display: flex; flex-wrap: wrap; gap: 16px 32px; align-items: center; padding: 16px 0; margin-bottom: 18px; border-bottom: 1px solid #c7d3dc; }
.genre-period, .genre-relations { display: grid; gap: 6px; }
.genre-filter-line { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 28px; font-size: 13px; }
.genre-filters h3 { margin: 0 4px 0 0; font-size: 14px; font-weight: 600; }
.genre-year-inputs input { width: 68px; padding: 3px 5px; }
.genre-period :deep(.op-scrubber) { gap: 6px; }
.genre-period :deep(.op-scrubber .op-tool-label), .genre-period :deep(.op-scrubber strong) { display: none; }
.genre-period :deep(.op-scrubber input[type=range]) { width: 62px; }
.genre-period :deep(.op-scrubber .op-btn) { min-height: 28px; padding: 2px 6px; font-size: 12px; }
.genre-form-error { padding: 0; margin: 0; }
.genre-relations { padding-left: 24px; border-left: 1px solid var(--genre-line); }
.genre-relations .genre-text-button { padding: 0; }
.genre-relations .op-chips { gap: 4px; }
.genre-relations .op-chip.on { background: white; color: #253f57; border-color: #a8b8c9; }
.genre-relations .op-chip:not(.on) .dot { background: transparent !important; outline: 1px solid #9aabbb; }
.genre-reset { margin-left: auto; }
.genre-picker { margin: 0 0 12px; }
.genre-picker summary { width: fit-content; color: #3d576f; }
.genre-picker summary strong { margin-left: 4px; font-weight: 600; }
.genre-picker-body { border-top: 1px solid var(--genre-line); margin-top: 8px; padding: 10px 0; }
.genre-workspace .genre-evidence .op-scroll { max-height: min(70vh, 640px); border: 0; border-radius: 0; overflow: auto; }
.genre-workspace .genre-evidence thead th { position: sticky; top: 0; z-index: 1; background: #edf2f5; }
.genre-workspace .genre-evidence tbody td { padding-top: 3px; padding-bottom: 3px; }
.genre-workspace .genre-evidence tbody tr { cursor: default; }
.genre-workspace .genre-evidence tr:has(.genre-expand[aria-expanded=true]) { background: #eaf1fa; }
.genre-detail-col, .genre-edge { width: 52px; text-align: center !important; }
.genre-expand { width: 36px; height: 34px; border: 0; border-radius: 3px; background: transparent; cursor: pointer; color: #375e81; }
.genre-expand span { display: inline-block; font: 23px/1 system-ui, sans-serif; }
.genre-expand:hover, .genre-expand:focus-visible { background: #e4ecf6; }
.genre-expand[aria-expanded=true] span { transform: rotate(90deg); }
.genre-mobile-type { display: none; }
.genre-table-tools input { width: min(32vw, 280px); }
.genre-pagination label { display: inline-flex; gap: 6px; align-items: center; }
.genre-rank-caption { margin: 0 0 10px; color: var(--genre-muted); font-size: 13px; }
.genre-rankings { padding-top: 16px; margin-top: 14px; border-top: 1px solid var(--genre-line); }
.genre-rankings h4 { margin: 0; font-size: 14px; }
.genre-rank-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.genre-rank-columns ol { list-style: none; padding: 0; margin: 8px 0 0; }
.genre-rank { display: flex; justify-content: space-between; align-items: center; gap: 8px; width: 100%; min-height: 41px; padding: 7px 2px; border: 0; border-top: 1px solid #ccd7df; background: transparent; text-align: left; font: inherit; font-size: 14px; color: #284257; cursor: pointer; }
.genre-rank strong { color: #29557b; font-variant-numeric: tabular-nums; }
.genre-rank:hover span, .genre-rank:focus-visible span { text-decoration: underline; text-underline-offset: 3px; }
.genre-focal-totals { display: flex; gap: 30px; margin: 8px 0 0; }
.genre-focal-totals dt { font-size: 13px; }
.genre-focal-totals dd { margin: 1px 0 0; font-size: clamp(30px, 2.6vw, 38px); font-weight: 600; line-height: 1.15; font-variant-numeric: lining-nums tabular-nums; color: #183950; }
.genre-focal-totals dd small { font-size: 13px; font-weight: 400; }
.genre-network-head, .genre-trend-fact { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px 24px; }
.genre-network-head { padding: 14px 0; margin: 22px 0 12px; border-top: 2px solid #284257; }
.genre-network-head h3, .genre-trend-fact h4 { color: #183950; margin: 0; }
.genre-network-head p, .genre-trend-fact p { margin: 3px 0 0; font-size: 14px; }
.genre-trend-fact { margin-top: 16px; border-top: 1px solid var(--genre-line); padding-top: 14px; }
.genre-trend-fact strong { color: #913916; }
.genre-workspace .genre-trend > header { justify-content: flex-start; column-gap: 24px; }
.genre-flow-sides { display: flex; justify-content: space-between; font-size: 13px; color: var(--genre-muted); }
.genre-flow-sides span:last-child { width: 151px; }
.genre-action-status, .genre-evidence-scope { font-size: 12px; color: #40596f; }
.genre-action-status:empty { display: none; }
.genre-page-number { width: 58px; border: 1px solid var(--genre-line); border-radius: 4px; color: inherit; padding: 6px; }
.genre-page-number:focus-visible { outline: 2px solid var(--genre-blue); }
/* Annual trajectory: one analytical canvas with a clearly separated control rail. */
.genre-workspace .genre-trend {
  --trend-ink: #193b50;
  --trend-border: #e2eaf0;
  padding: 28px 30px 22px;
  border: 1px solid var(--trend-border);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 2px 4px #193b5003, 0 12px 36px #193b5006;
}
.genre-workspace .genre-trend > .genre-trend-header { justify-content: space-between; gap: 20px; margin-bottom: 24px; flex-wrap: wrap; }
.genre-trend-heading { display: flex; align-items: center; gap: 14px; }
.genre-trend-icon { display: grid; place-items: center; flex-shrink: 0; width: 46px; height: 46px; border-radius: 13px; color: #2a607a; background: #edf4f7; border: 1px solid #e0ebf0; }
.genre-workspace .genre-trend h3 { color: var(--trend-ink); font-size: 21px; font-weight: 650; letter-spacing: -.4px; }
.genre-workspace .genre-trend-header p { margin-top: 4px; font-size: 12px; color: #788b99; }
.genre-trend .genre-segment { background: #f1f5f8; border: 1px solid #e8eef3; padding: 4px; gap: 2px; border-radius: 10px; }
.genre-workspace .genre-trend .genre-segment button { font-size: 12px; min-height: 35px; padding: 8px 13px; border-radius: 7px; transition: background .18s, color .18s, box-shadow .18s; }
.genre-trend .genre-segment button:hover { color: #193b50; background: #e8eff4; }
.genre-trend .genre-segment button.on { color: #fff; background: #214c65; box-shadow: 0 2px 5px #193b5024; }
.genre-trend-toolbar { position: relative; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px 24px; padding: 14px 0; border-top: 1px solid #edf1f5; border-bottom: 1px solid #edf1f5; }
.genre-trend .genre-picker { margin: 0; }
.genre-trend .genre-picker summary { display: flex; align-items: center; gap: 9px; min-height: 36px; padding: 6px 11px; border: 1px solid #dfe8ee; border-radius: 8px; background: #fff; font-size: 12px; color: #627b8d; list-style: none; transition: border-color .18s, background .18s; }
.genre-trend .genre-picker summary::-webkit-details-marker { display: none; }
.genre-trend .genre-picker summary:hover, .genre-trend .genre-picker[open] summary { background: #f5f9fb; border-color: #9db7c8; }
.genre-trend .genre-picker summary strong { margin: 0 8px 0 3px; font-size: 12px; color: #214c65; font-weight: 600; }
.genre-picker-chevron { font-size: 17px; line-height: 1; transition: transform .18s; }
.genre-picker[open] .genre-picker-chevron { transform: rotate(180deg); }
.genre-trend .genre-picker-body { position: absolute; z-index: 5; left: 0; right: 0; top: calc(100% + 8px); max-height: 330px; overflow-y: auto; margin: 0; padding: 20px; border: 1px solid #dce6ee; border-radius: 12px; background: #fff; box-shadow: 0 16px 45px #193b5026; }
.genre-trend .genre-inline-tools { padding: 0; gap: 20px; font-size: 12px; color: #627b8d; }
.genre-trend .genre-mean-toggle { gap: 7px; cursor: pointer; }
.genre-trend .genre-mean-toggle input { width: 15px; height: 15px; accent-color: #245774; }
.genre-trend .genre-year-locator { padding-left: 20px; border-left: 1px solid #e1e8ee; gap: 10px; }
.genre-workspace .genre-trend .op-select { min-height: 36px; padding: 6px 10px; border-color: #dfe8ee; border-radius: 7px; color: #294a62; background-color: #fff; font-size: 12px; }
.genre-trend-canvas { padding-top: 20px; }
.genre-chart-caption { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 0 0 6px; font-size: 12px; color: #78909f; }
.genre-chart-caption > span:first-child { color: #476477; font-weight: 600; }
.genre-trend .genre-chart-foot { margin-top: 14px; gap: 16px; font-size: 12px; }
.genre-observation { display: flex; align-items: center; gap: 10px; color: #6b8294; }
.genre-observation > svg { color: #8ba1b1; flex-shrink: 0; }
.genre-observation strong { color: #31566d; font-weight: 600; font-variant-numeric: tabular-nums; margin-left: 3px; }
.genre-observation small { display: inline-block; margin-left: 12px; padding-left: 12px; border-left: 1px solid #dce5ec; font-size: 11px; color: #8799a7; }
.genre-workspace .genre-trend .op-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 34px; border-radius: 7px; padding: 6px 11px; font-size: 12px; transition: border-color .18s, background .18s; }
.genre-workspace .genre-trend .genre-apply-window { background: #214c65; border-color: #214c65; color: #fff; }
.genre-workspace .genre-trend .genre-apply-window:disabled { background: #eff3f6; border-color: #e5ecf1; color: #96a8b5; opacity: 1; }
.genre-workspace .genre-trend .genre-restore-window { border-color: transparent; background: transparent; color: #627b8d; }
.genre-workspace .genre-trend .genre-restore-window:hover { background: #f1f6f9; color: #214c65; }
.genre-trend .genre-selection { margin-top: 14px; }
.genre-trend .genre-trend-fact { margin-top: 22px; padding: 17px 20px; background: #f4f8fa; border: 1px solid #e8eff3; border-radius: 11px; gap: 14px; }
.genre-insight-copy { display: flex; align-items: center; gap: 14px; }
.genre-insight-icon { color: #5d8398; display: grid; place-items: center; flex-shrink: 0; width: 35px; height: 35px; border-right: 1px solid #d8e4eb; padding-right: 14px; box-sizing: content-box; }
.genre-trend .genre-trend-fact h4 { font-size: 13px; font-weight: 600; }
.genre-trend .genre-trend-fact p { margin-top: 3px; font-size: 12px; color: #708596; line-height: 1.7; }
.genre-trend .genre-trend-fact strong { color: #c26643; font-weight: 650; }
.genre-trend .genre-trend-fact .genre-text-button { display: inline-flex; align-items: center; gap: 12px; font-size: 12px; font-weight: 600; color: #315c75; text-decoration: none; white-space: nowrap; }
.genre-trend .genre-trend-fact .genre-text-button:hover { color: #c26643; }
.genre-trend summary:focus-visible, .genre-trend select:focus-visible, .genre-trend input:focus-visible { outline: 2px solid #377898; outline-offset: 3px; }
@media (max-width: 1100px) {
  .genre-trend .genre-segment { width: 100%; }
  .genre-trend .genre-segment button { flex: 1; }
}
@media (max-width: 600px) {
  .genre-workspace .genre-trend { padding: 20px 14px 14px; border-radius: 14px; }
  .genre-workspace .genre-trend > .genre-trend-header { gap: 18px; margin-bottom: 16px; }
  .genre-workspace .genre-trend h3 { font-size: 18px; }
  .genre-trend-heading { gap: 10px; }
  .genre-trend-icon { width: 40px; height: 40px; border-radius: 10px; }
  .genre-trend .genre-segment button { flex: 1 1 40%; }
  .genre-trend-toolbar { gap: 12px; }
  .genre-trend .genre-inline-tools { width: 100%; justify-content: space-between; gap: 10px; }
  .genre-trend .genre-year-locator { padding-left: 0; border: 0; gap: 7px; }
  .genre-trend .genre-picker-body { padding: 14px; max-height: 340px; }
  .genre-chart-caption { font-size: 11px; }
  .genre-trend-canvas > .op-chart { height: 300px !important; }
  .genre-trend .genre-chart-foot { align-items: flex-start; gap: 12px; }
  .genre-observation small { display: block; border: 0; margin: 0; padding: 0; }
  .genre-trend .genre-actions { gap: 5px; }
  .genre-trend .genre-trend-fact { margin-top: 16px; padding: 14px; }
  .genre-insight-copy { align-items: flex-start; gap: 10px; }
  .genre-insight-icon { width: 20px; height: 28px; padding-right: 10px; }
  .genre-trend .genre-trend-fact .genre-text-button { margin-left: 41px; }
}
@media (prefers-reduced-motion: reduce) {
  .genre-trend button, .genre-trend summary, .genre-picker-chevron { transition: none !important; }
}
@media (min-width: 601px) {
  .genre-period { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; }
  .genre-evidence th.num { width: 8%; }
}
@media (max-width: 860px) {
  .genre-filters { column-gap: 16px; }
  .genre-relations { border: 0; padding-left: 0; }
}
@media (max-width: 1100px) {
  .genre-workspace .op-grid.even { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .genre-mast { flex-wrap: wrap; gap: 14px; padding: 6px 0 14px; }
  .genre-tally { width: 100%; min-width: 0; display: grid; gap: 4px; border: 0; padding: 0; }
  .genre-tally .genre-focal-totals { margin: 0; gap: 16px; }
  .genre-tally .genre-focal-totals dd { font-size: 26px; }
  .genre-tally .genre-scope { margin: 0; }
  .genre-filters { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
  .genre-relations { grid-column: 1 / -1; }
  .genre-reset { grid-column: 2; grid-row: 1; align-self: start; }
  .genre-period :deep(.op-scrubber) { flex-wrap: wrap; }
  .genre-period :deep(.op-scrubber input[type=range]) { width: 47px; }
  .genre-period :deep(.op-scrubber .op-btn) { min-height: 36px; }
  .genre-rank-columns { gap: 14px; }
  .genre-rank { font-size: 13px; }
  .genre-mobile-type { display: block; color: var(--genre-muted); font-size: 12px; }
  .genre-expand { width: 100%; min-height: 42px; }
  .genre-workspace .op-btn, .genre-workspace .op-chip { min-height: 40px; }
  .genre-table-tools input { width: min(56vw, 260px); }
  .genre-workspace input, .genre-workspace select { font-size: 16px !important; }
  .genre-workspace .genre-inline-tools { gap: 12px 8px; }
  .genre-method dl { grid-template-columns: 1fr; gap: 8px; }
  .genre-method dd { margin-bottom: 12px; }
  .genre-event { grid-template-columns: minmax(0,1fr) 16px minmax(0,1fr); }
  .genre-event-id { grid-column: 1 / -1; }
  .genre-workspace .op-card { padding: 16px 12px; }
  .genre-segment { width: 100%; }
  .genre-segment button { flex: 1 1 40%; }
  .genre-workspace .op-table { min-width: 0; width: 100%; table-layout: fixed; }
  .genre-workspace .op-table th, .genre-workspace .op-table td { padding: 8px 5px; font-size: 13px; white-space: normal; overflow-wrap: anywhere; }
  .genre-workspace .op-table th:nth-child(1) { width: 12%; }
  .genre-workspace .op-table th:nth-child(2), .genre-workspace .op-table th:nth-child(3) { width: 27%; }
  .genre-workspace .op-table th:nth-child(4), .genre-workspace .op-table td:nth-child(4) { display: none; }
  .genre-workspace .op-table th:nth-child(5), .genre-workspace .op-table th:nth-child(6) { width: 17%; }
  .genre-matrix-scroll > div { min-width: 520px; }
}
/* Module two shares the annual trajectory's marine palette and component system. */
.genre-workspace {
  --genre-blue: #315c75;
  --genre-line: #e2eaf0;
  --genre-muted: #708596;
  --genre-surface: #f4f8fa;
  --genre-radius: 18px;
  color: #294a62;
}
.genre-workspace ::selection { background: #d4e6ef; color: #193b50; }
.genre-mast { padding: 16px 0 26px; border-bottom: 0; gap: 28px; }
.genre-mast h2 { font-family: inherit; font-size: clamp(25px, 2.2vw, 34px); font-weight: 650; letter-spacing: -.8px; color: #193b50; }
.genre-dataset { margin-top: 10px; font-size: 13px; color: #708596; }
.genre-peak { display: inline-flex; align-items: center; gap: 3px; margin-top: 4px; font-size: 12px; color: #416c84; }
.genre-peak strong { color: #c26643; }
.genre-tally { border: 1px solid #e1eaf0; border-radius: 14px; padding: 16px 22px; background: #edf4f7; min-width: 270px; }
.genre-tally .genre-scope { margin: 0; color: #708596; font-size: 11px; }
.genre-focal-totals { gap: 36px; margin-top: 10px; }
.genre-focal-totals dt { color: #627d8f; font-size: 12px; }
.genre-focal-totals dd { margin-top: 4px; color: #214c65; font-size: 34px; font-weight: 600; letter-spacing: -1px; }
.genre-focal-totals dd small { font-size: 11px; margin-left: 3px; color: #78909f; letter-spacing: 0; }
.genre-filters { padding: 16px 22px; margin-bottom: 22px; border: 1px solid #e2eaf0; border-radius: 12px; background: #fff; gap: 14px 24px; }
.genre-filters h3 { font-size: 12px; color: #627b8d; font-weight: 500; margin-right: 6px; }
.genre-year-inputs { color: #91a3af; }
.genre-year-inputs input { min-height: 34px; width: 76px; padding: 5px 8px; border-radius: 7px; border-color: #dfe8ee; font-size: 12px; background: #f9fbfc; color: #294a62; font-variant-numeric: tabular-nums; }
.genre-reset { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: #627b8d; }
.genre-period :deep(.op-scrubber input) { accent-color: #315c75; }
.genre-period :deep(.op-scrubber .op-btn) { border-color: #e2eaf0; border-radius: 7px; color: #627b8d; min-height: 32px; padding: 4px 9px; }
.genre-period :deep(.op-scrubber .op-btn:hover) { background: #edf4f7; color: #214c65; border-color: #b9ceda; }
.genre-workspace .op-card { padding: 28px 30px 22px; border: 1px solid #e2eaf0; border-radius: 18px; background: #fff; box-shadow: 0 2px 4px #193b5003, 0 12px 36px #193b5006; }
.genre-workspace .op-card > header { justify-content: space-between; align-items: center; gap: 18px; flex-wrap: wrap; margin-bottom: 24px; }
.genre-workspace .op-card h3, .genre-network-head h3 { color: #193b50; font-size: 19px; font-weight: 650; letter-spacing: -.4px; }
.genre-workspace .genre-trend h3 { font-size: 21px; }
.genre-workspace .op-card header p { margin-top: 4px; font-size: 12px; color: #788b99; line-height: 1.7; }
.genre-panel-heading { display: flex; align-items: center; gap: 14px; min-width: 0; }
.genre-panel-icon { display: grid; place-items: center; flex-shrink: 0; width: 46px; height: 46px; border-radius: 13px; color: #2a607a; background: #edf4f7; border: 1px solid #e0ebf0; }
.genre-workspace .genre-segment { background: #f1f5f8; border: 1px solid #e8eef3; padding: 4px; gap: 2px; border-radius: 10px; }
.genre-workspace .genre-segment button { font-size: 12px; min-height: 35px; padding: 8px 13px; border-radius: 7px; color: #627b8d; transition: background .18s, color .18s, box-shadow .18s; }
.genre-workspace .genre-segment button:hover { color: #193b50; background: #e8eff4; }
.genre-workspace .genre-segment button.on { color: #fff; background: #214c65; box-shadow: 0 2px 5px #193b5024; }
.genre-workspace .op-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 34px; border: 1px solid #dfe8ee; border-radius: 7px; padding: 6px 11px; font-size: 12px; background: #fff; color: #476b81; transition: background .18s, border-color .18s; }
.genre-workspace .op-btn:hover:enabled { background: #f1f6f9; border-color: #b9ceda; }
.genre-workspace .op-btn[aria-pressed=true] { background: #edf4f7; border-color: #91afc0; color: #214c65; }
.genre-workspace .op-btn.genre-primary { color: #fff; background: #214c65; border-color: #214c65; }
.genre-workspace .op-btn.genre-primary:hover:enabled { background: #193b50; }
.genre-workspace .genre-trend .genre-apply-window:hover:enabled { background: #193b50; border-color: #193b50; }
.genre-workspace .op-btn:disabled { background: #f3f6f8; border-color: #e5ecf1; color: #99aab6; opacity: 1; cursor: default; }
.genre-workspace .op-input, .genre-workspace .op-select, .genre-page-number { min-height: 36px; border: 1px solid #dfe8ee; border-radius: 7px; padding: 6px 10px; background: #fff; color: #294a62; font-size: 12px; }
.genre-workspace .op-input::placeholder { color: #9aabb7; }
.genre-workspace .op-input:focus-visible, .genre-workspace .op-select:focus-visible, .genre-workspace button:focus-visible, .genre-workspace summary:focus-visible { outline: 2px solid #377898; outline-offset: 3px; }
.genre-inline-tools { color: #627b8d; font-size: 12px; gap: 12px 16px; }
.genre-inline-tools input[type=checkbox] { width: 15px; height: 15px; accent-color: #245774; }
.genre-matrix > .genre-inline-tools, .genre-table-tools { padding: 14px 0; margin-bottom: 18px; border-top: 1px solid #edf1f5; border-bottom: 1px solid #edf1f5; }
.genre-matrix > .genre-inline-tools > label:last-child { flex-basis: 100%; }
.genre-matrix > .genre-inline-tools .op-input { width: min(280px, 70%); }
.genre-composition > .genre-inline-tools { padding: 14px 0; margin-top: 14px; border-top: 1px solid #edf1f5; border-bottom: 1px solid #edf1f5; }
.genre-network-head { padding: 6px 2px; margin: 30px 0 18px; border: 0; gap: 18px 30px; }
.genre-network-head p { font-size: 12px; color: #788b99; margin-top: 4px; }
.genre-relations { border: 0; padding-left: 0; gap: 9px; }
.genre-relations .genre-filter-line { font-size: 11px; color: #78909f; min-height: 0; }
.genre-relations .op-chips { gap: 6px; }
.genre-workspace .op-chip { padding: 6px 10px; font-size: 12px; border-radius: 7px; border-color: #dfe8ee; color: #627b8d; transition: background .18s, border-color .18s; }
.genre-workspace .op-chip.on { background: #edf4f7; border-color: #c2d7e2; color: #315c75; }
.genre-workspace .op-chip:hover:enabled { border-color: #91afc0; }
.genre-workspace .op-chip .dot { width: 6px; height: 6px; }
.genre-workspace .op-grid { gap: 22px; align-items: start; }
.genre-workspace .op-note { padding-top: 12px; margin-top: 12px; color: #7a8f9e; font-size: 12px; line-height: 1.8; }
.genre-flow-sides { padding: 12px 0; border-top: 1px solid #edf1f5; font-size: 12px; color: #708596; }
.genre-rankings { margin-top: 22px; padding-top: 18px; border-color: #e8eef3; }
.genre-rank-caption { font-size: 11px; color: #8a9daa; margin-bottom: 14px; }
.genre-rank-columns { gap: 24px; }
.genre-rank-columns h4 { color: #31566d; font-size: 12px; font-weight: 600; }
.genre-rank { min-height: 44px; border-color: #edf1f5; font-size: 12px; padding: 10px 0; color: #627b8d; }
.genre-rank strong { color: #214c65; font-size: 13px; font-weight: 600; }
.genre-rank:hover { color: #214c65; background: #f8fbfc; }
.genre-selection { background: #edf4f7; border: 1px solid #dce8ef; color: #315c75; border-radius: 8px; gap: 8px; padding: 10px 12px; font-size: 12px; }
.genre-evidence { margin-top: 22px; }
.genre-evidence-scope { padding: 11px 14px; background: #f4f8fa; border-radius: 8px; color: #708596; font-size: 11px; line-height: 1.8; }
.genre-evidence .genre-table-tools { margin-top: 18px; }
.genre-workspace .genre-evidence .op-scroll { border: 1px solid #e5edf2; border-radius: 10px; }
.genre-workspace .genre-evidence thead th { background: #edf4f7; color: #5d7c90; padding: 13px 12px; font-size: 11px; font-weight: 600; border-color: #e5edf2; }
.genre-workspace .genre-evidence tbody td { padding: 8px 12px; font-size: 12px; color: #476477; border-color: #edf2f5; }
.genre-workspace .op-table tbody tr:nth-child(even) { background: #fafcfd; }
.genre-workspace .op-table tbody tr:hover { background: #f1f7fa; }
.genre-workspace .genre-evidence tr:has(.genre-expand[aria-expanded=true]) { background: #edf4f7; }
.genre-workspace .genre-evidence td.num:last-child { font-weight: 650; color: #214c65; }
.genre-expand { color: #6f91a6; border-radius: 7px; }
.genre-expand:hover, .genre-expand:focus-visible { background: #dceaf1; color: #214c65; }
.genre-detail { padding: 18px 20px; background: #f4f8fa; }
.genre-detail p { color: #708596; font-size: 12px; }
.genre-event { border-color: #dfeaf0; }
.genre-event b { color: #31566d; font-size: 12px; }
.genre-event-id code { background: #e5eef3; color: #315c75; }
.genre-pagination { padding: 18px 0 0; margin-top: 0; font-size: 12px; color: #7a8f9e; gap: 14px; }
.genre-pagination .genre-actions { gap: 10px; }
.genre-page-number { width: 56px; font-variant-numeric: tabular-nums; }
.genre-method { padding: 20px 24px; margin: 24px 0 0; border: 1px solid #e2eaf0; border-radius: 12px; background: #fff; font-size: 12px; color: #708596; }
.genre-method summary { color: #31566d; font-size: 13px; font-weight: 600; }
.genre-method dl { margin-top: 22px; gap: 16px 24px; line-height: 1.9; }
.genre-method dt { color: #476b81; font-weight: 600; }
.genre-empty { background: #f8fbfc; color: #78909f; border-radius: 8px; }
@media (max-width: 1300px) and (min-width: 1101px) {
  .genre-workspace .op-grid > .op-card > header .genre-segment { width: 100%; }
  .genre-workspace .op-grid > .op-card > header .genre-segment button { flex: 1; }
}
@media (max-width: 860px) {
  .genre-mast { flex-wrap: wrap; }
  .genre-tally { width: 100%; }
  .genre-network-head { align-items: flex-start; }
  .genre-pagination { align-items: flex-start; }
}
@media (max-width: 600px) {
  .genre-mast { gap: 18px; padding: 10px 0 18px; }
  .genre-mast h2 { font-size: 25px; line-height: 1.45; letter-spacing: -.5px; }
  .genre-dataset { font-size: 12px; line-height: 1.8; }
  .genre-tally { padding: 14px 16px; min-width: 0; }
  .genre-tally .genre-focal-totals { margin-top: 10px; gap: 36px; }
  .genre-tally .genre-focal-totals dd { font-size: 30px; }
  .genre-filters { padding: 14px; border-radius: 12px; margin-bottom: 18px; gap: 12px; }
  .genre-reset { font-size: 11px; gap: 4px; }
  .genre-year-inputs { gap: 6px; }
  .genre-year-inputs input { width: 70px; }
  .genre-period :deep(.op-scrubber) { gap: 5px; }
  .genre-period :deep(.op-scrubber .op-btn) { min-height: 36px; padding: 4px 8px; }
  .genre-workspace .op-card { padding: 20px 14px 14px; border-radius: 14px; }
  .genre-workspace .op-card > header { gap: 16px; margin-bottom: 18px; }
  .genre-workspace .op-card h3, .genre-network-head h3 { font-size: 17px; }
  .genre-workspace .genre-trend h3 { font-size: 18px; }
  .genre-panel-heading { gap: 10px; }
  .genre-panel-icon { width: 40px; height: 40px; border-radius: 10px; }
  .genre-workspace .op-card header p { font-size: 11px; }
  .genre-workspace .genre-segment button { min-height: 38px; font-size: 11px; padding: 8px 10px; }
  .genre-workspace .op-btn, .genre-workspace .op-chip { min-height: 40px; }
  .genre-network-head { margin-top: 24px; gap: 16px; }
  .genre-relations { width: 100%; }
  .genre-workspace .op-grid { gap: 18px; }
  .genre-workspace .op-grid > .op-card .genre-segment button { flex: 1; }
  .genre-evidence { margin-top: 18px; }
  .genre-workspace .genre-evidence tbody td, .genre-workspace .genre-evidence thead th { padding: 8px 5px; font-size: 11px; }
  .genre-evidence-scope { padding: 10px 12px; }
  .genre-table-tools label { width: 100%; }
  .genre-table-tools input { flex: 1; min-width: 0; width: 0; }
  .genre-pagination .genre-actions { gap: 8px; }
  .genre-pagination .op-btn { padding: 6px 8px; }
  .genre-method { padding: 17px 16px; margin-top: 18px; }
  .genre-method dl { margin-top: 18px; gap: 6px; }
  .genre-detail { padding: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  .genre-workspace button { transition: none !important; }
}
</style>
