<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { area, curveMonotoneY } from 'd3'
import { observeChartSize } from '../lib/atlas'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  tracks: { type: Array, required: true },
  years: { type: Array, required: true },
  flows: { type: Array, required: true },
  featuredGenre: { type: String, required: true },
  selectedYear: { type: Number, default: null },
  selectedGenre: { type: String, default: '' },
  ratio: { type: Boolean, default: false },
})
const emit = defineEmits(['select-year', 'select-flow', 'inspect'])
const frame = ref(null)
const viewport = ref(null)
const yearAxis = ref(null)
const size = ref({ width: 860, height: 506 })
const hovered = ref(null)
const scale = ref(1)
const query = ref('')
const searchStatus = ref('')
const panning = ref(false)
let drag = null
let stopMeasuring
let measured = false
watch(() => props.tracks, () => { hovered.value = null })

const colors = ['#78c5e3', '#efb47a', '#79c7ad', '#e3978f', '#bfce8b', '#82a8db', '#d5a0bc', '#b1c9db']
const axisWidth = 46
const overviewMode = computed(() => props.tracks.length > 12 && scale.value < 1.45)
const width = computed(() => Math.round(Math.max(
  size.value.width - axisWidth - 1, props.tracks.length * (props.tracks.length > 12 ? 42 : 88) + 12,
) * scale.value))
const height = computed(() => Math.round(size.value.height * scale.value))
const top = 77
const bottom = computed(() => height.value - 39)
const minYear = computed(() => props.years[0] ?? 1975)
const maxYear = computed(() => props.years.at(-1) ?? minYear.value)
const columnWidth = computed(() => (width.value - 12) / Math.max(1, props.tracks.length))
const maxValue = computed(() => Math.max(.001, ...props.tracks.flatMap(track => track.rows.map(row => row.value ?? 0))))
const firstPeak = computed(() => (props.tracks.find(track => track.name === props.featuredGenre) ?? props.tracks[0])?.rows.reduce(
  (best, row) => row.value > (best?.value ?? 0) ? row : best, null,
))
const activeYear = computed(() => hovered.value?.year ?? props.selectedYear ?? firstPeak.value?.year)
const activeGenre = computed(() => hovered.value?.genre || props.selectedGenre || props.featuredGenre)
const activePoint = computed(() => props.tracks.find(track => track.name === activeGenre.value)?.rows.find(row => row.year === activeYear.value))

onMounted(() => {
  stopMeasuring = observeChartSize(frame.value, (width, height) => {
    if (width !== size.value.width || height !== size.value.height) size.value = { width, height }
    if (!measured) {
      measured = true
      centerFeatured()
    }
  })
})
onBeforeUnmount(() => stopMeasuring?.())

function yearY(year) {
  if (minYear.value === maxYear.value) return (top + bottom.value) / 2
  return top + (year - minYear.value) / (maxYear.value - minYear.value) * (bottom.value - top)
}
function halfWidth(value) {
  return 1.2 + Math.sqrt(value / maxValue.value) * Math.min(62, columnWidth.value * .40)
}
function ribbonShape(points, x) {
  return area().y(point => yearY(point.year)).x0(point => x - halfWidth(point.value))
    .x1(point => x + halfWidth(point.value)).curve(curveMonotoneY)(points)
}
const columns = computed(() => props.tracks.map((track, index) => {
  const x = (index + .5) * columnWidth.value
  const ribbons = []
  const firstActive = track.rows.findIndex(row => row.value > 0)
  let segment = []
  for (const row of firstActive < 0 ? [] : track.rows.slice(Math.max(0, firstActive - 1))) {
    if (row.value == null) {
      if (segment.length) ribbons.push(ribbonShape(segment, x))
      segment = []
    } else segment.push(row)
  }
  if (segment.length) ribbons.push(ribbonShape(segment, x))
  return { ...track, x, color: colors[(track.colorIndex ?? index) % colors.length], ribbons }
}))
const guideYears = computed(() => props.years.filter(year =>
  year === minYear.value || year === maxYear.value || (year % 5 === 0 && year - minYear.value > 2 && maxYear.value - year > 2),
))
const columnIndex = computed(() => new Map(columns.value.map(column => [column.name, column])))
function headingWidth(index) {
  if (!overviewMode.value) return columnWidth.value - 4
  const edge = index === 0 || index === columns.value.length - 1
  return columnWidth.value * (edge ? 1.45 : 1.86)
}
function headingLeft(column, index) {
  const labelWidth = headingWidth(index)
  return Math.max(0, Math.min(width.value - labelWidth, column.x - labelWidth / 2))
}
async function centerFeatured() {
  await nextTick()
  const panel = viewport.value
  const column = columnIndex.value.get(props.featuredGenre)
  if (panel && column) panel.scrollLeft = column.x - panel.clientWidth / 2
}
watch(() => props.tracks.map(track => track.name).join('|'), centerFeatured)
function routeGroups(genre, year = null) {
  const groups = new Map()
  for (const flow of props.flows) {
    if ((year != null && flow.year !== year) || !columnIndex.value.has(flow.source) || !columnIndex.value.has(flow.target)) continue
    if (genre && flow.source !== genre && flow.target !== genre) continue
    const id = flow.year + '|' + flow.source + '|' + flow.target
    if (!groups.has(id)) groups.set(id, { id, year: flow.year, source: flow.source, target: flow.target, value: 0 })
    groups.get(id).value += flow.value
  }
  return [...groups.values()]
}
function routePath(flow) {
  const source = columnIndex.value.get(flow.source)
  const target = columnIndex.value.get(flow.target)
  const direction = Math.sign(target.x - source.x)
  const y = yearY(flow.year)
  const x1 = source.x + direction * 7
  const x2 = target.x - direction * 8
  const curve = direction * Math.min(48, 9 + Math.abs(x2 - x1) * .14)
  const bend = (x2 - x1) * .26
  return { ...flow, color: source.color, d: 'M ' + x1 + ' ' + y + ' C ' + (x1 + bend) + ' ' + (y - curve)
    + ' ' + (x2 - bend) + ' ' + (y - curve) + ' ' + x2 + ' ' + y }
}
const backgroundRoutes = computed(() => routeGroups(props.tracks.length > 12 ? '' : props.featuredGenre)
  .sort((a, b) => b.value - a.value || a.year - b.year).slice(0, props.tracks.length > 12 ? 28 : 16).map(routePath))
const bridges = computed(() => {
  const current = activeYear.value == null ? [] : routeGroups(activeGenre.value, activeYear.value).map(routePath)
  const activeIds = new Set(current.map(flow => flow.id))
  return [...backgroundRoutes.value.filter(flow => !activeIds.has(flow.id)).map(flow => ({ ...flow, quiet: true })), ...current]
})
function formatValue(value) {
  return props.ratio ? (value * 100).toFixed(1) + '%' : Number(value.toFixed(2)).toLocaleString('zh-CN')
}
function showPoint(year, genre) {
  hovered.value = { year, genre }
}
function selectRibbon(event, column) {
  const rect = event.currentTarget.ownerSVGElement.getBoundingClientRect()
  const position = (event.clientY - rect.top - top) / (bottom.value - top)
  const year = Math.round(minYear.value + Math.max(0, Math.min(1, position)) * (maxYear.value - minYear.value))
  if (column.rows.some(row => row.year === year && row.value != null)) {
    emit('select-year', { year, genre: column.name })
  }
}
async function zoomMap(next, anchor = null) {
  const panel = viewport.value
  const x = anchor?.x ?? panel.clientWidth / 2
  const y = anchor?.y ?? panel.clientHeight / 2
  const xRatio = (panel.scrollLeft + x) / width.value
  const yRatio = (panel.scrollTop + y) / height.value
  scale.value = Math.max(1, Math.min(3, next))
  await nextTick()
  panel.scrollTo(xRatio * width.value - x, yRatio * height.value - y)
}
function wheelZoom(event) {
  if (!event.ctrlKey) return
  event.preventDefault()
  const bounds = viewport.value.getBoundingClientRect()
  zoomMap(scale.value * (event.deltaY < 0 ? 1.16 : .86), { x: event.clientX - bounds.left, y: event.clientY - bounds.top })
}
async function resetMap() {
  scale.value = 1
  await nextTick()
  viewport.value.scrollTo(0, 0)
  centerFeatured()
}
async function locate() {
  const name = query.value.trim().toLocaleLowerCase()
  if (!name) return
  const match = columns.value.find(column => column.name.toLocaleLowerCase() === name)
    ?? columns.value.find(column => column.name.toLocaleLowerCase().includes(name))
  if (!match) {
    searchStatus.value = '当前地图中没有匹配的流派。'
    return
  }
  query.value = match.name
  searchStatus.value = ''
  hovered.value = null
  const peak = match.rows.reduce((best, row) => row.value > (best?.value ?? 0) ? row : best, null)
  const year = peak?.year ?? maxYear.value
  emit('select-year', { year, genre: match.name })
  scale.value = Math.max(scale.value, 1.65)
  await nextTick()
  const panel = viewport.value
  const column = columnIndex.value.get(match.name)
  panel.scrollTo(column.x - panel.clientWidth / 2, yearY(year) - panel.clientHeight / 2)
}
function beginPan(event) {
  if (event.pointerType !== 'mouse' || event.button !== 0 || event.target.closest('[role="button"]')) return
  const panel = viewport.value
  drag = { x: event.clientX, y: event.clientY, left: panel.scrollLeft, top: panel.scrollTop }
}
function movePan(event) {
  if (!drag) return
  const dx = event.clientX - drag.x
  const dy = event.clientY - drag.y
  if (!panning.value && Math.hypot(dx, dy) < 5) return
  const panel = viewport.value
  if (!panning.value) panel.setPointerCapture(event.pointerId)
  panning.value = true
  panel.scrollTo(drag.left - dx, drag.top - dy)
}
function endPan() {
  drag = null
  panning.value = false
}
function syncAxis(event) {
  const axis = yearAxis.value
  if (axis) axis.style.transform = 'translateY(' + -event.target.scrollTop + 'px)'
}
function movePoint(event, laneIndex, year) {
  const { key } = event
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(key)) return
  event.preventDefault()
  let nextColumn = laneIndex
  let nextPoint
  if (key === 'ArrowUp' || key === 'ArrowDown') {
    const earlier = key === 'ArrowUp'
    const rows = columns.value[laneIndex].rows.filter(row => row.value > 0 && (earlier ? row.year < year : row.year > year))
    nextPoint = earlier ? rows.at(-1) : rows[0]
  } else {
    const step = key === 'ArrowLeft' ? -1 : 1
    for (let index = laneIndex + step; index >= 0 && index < columns.value.length; index += step) {
      const rows = columns.value[index].rows.filter(row => row.value > 0)
      if (!rows.length) continue
      nextColumn = index
      nextPoint = rows.reduce((best, row) => Math.abs(row.year - year) < Math.abs(best.year - year) ? row : best)
      break
    }
  }
  if (nextPoint) viewport.value.querySelector(`[data-lane="${nextColumn}"][data-year="${nextPoint.year}"]`)?.focus()
}
</script>

<template>
  <div class="atlas-carta-board" data-visual>
    <div class="atlas-carta-tools">
      <form class="atlas-carta-search" role="search" @submit.prevent="locate">
        <AppIcon name="search" :size="15" />
        <input v-model="query" type="search" list="atlas-carta-genres" placeholder="定位流派" aria-label="在年代地图中定位流派"
          @input="searchStatus = ''">
        <datalist id="atlas-carta-genres"><option v-for="track in tracks" :key="track.name" :value="track.name" /></datalist>
        <button type="submit">定位</button>
      </form>
      <span v-if="searchStatus" class="atlas-carta-status" role="status">{{ searchStatus }}</span>
      <div class="atlas-carta-zoom" role="group" aria-label="地图缩放">
        <button type="button" aria-label="缩小地图" :disabled="scale <= 1" @click="zoomMap(scale / 1.33)"><AppIcon name="minus" :size="15" /></button>
        <span>{{ Math.round(scale * 100) }}%</span>
        <button type="button" aria-label="放大地图" :disabled="scale >= 3" @click="zoomMap(scale * 1.33)"><AppIcon name="plus" :size="15" /></button>
        <button type="button" aria-label="重置年代地图" @click="resetMap"><AppIcon name="reset" :size="15" /></button>
      </div>
    </div>
    <div ref="frame" class="atlas-carta" :class="{ 'is-overview': overviewMode }" :style="{ '--axis-width': axisWidth + 'px' }">
      <div class="atlas-carta-axis" aria-hidden="true">
        <svg ref="yearAxis" :width="axisWidth" :height="height">
          <text v-for="year in guideYears" :key="year" x="8" :y="yearY(year)" dominant-baseline="central">{{ year }}</text>
        </svg>
      </div>
      <div ref="viewport" class="atlas-carta-viewport" :class="{ 'is-panning': panning }" tabindex="0"
        aria-label="年代地图，可拖动浏览，Ctrl 加滚轮缩放"
        @wheel="wheelZoom" @scroll="syncAxis"
        @pointerdown="beginPan" @pointermove="movePan" @pointerup="endPan" @pointercancel="endPan" @lostpointercapture="endPan"
        @pointerleave="hovered = null; endPan()">
      <svg :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height"
        role="group" aria-label="年份自上而下，列内轮廓为所选年度指标">
        <defs>
          <marker id="atlas-carta-arrow" viewBox="0 0 8 8" refX="7" refY="4"
            markerWidth="7" markerHeight="7" markerUnits="userSpaceOnUse" orient="auto">
            <path d="M0 1 7.6 4 0 7 2.1 4Z" fill="#d7edf7" />
          </marker>
        </defs>
        <g aria-hidden="true" class="atlas-carta-columns">
          <rect v-for="column in columns" :key="column.name" :x="column.x - columnWidth / 2 + 4"
            :y="top - 12" :width="columnWidth - 8" :height="bottom - top + 23"
            rx="6" :fill="column.color" :fill-opacity="column.name === activeGenre ? .13 : .054" />
        </g>
        <g aria-hidden="true" class="atlas-carta-guides">
          <line v-for="year in guideYears" :key="year" x1="0" :x2="width - 12" :y1="yearY(year)" :y2="yearY(year)" />
          <line v-if="activeYear != null" class="atlas-carta-selected-year"
            x1="0" :x2="width - 12" :y1="yearY(activeYear)" :y2="yearY(activeYear)" />
        </g>
        <g v-for="(column, index) in columns" :key="column.name" :class="{ 'is-focused': column.name === activeGenre }">
          <foreignObject :x="headingLeft(column, index)" :y="overviewMode ? 1 + index % 2 * 36 : 7"
            :width="headingWidth(index)" :height="overviewMode ? 36 : 53">
            <div class="atlas-carta-genre"><i :style="{ background: column.color }" />{{ column.name }}</div>
          </foreignObject>
          <path v-for="(path, index) in column.ribbons" :key="index" class="atlas-carta-ribbon"
            :d="path" :fill="column.color" :stroke="column.color" @click.stop="selectRibbon($event, column)" />
          <line class="atlas-carta-track" :x1="column.x" :x2="column.x" :y1="top" :y2="bottom" :stroke="column.color" />
        </g>
        <g v-for="bridge in bridges" :key="bridge.id" class="atlas-carta-bridge" :class="{ 'is-context': bridge.quiet }"
          role="button" tabindex="0" :aria-label="bridge.year + ' 年，' + bridge.source + ' 到 ' + bridge.target + '，' + bridge.value + ' 条引用'"
          @click="emit('select-flow', bridge)" @keydown.enter.prevent="emit('select-flow', bridge)"
          @keydown.space.prevent="emit('select-flow', bridge)">
          <title>{{ bridge.year }} 年 · {{ bridge.source }} → {{ bridge.target }} · {{ bridge.value }} 条</title>
          <path :d="bridge.d" stroke="transparent" stroke-width="14" />
          <path class="atlas-carta-flow" :d="bridge.d" :stroke="bridge.color"
            :stroke-width="1.8 + Math.min(3, Math.sqrt(bridge.value) * .6)" marker-end="url(#atlas-carta-arrow)" />
        </g>
        <g v-for="(column, index) in columns" :key="'points-' + column.name">
          <g v-for="point in column.rows.filter(row => row.value > 0)" :key="point.year"
            class="atlas-carta-point" :class="{ 'is-selected': point.year === activeYear && column.name === activeGenre }"
            role="button" :tabindex="point.year === activeYear && column.name === activeGenre ? 0 : -1"
            :data-lane="index" :data-year="point.year"
            :aria-label="column.name + '，' + point.year + ' 年，' + formatValue(point.value)"
            @pointerenter="showPoint(point.year, column.name)"
            @focus="showPoint(point.year, column.name)" @blur="hovered = null"
            @keydown="movePoint($event, index, point.year)"
            @click="emit('select-year', { year: point.year, genre: column.name })"
            @keydown.enter.prevent="emit('select-year', { year: point.year, genre: column.name })"
            @keydown.space.prevent="emit('select-year', { year: point.year, genre: column.name })">
            <title>{{ column.name }} · {{ point.year }} · {{ formatValue(point.value) }}</title>
            <circle :cx="column.x" :cy="yearY(point.year)" r="6" fill="transparent" />
            <circle class="atlas-carta-sample" :cx="column.x" :cy="yearY(point.year)"
              :r="(overviewMode ? 1.05 : 1.9) + Math.sqrt(point.value / maxValue) * 2.7" :fill="column.color" />
          </g>
        </g>
      </svg>
      </div>
      <div v-if="activeYear != null" class="atlas-carta-readout">
        <strong>{{ activeYear }} 年</strong>
        <span>{{ activeGenre }}</span>
        <b v-if="activePoint?.value != null">{{ formatValue(activePoint.value) }}</b>
        <button v-if="selectedYear != null" type="button" @click="emit('inspect')">查看证据<AppIcon name="arrow" :size="14" /></button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.atlas-carta-board {
  overflow: hidden;
  border: 1px solid #30495d;
  border-radius: 10px;
  background: #102437;
  color: #d7e8f2;
}
.atlas-carta-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding: 8px 11px;
  border-bottom: 1px solid #30495d;
}
.atlas-carta-search, .atlas-carta-zoom { display: flex; align-items: center; gap: 7px; }
.atlas-carta-search {
  min-width: 0;
  border: 1px solid #537187;
  border-radius: 6px;
  padding-left: 8px;
  background: #183247;
}
.atlas-carta-search input {
  min-width: 0;
  width: min(180px, 39vw);
  border: 0;
  background: transparent;
  color: #f1f9fe;
  font: inherit;
  font-size: 13px;
}
.atlas-carta-search input::placeholder { color: #b5cddd; }
.atlas-carta-tools button, .atlas-carta-readout button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 34px;
  min-height: 32px;
  padding: 3px 7px;
  border: 1px solid #537187;
  border-radius: 6px;
  background: #19374d;
  color: #edf8ff;
  cursor: pointer;
  font: 13px/1.3 system-ui, sans-serif;
  transition: background 150ms ease;
}
.atlas-carta-tools button:disabled { opacity: .45; cursor: default; }
.atlas-carta-tools button:not(:disabled):hover, .atlas-carta-readout button:hover { background: #2b4b61; }
.atlas-carta-search button { border-width: 0 0 0 1px; border-radius: 0 5px 5px 0; }
.atlas-carta-zoom { margin-left: auto; }
.atlas-carta-zoom span, .atlas-carta-status { font-size: 13px; color: #bad0e1; }
.atlas-carta-zoom span { min-width: 37px; text-align: center; font-variant-numeric: tabular-nums; }
.atlas-carta {
  position: relative;
  display: grid;
  grid-template-columns: var(--axis-width) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  height: clamp(490px, 66svh, 710px);
  overflow: hidden;
  min-width: 0;
  background: radial-gradient(ellipse at 44% 70%, #294b5d, #132c40 63%, #102437);
  scrollbar-color: #6d8ba0 #172e44;
}
.atlas-carta-axis, .atlas-carta-viewport { min-height: 0; }
.atlas-carta-axis { overflow: hidden; border-right: 1px solid #38566c; }
.atlas-carta-viewport { overflow: auto; scrollbar-width: thin; cursor: grab; user-select: none; }
.atlas-carta-viewport.is-panning { cursor: grabbing; }
.atlas-carta-viewport:focus-visible { outline: 2px solid #93cce6; outline-offset: -2px; }
.atlas-carta-viewport svg { display: block; }
.atlas-carta-columns, .atlas-carta-guides { pointer-events: none; }
.atlas-carta-guides line { stroke: #507086; stroke-width: 1; opacity: .55; }
.atlas-carta-axis text { fill: #c1d9e7; font-size: 12px; }
.atlas-carta-guides .atlas-carta-selected-year { stroke: #bbd6e8; stroke-dasharray: 3 4; opacity: .76; }
.atlas-carta-genre { display: flex; align-items: center; justify-content: center; gap: 5px; height: 100%; color: #dbe9f1; text-align: center; font-size: 12px; line-height: 1.18; overflow-wrap: anywhere; }
.is-overview .atlas-carta-genre { gap: 3px; font-size: 11px; line-height: 1.08; overflow-wrap: normal; }
.atlas-carta-genre i { width: 6px; height: 6px; flex: none; border-radius: 50%; }
.atlas-carta-ribbon { fill-opacity: .35; stroke-width: 1.15; stroke-opacity: .75; cursor: pointer; }
.is-focused .atlas-carta-ribbon { fill-opacity: .56; stroke-opacity: .94; }
.atlas-carta-track { stroke-width: .7; opacity: .32; pointer-events: none; }
.atlas-carta-bridge { cursor: pointer; fill: none; outline: none; }
.atlas-carta-flow { opacity: .8; transition: opacity 140ms ease; stroke-linecap: round; }
.atlas-carta-bridge.is-context .atlas-carta-flow { opacity: .25; }
.atlas-carta-bridge:is(:hover, :focus-visible) .atlas-carta-flow { opacity: 1; stroke: #edf9ff; }
.atlas-carta-point { cursor: pointer; outline: none; }
.atlas-carta-sample { opacity: .75; }
.atlas-carta-point:is(.is-selected, :focus-visible, :hover) .atlas-carta-sample { stroke: #f8fdff; stroke-width: 1.5; opacity: 1; }
.atlas-carta-readout {
  position: absolute;
  bottom: 14px;
  left: 54px;
  max-width: calc(100% - 64px);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  padding: 4px 8px;
  border-radius: 5px;
  background: #142d41;
  color: #d6eaf5;
  font-size: 13px;
  pointer-events: none;
}
.atlas-carta-readout b { color: #f5c597; font-weight: 600; }
.atlas-carta-readout button { pointer-events: auto; min-height: 28px; }
.atlas-carta-board :is(button, input):focus-visible { outline: 2px solid #9cdbf2; outline-offset: -2px; }
@media (max-width: 620px) { .atlas-carta { height: 456px; } .atlas-carta-zoom { margin-left: 0; } }
@media (prefers-reduced-motion: reduce) { .atlas-carta-flow { transition: none; } }
</style>
