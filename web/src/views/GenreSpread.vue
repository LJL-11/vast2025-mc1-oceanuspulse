<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import ChartPanel from '../components/ChartPanel.vue'
import GenreCarta from '../components/GenreCarta.vue'
import GenreChronicle from '../components/GenreChronicle.vue'
import GenreCitationField from '../components/GenreCitationField.vue'
import GenreRelationRecord from '../components/GenreRelationRecord.vue'
import GenreDotMatrix from '../components/GenreDotMatrix.vue'
import GenreTypeRecords from '../components/GenreTypeRecords.vue'
import GenreAffectedArtists from '../components/GenreAffectedArtists.vue'
import GenreSectionSky from '../components/GenreSectionSky.vue'
import JournalPager from '../components/JournalPager.vue'
import TimeScrubber from '../components/TimeScrubber.vue'
import FilterPanel from '../components/FilterPanel.vue'
import AppIcon from '../components/AppIcon.vue'
import { FLOW_TYPES, EDGE_LABELS, formatCount } from '../lib/palette'
import { voiceColors as FLOW_COLORS, directionColors as FLOW_TONES, scoreGenreColor as genreColor,
  chartText as CHART_MUTED, chartGrid as CHART_GRID } from '../lib/genreScorePalette'
import '../styles/genre-score.css'

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const trends = ref(null)
const flows = ref(null)
const overview = ref(null)
const selectedCell = ref(null)
const selectedYear = ref(null)
const selectedGenre = ref('')
const selectedType = ref('')
const selectedDirection = ref('')
const selectedArtist = ref(null)
const trendMode = ref('spread')
const artistsOpen = ref(false)
const matrixScope = ref('focus')
const typeScope = ref('out')
const typeMode = ref('records')
const showAllLanes = ref(store.focusGenres.length < 2)
const evidencePanel = ref(null)
const evidenceLimit = ref(40)

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
const genreColors = computed(() => Object.fromEntries(allGenres.value.map((name, index) => [name, genreColor(index)])))
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
function highlightGenre(event) {
  focusGenre(event.target.value)
}
function focusGenre(genre) {
  focusGenres.value = [genre, ...focusGenres.value.filter(name => name !== genre)]
}
async function inspectEvidence() {
  await nextTick()
  evidencePanel.value?.scrollIntoView({
    block: 'start',
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
  })
}

const rowsInWindow = computed(() => (trends.value?.rows || [])
  .filter(row => row.year >= yearRange.value[0] && row.year <= yearRange.value[1]))
const chartYears = computed(() => [...new Set(rowsInWindow.value.map(row => row.year))].sort((a, b) => a - b))
const rowLookup = computed(() => new Map(rowsInWindow.value.map(row => [`${row.genre}|${row.year}`, row])))
const isRatio = computed(() => metric.value === 'external_work_coverage')
const chartTooltip = { trigger: 'axis', confine: true, backgroundColor: '#15253b', borderColor: '#536d86',
  textStyle: { color: '#edf4ff' }, axisPointer: { lineStyle: { color: '#accde7' } } }

const trendOption = computed(() => ({
  tooltip: chartTooltip,
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
    lineStyle: { width: index === 0 ? 2.8 : 1.7, color: genreColors.value[genre] },
    itemStyle: { color: genreColors.value[genre] },
    areaStyle: index === 0 ? { color: genreColors.value[genre], opacity: .13 } : undefined,
    data: chartYears.value.map(year => rowLookup.value.get(`${genre}|${year}`)?.[metric.value] ?? null),
  })),
}))

const datedFlows = computed(() => (flows.value?.flows || []).filter(flow => flow.year != null && flow.source !== flow.target))
const filteredFlows = computed(() => datedFlows.value.filter(flow =>
  flow.year >= yearRange.value[0]
  && flow.year <= yearRange.value[1]
  && visibleFlowTypes.value.includes(flow.type)
))
const citationExtent = computed(() => [overview.value.year_fields.release_year.min, overview.value.meta.cutoff_year])
const focusAllFlows = computed(() => datedFlows.value.filter(flow => flow.source === featuredGenre.value || flow.target === featuredGenre.value))
const focusFlows = computed(() => filteredFlows.value.filter(flow => flow.source === featuredGenre.value || flow.target === featuredGenre.value))
const focusSummary = computed(() => {
  const years = new Map()
  for (const flow of focusFlows.value) {
    if (flow.source === featuredGenre.value) years.set(flow.year, (years.get(flow.year) ?? 0) + flow.value)
  }
  const peak = [...years].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0]
  return { activeYears: years.size, peak }
})
const relationFlows = computed(() => selectedYear.value == null ? filteredFlows.value
  : filteredFlows.value.filter(flow => flow.year === selectedYear.value))
const artistFlows = computed(() => relationFlows.value.filter(flow => flow.source === featuredGenre.value))
const typeFlows = computed(() => typeScope.value === 'all' ? filteredFlows.value
  : focusFlows.value.filter(flow => (typeScope.value === 'in' ? flow.target : flow.source) === featuredGenre.value))
const matrixGenres = computed(() => {
  const totals = new Map()
  for (const flow of matrixScope.value === 'all' ? filteredFlows.value : focusFlows.value) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value)
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value)
  }
  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1]).map(entry => entry[0])
  return [...new Set([...focusGenres.value, 'Oceanus Folk', ...ranked])].slice(0, 12)
})
const flowTypeOption = computed(() => ({
  tooltip: chartTooltip,
  legend: { type: 'scroll', top: 0, textStyle: { fontSize: 11, color: CHART_MUTED }, pageIconColor: '#a8d4ff', pageTextStyle: { color: CHART_MUTED } },
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
    data: chartYears.value.map(year => typeFlows.value
      .filter(flow => flow.type === type && flow.year === year)
      .reduce((sum, flow) => sum + flow.value, 0)),
  })),
}))

function onTrendClick(params) {
  selectedArtist.value = null
  selectedCell.value = null
  selectedType.value = ''
  selectedDirection.value = ''
  selectedYear.value = chartYears.value[params.dataIndex] ?? null
  selectedGenre.value = params.seriesName
}
function chooseMapYear({ year, genre, direction = '' }) {
  selectedArtist.value = null
  selectedCell.value = null
  selectedType.value = ''
  selectedDirection.value = direction
  selectedYear.value = year
  selectedGenre.value = genre
}
function choosePair(source, target, year = null, type = null) {
  selectedArtist.value = null
  selectedType.value = ''
  selectedDirection.value = ''
  if (year == null || year !== selectedYear.value) selectedGenre.value = ''
  selectedYear.value = year
  selectedCell.value = { source, target, type }
}
function chooseCitation(flow) {
  choosePair(flow.source, flow.target, flow.year, flow.type)
}
function chooseTypeYear({ type, year }) {
  selectedCell.value = null
  selectedArtist.value = null
  selectedGenre.value = typeScope.value === 'all' ? '' : featuredGenre.value
  selectedDirection.value = typeScope.value === 'all' ? '' : typeScope.value
  selectedType.value = type
  selectedYear.value = year
}
function chooseArtist(artist) {
  selectedArtist.value = artist
  selectedCell.value = null
  selectedGenre.value = ''
  selectedDirection.value = ''
  selectedType.value = ''
}
function clearEvidence() {
  selectedArtist.value = null
  selectedCell.value = null
  selectedYear.value = null
  selectedGenre.value = ''
  selectedType.value = ''
  selectedDirection.value = ''
}
watch([yearRange, focusGenres, visibleFlowTypes, metric], clearEvidence)
watch(typeScope, clearEvidence)
watch(focusGenres, genres => { if (genres.length > 1) showAllLanes.value = false })
const drillRows = computed(() => {
  if (selectedArtist.value) {
    const ids = new Set(selectedArtist.value.eventIds)
    return filteredFlows.value.flatMap(flow => {
      const event_ids = flow.event_ids.filter(id => ids.has(id))
      return event_ids.length ? [{ ...flow, event_ids, value: event_ids.length }] : []
    })
  }
  if (selectedCell.value) {
    return filteredFlows.value.filter(flow =>
      flow.source === selectedCell.value.source && flow.target === selectedCell.value.target
      && (selectedYear.value == null || flow.year === selectedYear.value)
      && (selectedCell.value.type == null || flow.type === selectedCell.value.type),
    )
  }
  if (selectedYear.value != null) {
    return filteredFlows.value.filter(flow => flow.year === selectedYear.value &&
      (!selectedType.value || flow.type === selectedType.value) &&
      (!selectedGenre.value || (selectedDirection.value === 'both'
        ? flow.source === selectedGenre.value || flow.target === selectedGenre.value
        : ((selectedDirection.value || (metric.value === 'inbound_events' ? 'in' : 'out')) === 'in' ? flow.target : flow.source) === selectedGenre.value)))
  }
  return focusFlows.value.slice(0, 12)
})
const drillCount = computed(() => drillRows.value.reduce((sum, flow) => sum + flow.value, 0))
watch(drillRows, () => { evidenceLimit.value = 40 })
const hasSelection = computed(() => selectedCell.value || selectedYear.value != null || selectedArtist.value)
const selectionLabel = computed(() => selectedArtist.value ? selectedArtist.value.name + ' · 表演作品'
  : selectedCell.value
  ? selectedCell.value.source + ' → ' + selectedCell.value.target
  : [selectedGenre.value, { both: '双向', in: '流入', out: '流出' }[selectedDirection.value], selectedType.value && EDGE_LABELS[selectedType.value], selectedYear.value && selectedYear.value + ' 年'].filter(Boolean).join(' · '))

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
const lensGenre = computed(() => featuredGenre.value)
const lensOut = computed(() => topFlow('out', lensGenre.value, selectedYear.value))
const lensIn = computed(() => topFlow('in', lensGenre.value, selectedYear.value))
const laneMax = computed(() => Math.max(1, lensOut.value[0]?.[1] ?? 0, lensIn.value[0]?.[1] ?? 0))
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
      <section class="genre-poster" aria-labelledby="genre-plate-title">
        <GenreCitationField :flows="focusAllFlows" :visible-flows="focusFlows" :extent="citationExtent"
          :genre="featuredGenre" :selected-year="selectedYear" :selected-pair="selectedCell"
          @select-year="year => chooseMapYear({ year, genre: featuredGenre, direction: 'both' })"
          @select-citation="chooseCitation" @inspect="inspectEvidence">
          <template #intro>
            <h1 id="genre-plate-title">流派传播</h1>
            <p class="genre-poster-lede">{{ featuredGenre }}</p>
            <p v-if="focusSummary.peak" class="genre-poster-finding">外向引用横跨 {{ focusSummary.activeYears }} 个活跃年份，{{ focusSummary.peak[0] }} 年以 {{ focusSummary.peak[1] }} 条达到峰值。</p>
            <p v-else class="genre-poster-finding">当前筛选下无外向引用。</p>
            <a class="genre-poster-jump" href="#genre-chronicle">探索年代谱 <AppIcon name="arrow" :size="16" /></a>
          </template>
          <template #focus-control>
            <label class="genre-poster-focus">焦点流派<select class="op-select" :value="featuredGenre" @change="highlightGenre">
              <option v-for="genre in allGenres" :key="genre" :value="genre">{{ genre }}</option>
            </select></label>
          </template>
        </GenreCitationField>
      </section>

      <div class="genre-score">
      <nav class="score-contents" aria-label="流派传播页内目录">
        <a href="#genre-chronicle">年代谱</a><a href="#genre-connections-title">流派流向</a>
        <a href="#genre-types-title">五类引用</a><a href="#genre-evidence">原始证据</a><a href="#genre-notes-title">读图笔记</a>
      </nav>
      <details class="op-card atlas-filter-card atlas-genre-filters">
        <summary><span>时间与引用筛选</span><small>{{ yearRange.join('—') }} · {{ metricOptions.find(item => item.value === metric)?.label }}</small></summary>
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

      <section id="genre-chronicle" class="genre-movement genre-timeline">
        <GenreSectionSky :variation="0" />
        <header class="genre-movement-head">
          <div><span class="genre-overline">01 / 传播年代</span><h2>流派的传播年代谱</h2>
            <p>每一行是一种流派。横向读年度变化，沿连线读同一年发生的引用。</p></div>
          <div class="atlas-segments" role="group" aria-label="传播图表形式">
            <button type="button" :aria-pressed="trendMode === 'spread'" @click="trendMode = 'spread'">年代谱</button>
            <button type="button" :aria-pressed="trendMode === 'map'" @click="trendMode = 'map'">年代地图</button>
            <button type="button" :aria-pressed="trendMode === 'line'" @click="trendMode = 'line'">年度曲线</button>
          </div>
        </header>
        <div class="genre-timeline-view">
          <GenreChronicle v-if="trendMode === 'spread'" :tracks="spreadTracks" :years="chartYears" :flows="filteredFlows"
            :featured-genre="featuredGenre" :selected-year="selectedYear" :selected-genre="selectedGenre || selectedCell?.source"
            :ratio="isRatio" @select-year="chooseMapYear" @inspect="inspectEvidence"
            @select-flow="flow => choosePair(flow.source, flow.target, flow.year)" />
          <template v-else-if="trendMode === 'map'">
            <GenreCarta :tracks="scoreTracks" :years="chartYears" :flows="filteredFlows"
              :featured-genre="featuredGenre" :selected-year="selectedYear" :selected-genre="selectedGenre || selectedCell?.source"
              :ratio="isRatio" @select-year="chooseMapYear" @inspect="inspectEvidence"
              @select-flow="flow => choosePair(flow.source, flow.target, flow.year)" />
            <div class="atlas-map-caption"><span>拖动浏览 · Ctrl + 滚轮缩放 · 点选查看证据</span>
              <button type="button" class="atlas-inline" :aria-pressed="showAllLanes" @click="showAllLanes = !showAllLanes">{{ showAllLanes ? '聚焦对比流派' : '查看全部 ' + allGenres.length + ' 个流派' }}</button></div>
          </template>
          <ChartPanel v-else :option="trendOption" height="420px" @chart-click="onTrendClick" />
        </div>
        <p class="genre-measure-note">年代谱与年度曲线使用完整年度指标；引用关系筛选用于引用连线、封面星轨和下方证据。年份取受影响作品的发行年。</p>
      </section>

      <section class="genre-movement genre-connections" aria-labelledby="genre-connections-title">
        <GenreSectionSky :variation="1" />
        <header class="genre-movement-head">
          <div><span class="genre-overline">02 / 双向流向</span><h2 id="genre-connections-title">影响流向哪里，灵感来自哪里</h2>
            <p>{{ featuredGenre }} · {{ selectedYear ?? yearRange.join('—') }} 年 · 从流派联系读到作品证据</p></div>
        </header>
        <aside class="genre-reading-rail" aria-label="焦点流派的双向联系前三位">
          <div class="genre-reading-intro"><span>焦点流派</span><h3>{{ featuredGenre }}</h3>
            <small>{{ selectedYear ?? yearRange.join('—') }}</small></div>
          <template v-for="(entries, side) in { in: lensIn, out: lensOut }" :key="side">
          <div class="atlas-flow-list" :class="'score-' + side" :style="{ '--direction-ink': FLOW_TONES[side] }">
            <h4>{{ side === 'out' ? '影响流出' : '灵感流入' }} <small>前三位</small></h4>
            <button v-for="[name, count] in entries" :key="name" type="button" class="atlas-flow-row"
              :aria-label="(side === 'in' ? name + ' → ' + featuredGenre : featuredGenre + ' → ' + name) + '，' + count + ' 条引用'"
              @click="side === 'in' ? choosePair(name, featuredGenre, selectedYear) : choosePair(featuredGenre, name, selectedYear)">
              <span>{{ name }}</span><i class="score-flow-meter" aria-hidden="true"><i :style="{ width: (count / laneMax * 100) + '%' }" /></i><strong>{{ count }}</strong><AppIcon name="arrow" :size="14" /></button>
            <p v-if="!entries.length" class="atlas-subtle">当前范围无记录</p>
          </div>
          <svg class="score-lead" :class="'score-lead-' + side" viewBox="0 0 80 102" preserveAspectRatio="none" aria-hidden="true">
            <g :transform="side === 'out' ? 'translate(80 0) scale(-1 1)' : undefined" :stroke="FLOW_TONES[side]">
              <path v-for="([name,count],i) in entries" :key="name" :d="'M1,' + (17 + i * 34) + ' C34,' + (17 + i * 34) + ' 45,51 77,51'"
                fill="none" :stroke-width=".65 + 2.3 * count / laneMax" />
              <circle v-if="entries.length" cx="77" cy="51" r="2.3" :fill="FLOW_TONES[side]" />
            </g>
          </svg>
          </template>
        </aside>
        <div class="genre-analysis-panel">
          <div class="genre-connections-grid">
            <div class="genre-record-sheet">
              <h3>流派关系唱片</h3>
              <GenreRelationRecord :flows="filteredFlows" :genres="matrixGenres" :genre-colors="genreColors" :focus="featuredGenre"
                :years="chartYears" :selected-year="selectedYear" :selected-pair="selectedCell"
                @focus="focusGenre" @select-flow="flow => choosePair(flow.source, flow.target, flow.year)"
                @select-year="year => chooseMapYear({ year, genre: featuredGenre, direction: 'both' })" @inspect="inspectEvidence" />
              <p class="genre-sheet-note">外圈每格一年，颜色区分引用类型，深浅表示数量；统计焦点流派的全部双向引用。内圈仅连向入图流派。</p>
            </div>
            <div class="genre-matrix-sheet">
              <h3>流向的对照谱</h3>
              <p class="genre-sheet-note">行读来源，列读受影响者。看一条联系，也看它在邻近流派中的分量。</p>
              <label class="genre-view-scope">对照范围<select v-model="matrixScope" class="op-select"><option value="focus">焦点流派与邻居</option><option value="all">全流派对照</option></select></label>
              <GenreDotMatrix :flows="relationFlows" :genres="matrixGenres" :genre-colors="genreColors" :selected-pair="selectedCell"
                @select-flow="flow => choosePair(flow.source, flow.target, selectedYear)" />
              <p class="genre-sheet-note">圆面积表示引用次数；最多比较 12 个流派。点选圆点查看证据，涉及焦点流派的联系会同步高亮左侧关系线。</p>
            </div>
          </div>
        </div>
        <details class="genre-artist-evidence" @toggle="artistsOpen = $event.target.open">
          <summary><span>从流派到作品，再到表演者</span><small>{{ featuredGenre }} · {{ selectedYear ?? yearRange.join('—') }} · {{ artistsOpen ? '收起艺人证据' : '展开艺人证据' }}</small></summary>
          <div v-if="artistsOpen" class="genre-artist-body">
            <p class="genre-sheet-note">这些表演者的作品承接了焦点流派的外向引用。沿作品与表演署名核对联系，登榜标记可单独筛选。</p>
            <GenreAffectedArtists :flows="artistFlows" :focus="featuredGenre" :years="chartYears" :selected-id="selectedArtist?.id"
              @select="chooseArtist" @inspect="inspectEvidence" />
          </div>
        </details>
      </section>

      <section class="genre-movement genre-type-movement" aria-labelledby="genre-types-title">
        <GenreSectionSky :variation="2" />
        <header class="genre-movement-head">
          <div><span class="genre-overline">03 / 引用类型</span><h2 id="genre-types-title">五种引用，五张年代唱片</h2>
            <p>风格借鉴、翻唱、采样与片段、歌词引用，在同一年代尺度上留下纹路。</p></div>
          <div class="atlas-segments" role="group" aria-label="引用类型图表形式">
            <button type="button" :aria-pressed="typeMode === 'records'" @click="typeMode = 'records'">年代唱片</button>
            <button type="button" :aria-pressed="typeMode === 'stack'" @click="typeMode = 'stack'">堆叠曲线</button>
          </div>
        </header>
        <div class="genre-type-toolbar">
          <label class="genre-view-scope">引用范围<select v-model="typeScope" class="op-select"><option value="out">{{ featuredGenre }} · 影响流出</option><option value="in">{{ featuredGenre }} · 灵感流入</option><option value="all">全流派对照</option></select></label>
          <p class="genre-sheet-note">{{ yearRange.join('—') }} · 当前关系筛选 · 点选年份查看对应引用</p>
        </div>
        <GenreTypeRecords v-if="typeMode === 'records'" :flows="typeFlows" :extent="citationExtent"
          :selected-year="selectedYear" :selected-type="selectedCell?.type || selectedType"
          :visible-types="visibleFlowTypes" @select-type="chooseTypeYear" />
        <div v-else class="genre-stack-sheet"><ChartPanel v-if="typeFlows.length" :option="flowTypeOption" height="390px"
            @chart-click="params => chooseTypeYear({ type: FLOW_TYPES.find(type => EDGE_LABELS[type] === params.seriesName), year: chartYears[params.dataIndex] })" />
          <p v-else class="op-state">当前筛选下没有可汇总的引用。</p></div>
      </section>

      <section ref="evidencePanel" id="genre-evidence" class="genre-movement genre-evidence atlas-evidence-panel">
        <GenreSectionSky :variation="3" />
        <header class="genre-evidence-head">
          <div>
          <span class="genre-overline">04 / 原始证据</span><h2>引用曲目单</h2>
          <p v-if="selectedArtist">{{ selectedArtist.name }} 的表演作品所承接的引用</p>
          <p v-else-if="selectedCell">{{ selectedCell.source }} → {{ selectedCell.target }}{{ selectedYear != null ? ' · ' + selectedYear + ' 年' : '' }}{{ selectedCell.type ? ' · ' + EDGE_LABELS[selectedCell.type] : '' }}</p>
          <p v-else-if="selectedYear != null">{{ selectionLabel }}的引用</p>
          <p v-else>点选上方图形以筛选，默认预览焦点流派的前 12 组引用</p>
          <p v-if="hasSelection" class="genre-proof-count" role="status">匹配 {{ formatCount(drillCount) }} 条原始引用<span v-if="drillRows.length > evidenceLimit"> · 显示前 {{ evidenceLimit }} 组</span></p>
          </div>
          <button v-if="hasSelection" type="button" class="atlas-inline" @click="clearEvidence">清除定位</button>
        </header>
        <p class="genre-ledger-hint">上下滚动浏览引用。展开原始边 ID 可核对同一组的全部记录。</p>
        <div class="op-scroll genre-ledger-scroll" tabindex="0" aria-label="引用证据，滚动查看更多记录">
          <table class="op-table" role="table">
            <thead><tr><th scope="col">来源</th><th scope="col">受影响</th><th scope="col">关系类型</th><th class="num" scope="col">年份</th><th class="num" scope="col">事件数</th><th scope="col">原始边 ID</th></tr></thead>
            <tbody>
              <tr v-for="(flow, index) in drillRows.slice(0, evidenceLimit)" :key="`${flow.source}-${flow.target}-${flow.type}-${flow.year}-${index}`">
                <td>{{ flow.source }}</td><td>{{ flow.target }}</td>
                <td><span class="genre-evidence-type" :style="{ '--type-color': FLOW_COLORS[flow.type] }">{{ EDGE_LABELS[flow.type] || flow.type }}</span></td>
                <td class="num">{{ flow.year }}</td><td class="num">{{ flow.value }}</td>
                <td>
                  <details v-if="flow.event_ids.length > 1" class="genre-edge-list">
                    <summary><code>{{ flow.event_ids[0] }}</code><span>全部 {{ flow.event_ids.length }} 条</span></summary>
                    <code v-for="id in flow.event_ids" :key="id">{{ id }}</code>
                  </details>
                  <code v-else>{{ flow.event_ids[0] || '—' }}</code>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <button v-if="drillRows.length > evidenceLimit" type="button" class="atlas-inline genre-evidence-more" @click="evidenceLimit += 40">再看 {{ Math.min(40, drillRows.length - evidenceLimit) }} 组引用 ↓</button>
        <p v-if="!drillRows.length" class="atlas-subtle">当前时间窗与关系类型下没有匹配的引用。</p>
        <p class="op-note">每行都可回查 <code>MC1_graph.json</code> 的原始关系 ID；推导到艺人的联系不证明私下合作或因果影响。</p>
      </section>

      <section class="genre-reading-notes" aria-labelledby="genre-notes-title">
      <GenreSectionSky :variation="4" />
      <header><span class="genre-overline">05 / 读图笔记</span><h2 id="genre-notes-title">Oceanus Folk 的传播笔记</h2><p>按年度、影响方向与数据覆盖核对传播结论。</p></header>
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
      </section>
      <Transition name="selection-dock">
        <div v-if="hasSelection" class="genre-selection-dock">
          <span><strong>{{ selectionLabel }}</strong><small>{{ formatCount(drillCount) }} 条匹配引用</small></span>
          <button type="button" class="atlas-inline" @click="inspectEvidence">查看证据 →</button>
          <button type="button" class="genre-dock-clear" aria-label="清除当前引用定位" @click="clearEvidence">×</button>
        </div>
      </Transition>
      <JournalPager module="genre" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.atlas-genre { --journal-stock:#fcfbf5;--journal-rule:#ced8d7;--journal-accent:#a95b41;--genre-paper:#fcfbf5;--genre-ink:#203f55;--genre-muted:#58717d; }
.genre-poster-focus,.genre-view-scope { display:flex;align-items:center;flex-wrap:wrap;gap:9px;font-size:12px;color:#58717d; }.genre-poster-focus select,.genre-view-scope select { min-height:34px;max-width:100%; }
.genre-poster-focus { font-size:13px; color:#43647a; }
.genre-poster-focus select { min-height:40px; }
.genre-poster h1 {
  margin: 0;
  color: #f5f7fc;
  font: 500 clamp(44px, 6.9vw, 106px)/1.05 var(--atlas-display);
  letter-spacing: .02em;
}
.genre-poster-lede {
  margin: 13px 0 0;
  color: #cbd9ed;
  font: italic clamp(21px, 2.65vw, 37px)/1.15 Georgia, serif;
  overflow-wrap: anywhere;
}
.genre-poster-finding {
  margin: 17px auto 0;
  max-width: 35em;
  color: #b9c8dc;
  font-size: clamp(12px, 1.06vw, 15px);
  line-height: 1.7;
}
.genre-poster-jump {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 43px;
  margin-top: 21px;
  padding: 0 18px;
  border-radius: 24px;
  color: #10243b;
  background: #e9f1fd;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: background 180ms ease;
}
.genre-poster-jump:hover { background: #bfdafa; }
.genre-poster-jump:focus-visible { outline-color: #c5e1ff; }
.genre-poster-jump svg { transform: rotate(90deg); }
@media(max-width:700px) {
  .genre-poster h1 { font-size:clamp(40px,12vw,65px); }
  .genre-poster-lede { margin-top:10px; }
  .genre-poster-finding { margin-top:12px; }
  .genre-poster-jump { margin-top:16px; }
  .genre-poster-focus { gap:6px; }
  .genre-poster-focus select { max-width:min(100%, 180px); }
}
</style>
