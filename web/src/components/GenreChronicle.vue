<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { area, curveMonotoneX } from 'd3'
import { FLOW_TONES, observeChartSize } from '../lib/atlas'
import { formatCount, genreColor } from '../lib/palette'
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
const viewport = ref(null)
const measuredWidth = ref(960)
const scrollOffset = ref(0)
const hovered = ref(null)
let stopMeasuring
let positioned = false
const firstLane = 111
const laneSpacing = 69
const width = computed(() => Math.max(590, measuredWidth.value))
const height = computed(() => firstLane + props.tracks.length * laneSpacing)
const minYear = computed(() => props.years[0] ?? 1975)
const maxYear = computed(() => props.years.at(-1) ?? minYear.value)
const left = 22
const right = computed(() => width.value - 22)
const maxValue = computed(() => Math.max(.001, ...props.tracks.flatMap(track => track.rows.map(row => row.value ?? 0))))
const tickYears = computed(() => props.years.filter(year =>
  year === minYear.value || year === maxYear.value
  || (year % 10 === 0 && year - minYear.value >= 4 && maxYear.value - year >= 4),
))
function yearX(year) {
  const share = minYear.value === maxYear.value ? .5 : (year - minYear.value) / (maxYear.value - minYear.value)
  return left + share * (right.value - left)
}
function showTickLabel(year) {
  const position = yearX(year) - scrollOffset.value
  return position >= 18 && position <= measuredWidth.value - 18
}
function magnitude(value) {
  return .8 + 26 * Math.sqrt(Math.max(0, value) / maxValue.value)
}
const bands = computed(() => props.tracks.map((track, index) => {
  const y = firstLane + index * laneSpacing
  const color = genreColor(track.colorIndex ?? index)
  const shape = scale => area().defined(row => row.value != null).x(row => yearX(row.year))
    .y0(row => y + magnitude(row.value) * scale)
    .y1(row => y - magnitude(row.value) * scale).curve(curveMonotoneX)(track.rows)
  const points = track.rows.filter(row => row.value > 0)
  const peak = points.reduce((best, row) => !best || row.value > best.value ? row : best, null)
  return { ...track, index, y, color, outer: shape(1), inner: shape(.64), points, peak }
}))
const focusBand = computed(() => bands.value.find(band => band.name === props.featuredGenre) ?? bands.value[0])
const activeYear = computed(() => hovered.value?.year ?? props.selectedYear ?? focusBand.value?.peak?.year)
const activeGenre = computed(() => hovered.value?.genre || props.selectedGenre || focusBand.value?.name)
const activeRow = computed(() => bands.value.find(band => band.name === activeGenre.value)?.rows.find(row => row.year === activeYear.value))
const routes = computed(() => {
  const lanes = new Map(bands.value.map(band => [band.name, band]))
  const pairs = new Map()
  for (const flow of props.flows) {
    if (flow.year !== activeYear.value || (flow.source !== activeGenre.value && flow.target !== activeGenre.value)) continue
    if (!lanes.has(flow.source) || !lanes.has(flow.target)) continue
    const key = flow.source + '|' + flow.target
    const route = pairs.get(key) ?? { key, source: flow.source, target: flow.target, year: flow.year, value: 0 }
    route.value += flow.value
    pairs.set(key, route)
  }
  return [...pairs.values()].map(route => {
    const y1 = lanes.get(route.source).y
    const y2 = lanes.get(route.target).y
    const side = route.source === activeGenre.value ? 'out' : 'in'
    const x = yearX(route.year)
    const to = y2 - 5 * Math.sign(y2 - y1)
    const bend = Math.min(51, 19 + Math.abs(y2 - y1) * .12) * (side === 'out' ? 1 : -1)
    return {
      ...route, side,
      path: `M${x},${y1} C${x + bend},${y1 + (to - y1) * .25} ${x + bend},${to - (to - y1) * .25} ${x},${to}`,
    }
  })
})
const strongestRoute = computed(() => routes.value.reduce(
  (best, route) => !best || route.value > best.value ? route : best, null,
))
const peakNote = computed(() => {
  const peak = focusBand.value?.peak
  if (!peak) return null
  const x = yearX(peak.year)
  const y = focusBand.value.y - magnitude(peak.value)
  return { ...peak, x, y, labelX: Math.max(left, Math.min(right.value - 120, x - 65)) }
})
function formatValue(value) {
  if (!Number.isFinite(value)) return '无观测值'
  return props.ratio ? (value * 100).toFixed(1) + '%' : formatCount(Number(value.toFixed(2)))
}
function preview(year, genre) { hovered.value = { year, genre } }
function selectYear(year, genre) { emit('select-year', { year, genre }) }
function selectBand(event, band) {
  const rect = event.currentTarget.ownerSVGElement.getBoundingClientRect()
  const x = event.clientX - rect.left
  const share = Math.max(0, Math.min(1, (x - left) / (right.value - left)))
  const year = Math.round(minYear.value + share * (maxYear.value - minYear.value))
  if (band.rows.some(row => row.year === year && row.value != null)) selectYear(year, band.name)
}
function moveSample(event, band, point, offset) {
  event.preventDefault()
  const next = band.points[band.points.indexOf(point) + offset]
  if (next) viewport.value?.querySelector(`[data-track="${band.index}"][data-year="${next.year}"]`)?.focus()
}
async function frameYear(year) {
  await nextTick()
  const el = viewport.value
  if (el && year != null && el.scrollWidth > el.clientWidth) {
    const limit = el.scrollWidth - el.clientWidth
    const offset = yearX(year) - el.clientWidth * .60
    el.scrollLeft = limit - offset < 42 ? limit : Math.max(0, offset)
  }
}
onMounted(() => {
  stopMeasuring = observeChartSize(viewport.value, value => {
    measuredWidth.value = value
    if (!positioned) {
      positioned = true
      frameYear(activeYear.value)
    }
  })
})
onBeforeUnmount(() => stopMeasuring?.())
</script>

<template>
  <div class="genre-chronicle" data-visual>
    <div class="chronicle-spread">
      <ol v-if="years.length" class="chronicle-tracks" aria-label="年代谱流派"
        :style="{ '--lane-spacing': laneSpacing + 'px', paddingTop: firstLane - laneSpacing / 2 + 'px' }">
        <li v-for="band in bands" :key="band.name" class="chronicle-genre" :style="{ '--track-color': band.color }"
          :class="{ 'is-current': band.name === activeGenre }">{{ band.name }}</li>
      </ol>
      <div ref="viewport" class="chronicle-viewport" tabindex="0" aria-label="横向流派年代谱，可横向滚动浏览年份"
        @pointerleave="hovered = null" @scroll.passive="scrollOffset = $event.currentTarget.scrollLeft">
      <svg v-if="years.length" :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height" role="group"
        aria-label="从左往右读年份，各行的色带使用同一尺度">
        <defs>
          <marker v-for="(color, side) in FLOW_TONES" :id="'chronicle-arrow-' + side" :key="side"
            viewBox="0 0 7 7" refX="6" refY="3.5" markerWidth="6" markerHeight="6" markerUnits="userSpaceOnUse" orient="auto">
            <path d="M0 0L7 3.5L0 7Z" :fill="color" />
          </marker>
        </defs>
        <g class="chronicle-grid" aria-hidden="true">
          <line :x1="left" :x2="right" y1="68" y2="68" />
          <g v-for="year in tickYears" :key="year">
            <line :x1="yearX(year)" :x2="yearX(year)" y1="62" :y2="height - 27" />
            <text v-if="showTickLabel(year)" :x="yearX(year)" y="55" text-anchor="middle">{{ year }}</text>
          </g>
          <line v-if="activeYear != null" class="chronicle-year-guide" :x1="yearX(activeYear)"
            :x2="yearX(activeYear)" y1="67" :y2="height - 27" />
        </g>
        <g v-for="band in bands" :key="band.name" class="chronicle-lane" :class="{ 'is-current': band.name === activeGenre }">
          <line :x1="left" :x2="right" :y1="band.y" :y2="band.y" />
          <path v-if="band.outer" :d="band.outer" class="chronicle-band" :fill="band.color" :stroke="band.color"
            @click="selectBand($event, band)" />
          <path v-if="band.inner" :d="band.inner" class="chronicle-contour" :stroke="band.color" />
        </g>
        <g v-for="route in routes" :key="route.key" class="chronicle-route" role="button" tabindex="0"
          :aria-label="route.year + ' 年，' + route.source + ' 到 ' + route.target + '，' + route.value + ' 条引用'"
          @click="emit('select-flow', route)" @keydown.enter.prevent="emit('select-flow', route)"
          @keydown.space.prevent="emit('select-flow', route)">
          <path :d="route.path" stroke="transparent" stroke-width="13" />
          <path :d="route.path" :stroke="FLOW_TONES[route.side]" :stroke-width="1.1 + Math.sqrt(route.value) * .45"
            :marker-end="'url(#chronicle-arrow-' + route.side + ')'" />
        </g>
        <g v-for="band in bands" :key="'sample-' + band.name">
          <g v-for="point in band.points" :key="point.year" class="chronicle-point"
            :class="{ 'is-current': point.year === activeYear && band.name === activeGenre }"
            :data-track="band.index" :data-year="point.year"
            role="button" :tabindex="point.year === band.peak.year ? 0 : -1"
            :aria-label="band.name + '，' + point.year + ' 年，' + formatValue(point.value)"
            @pointerenter="preview(point.year, band.name)" @focus="preview(point.year, band.name)" @blur="hovered = null"
            @click="selectYear(point.year, band.name)" @keydown.enter.prevent="selectYear(point.year, band.name)"
            @keydown.space.prevent="selectYear(point.year, band.name)"
            @keydown.left="moveSample($event, band, point, -1)" @keydown.right="moveSample($event, band, point, 1)">
            <circle :cx="yearX(point.year)" :cy="band.y" r="7" fill="transparent" />
            <circle :cx="yearX(point.year)" :cy="band.y" :r="point.year === band.peak.year ? 3 : 1.7" :fill="band.color" />
          </g>
        </g>
        <g v-if="peakNote" class="chronicle-peak" role="button" tabindex="0" :aria-label="peakNote.year + ' 年峰值，查看证据'"
          @click="selectYear(peakNote.year, focusBand.name)" @keydown.enter.prevent="selectYear(peakNote.year, focusBand.name)"
          @keydown.space.prevent="selectYear(peakNote.year, focusBand.name)">
          <path :d="`M${peakNote.labelX} 32H${peakNote.x - 6}L${peakNote.x} ${peakNote.y}`" />
          <circle :cx="peakNote.x" :cy="peakNote.y" r="3" />
          <text :x="peakNote.labelX" y="23">{{ peakNote.year }} 年峰值 · {{ formatValue(peakNote.value) }}</text>
        </g>
      </svg>
      <p v-else class="op-state">所选时间窗没有可绘制的年份。</p>
      </div>
    </div>
    <div class="chronicle-readout">
      <span v-if="activeYear != null"><strong>{{ activeYear }} 年 · {{ activeGenre }}</strong> · {{ formatValue(activeRow?.value) }}</span>
      <span v-else>当前指标暂无非零观测值。</span>
      <button v-if="strongestRoute" class="atlas-inline chronicle-route-link" type="button" @click="emit('select-flow', strongestRoute)">
        <i :style="{ background: FLOW_TONES[strongestRoute.side] }" />
        {{ strongestRoute.source }} → {{ strongestRoute.target }} · {{ formatCount(strongestRoute.value) }} 条
      </button>
      <button v-if="selectedYear != null" class="atlas-inline" type="button" @click="emit('inspect')">
        查看该年证据<AppIcon name="arrow" :size="15" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.genre-chronicle { background: var(--journal-stock); border-block: 1px solid var(--journal-rule); }
.chronicle-spread { display: flex; }
.chronicle-tracks {
  flex: 0 0 clamp(92px, 10.5vw, 145px);
  margin: 0;
  padding-inline: 10px 7px;
  list-style: none;
  border-right: 1px solid var(--journal-rule);
}
.chronicle-viewport { flex: 1; min-width: 0; overflow: auto hidden; scrollbar-width: thin; scrollbar-color: #9db2be #eef3f4; }
.chronicle-viewport svg { display: block; max-width: none; }
.chronicle-grid line { stroke: #c4d0d5; stroke-width: 1; }
.chronicle-grid g line { stroke-dasharray: 2 5; }
.chronicle-grid .chronicle-year-guide { stroke: #668c9e; stroke-dasharray: 3 4; }
.chronicle-grid text { font: 14px Georgia, serif; fill: #536b79; }
.chronicle-lane line { stroke: #dae4e7; }
.chronicle-genre { display: flex; align-items: center; height: var(--lane-spacing); font-size: 13px; line-height: 1.2; color: #243f50; overflow-wrap: anywhere; }
.chronicle-genre.is-current { font-weight: 700; }
.chronicle-genre::before { content: ''; flex: none; width: 6px; height: 6px; margin-right: 6px; border-radius: 50%; background: var(--track-color); }
.chronicle-band { fill-opacity: .19; stroke-width: .85; stroke-opacity: .65; cursor: pointer; }
.chronicle-lane.is-current .chronicle-band { fill-opacity: .30; stroke-opacity: .88; }
.chronicle-contour { fill: none; stroke-width: .8; opacity: .47; pointer-events: none; }
.chronicle-route { fill: none; cursor: pointer; outline: none; }
.chronicle-route path + path { opacity: .77; }
.chronicle-route:is(:hover, :focus-visible) path + path { stroke: var(--journal-accent); opacity: 1; }
.chronicle-point { cursor: pointer; outline: none; }
.chronicle-point:is(.is-current, :focus-visible) circle + circle { stroke: #1e4358; stroke-width: 2; }
.chronicle-peak { color: var(--journal-accent); cursor: pointer; outline: none; }
.chronicle-peak path { fill: none; stroke: currentColor; stroke-width: .95; }
.chronicle-peak circle { fill: #fffdfa; stroke: currentColor; }
.chronicle-peak text { fill: currentColor; font-size: 13px; }
.chronicle-peak:is(:hover, :focus-visible) circle { fill: currentColor; }
.chronicle-readout { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 3px 10px; padding: 6px 11px; border-top: 1px solid var(--atlas-line); color: var(--atlas-muted); font-size: 13px; }
.chronicle-readout strong { color: var(--atlas-ink); }
.chronicle-route-link { text-align: start; }
.chronicle-route-link i { width: 6px; height: 6px; flex: none; border-radius: 50%; }
@media (max-width: 680px) {
  .chronicle-genre { font-size: 12px; }
}
</style>
