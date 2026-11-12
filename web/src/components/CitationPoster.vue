<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { arc, curveCatmullRom, line } from 'd3'
import { revolvingWave, wavePhase } from '../lib/ambientMotion'
import { EDGE_LABELS, FLOW_COLORS, FLOW_TYPES, formatCount } from '../lib/palette'
import AmbientTrace from './AmbientTrace.vue'

const props = defineProps({
  flows: { type: Array, required: true },
  years: { type: Array, required: true },
  relation: { type: String, default: 'all' },
})
const emit = defineEmits(['year', 'relation'])
const stackedCover = window.matchMedia('(max-width: 900px)')
const compact = ref(stackedCover.matches)
const hovered = ref(null)
const pickedYear = ref(null)

function syncCoverLayout(event) {
  compact.value = event.matches
}
onMounted(() => stackedCover.addEventListener('change', syncCoverLayout))
onBeforeUnmount(() => stackedCover.removeEventListener('change', syncCoverLayout))

const groups = computed(() => {
  const years = new Map(props.years.map(year => [year, { year, total: 0, counts: {}, rows: [] }]))
  for (const row of props.flows) {
    const group = years.get(row.year)
    if (!group) continue
    group.total += row.value
    group.counts[row.type] = (group.counts[row.type] ?? 0) + row.value
    group.rows.push(row)
  }
  return [...years.values()]
})

const turn = Math.PI / 180
const startAngle = -230 * turn
const sweep = 305 * turn
const grooveLine = line().defined(Boolean).x(point => point.x).y(point => point.y).curve(curveCatmullRom.alpha(.5))
const yearSector = arc()

function polar(cx, cy, angle, radius) {
  return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) }
}
function coordinate(point) {
  return point.x.toFixed(1) + ' ' + point.y.toFixed(1)
}
function railPath(cx, cy, radius, from, to) {
  return `M${coordinate(polar(cx, cy, from, radius))}A${radius} ${radius} 0 1 1 ${coordinate(polar(cx, cy, to, radius))}`
}

const chart = computed(() => {
  const { width, height, cx, cy, radius, inner, trackGap, scale } = compact.value
    ? { width: 420, height: 373, cx: 209, cy: 175, radius: 142, inner: 41, trackGap: 16, scale: .56 }
    : { width: 1400, height: 650, cx: 910, cy: 322, radius: 277, inner: 81, trackGap: 31, scale: 1 }
  const entries = groups.value
  const step = sweep / Math.max(1, entries.length - 1)
  const angleAt = index => startAngle + index * step
  const pointAt = (angle, distance) => polar(cx, cy, angle, distance)
  const stopAngle = startAngle + sweep
  const maxTrack = Math.max(1, ...entries.flatMap(row => Object.values(row.counts)))
  const trackWidth = count => (trackGap - 4 * scale) * Math.sqrt(count / maxTrack)
  const tracks = FLOW_TYPES.map((type, index) => {
    const base = inner + (FLOW_TYPES.length - 1 - index) * trackGap
    const samples = entries.map(row => trackWidth(row.counts[type] ?? 0))
    const contours = [.26, .58, 1].map(share => grooveLine(samples.map((value, year) =>
      value || samples[year - 1] || samples[year + 1]
        ? pointAt(angleAt(year), base + scale * 1.6 + share * value) : null,
    )))
    return { type, base, samples, contours, rail: railPath(cx, cy, base, startAngle, stopAngle) }
  })
  const tracksByType = new Map(tracks.map(track => [track.type, track]))
  const years = entries.map((group, index) => {
    const angle = angleAt(index)
    const paths = new Map()
    const placedByType = {}
    const rows = [...group.rows].sort((a, b) => a.source.localeCompare(b.source) || a.target.localeCompare(b.target))
    for (const flow of rows) {
      const track = tracksByType.get(flow.type)
      if (!track) continue
      const level = flow.value >= 7 ? 2 : flow.value >= 3 ? 1 : 0
      const key = flow.type + ':' + level
      if (!paths.has(key)) paths.set(key, { key, type: flow.type, level, segments: [] })
      const points = paths.get(key).segments
      const count = group.counts[flow.type]
      const phase = group.year * .417 + track.base * .038
      const pressure = track.samples[index]
      let placed = placedByType[flow.type] ?? 0
      for (let event = 0; event < flow.value; event += 1) {
        // All events stay in their own year. Irrational steps stagger the radial positions without a grid.
        const offset = ((placed + .5) / count - .5) * .98
        const adjacent = track.samples[index + Math.sign(offset)] ?? pressure
        const localWidth = pressure + (adjacent - pressure) * Math.abs(offset)
        const sequence = (phase + placed * .61803398875) % 1
        const distance = track.base + scale * 1.6 + localWidth * (.09 + .85 * sequence ** 1.42)
        points.push('M' + coordinate(pointAt(angle + offset * step, distance)) + 'h.01')
        placed += 1
      }
      placedByType[flow.type] = placed
    }
    const major = group.year % 10 === 0 || index === 0 || index === entries.length - 1
    return {
      ...group, angle, major, wavePhase: wavePhase(angle),
      anchor: pointAt(angle, radius),
      tick: pointAt(angle, radius + scale * (major ? 8.5 : 3.6)),
      label: pointAt(angle, radius + (compact.value ? 16 : 21)),
      trace: `M${coordinate(pointAt(angle, inner - 3))}L${coordinate(pointAt(angle, radius + scale * 6))}`,
      hit: yearSector({
        innerRadius: inner - 4, outerRadius: radius + scale * 8,
        startAngle: angle - step / 2 + Math.PI / 2, endAngle: angle + step / 2 + Math.PI / 2,
      }),
      paths: [...paths.values()].sort((a, b) => a.level - b.level)
        .map(path => ({ ...path, d: path.segments.join('') })),
    }
  })
  return {
    width, height, cx, cy, radius, scale, tracks, years,
    edge: railPath(cx, cy, radius, startAngle, stopAngle),
  }
})
const observed = computed(() => chart.value.years.filter(row => row.total > 0))
function visibleCount(row) {
  return props.relation === 'all' ? row.total : row.counts[props.relation] ?? 0
}
const rim = computed(() => {
  const { cx, cy, radius, scale, years } = chart.value
  const maxTotal = Math.max(1, ...years.map(year => year.total))
  return Array.from({ length: 5 }, (_, index) => grooveLine(years.map(year => {
    const relief = Math.sqrt(visibleCount(year) / maxTotal) * (7 + index * 2.65)
    return polar(cx, cy, year.angle, radius - scale * (4 + index * 3 + relief))
  })))
})
const orbit = computed(() => {
  const { cx, cy, radius, scale } = chart.value
  return revolvingWave(cx, cy, radius - 19 * scale, {
    amplitude: 15.8 * scale, seconds: 5.8,
  })
})
const selectable = computed(() => observed.value.filter(row => visibleCount(row) > 0))
const peak = computed(() => selectable.value.reduce((best, row) => !best || visibleCount(row) > visibleCount(best) ? row : best, null))
const first = computed(() => selectable.value[0])
const inspected = computed(() => selectable.value.find(row => row.year === (hovered.value ?? pickedYear.value)))
const active = computed(() => inspected.value ?? peak.value)
const ticks = computed(() => chart.value.years.filter(row => row.major))
const shownTypes = computed(() => FLOW_TYPES.filter(type => props.flows.some(row => row.type === type)))
const reading = computed(() => {
  const counts = inspected.value?.counts ?? chart.value.years.reduce((sum, year) => {
    for (const type of shownTypes.value) sum[type] = (sum[type] ?? 0) + (year.counts[type] ?? 0)
    return sum
  }, {})
  const types = shownTypes.value.filter(type => props.relation === 'all' || type === props.relation)
  const total = types.reduce((sum, type) => sum + (counts[type] ?? 0), 0)
  const halfWidth = compact.value ? 23 : 45
  let x = -halfWidth
  const segments = types.filter(type => counts[type]).map(type => {
    const end = x + 2 * halfWidth * counts[type] / total
    const segment = { type, x, end }
    x = end
    return segment
  })
  return {
    title: inspected.value?.year ?? formatCount(total),
    detail: (inspected.value ? formatCount(total) + ' 条' : '条') + (EDGE_LABELS[props.relation] ?? '跨流派引用'),
    segments,
  }
})

function annotation(mark, kind, label) {
  const { cx, cy, radius, height } = chart.value
  const left = kind === 'first'
  const small = compact.value
  const anchor = mark.anchor
  const elbow = polar(cx, cy, mark.angle, radius + (small ? 9 : 18))
  const x = small ? (left ? 18 : 305) : (left ? 466 : 1227)
  const y = small ? (left ? 319 : 312) : Math.max(55, Math.min(height - 65, elbow.y + (left ? 19 : -9)))
  const end = small ? { x: x + (left ? 21 : 69), y: y - 13 } : { x: x + (left ? 134 : -10), y: y + 9 }
  const bend = small
    ? { x: left ? 34 : 386, y: elbow.y + 11 }
    : { x: elbow.x + (left ? -22 : 22), y: end.y }
  const path = `M${coordinate(anchor)}L${coordinate(elbow)}Q${coordinate(bend)} ${coordinate(end)}`
  const detailTypes = !small && !left && props.relation === 'all'
    ? shownTypes.value.filter(type => mark.counts[type]) : []
  return { mark, x, y, anchor, label, path, detailTypes }
}

const annotations = computed(() => {
  if (!first.value || !peak.value) return []
  const firstNote = annotation(first.value, 'first', '最早记录')
  if (first.value.year === peak.value.year) return [firstNote]
  return [firstNote, annotation(peak.value, 'peak', props.relation === 'all' ? '全网峰年' : '所选类型峰年')]
})
function countLabel(row) {
  const label = props.relation === 'all' ? '引用' : EDGE_LABELS[props.relation]
  return row.year + ' 年 · ' + formatCount(visibleCount(row)) + ' 条' + label
}
function openYear(year) {
  pickedYear.value = year
  emit('year', year)
}
function strokeWidth(level) {
  return chart.value.scale * [1.64, 2.35, 3.25][level]
}
</script>

<template>
  <div class="citation-poster" :class="{ 'is-compact': compact }" data-visual data-wave-surface>
    <svg :viewBox="`0 0 ${chart.width} ${chart.height}`" :style="orbit.style" role="group"
      aria-label="跨流派引用唱片谱，年份沿外圈排列，每一点为一条真实引用">
      <g aria-hidden="true" class="poster-rules">
        <path class="poster-edge" :d="chart.edge" />
        <g class="atlas-wave-body">
          <path v-for="(profile, index) in rim" :key="index" class="poster-profile"
            :class="{ 'is-deep': index === 3, 'is-fine': index % 2 === 0 }" :d="profile" />
          <g v-for="track in chart.tracks" :key="track.type" class="poster-grooves"
            :class="{ 'is-filtered': relation !== 'all' && relation !== track.type }" :stroke="FLOW_COLORS[track.type]">
            <path class="poster-rail" :d="track.rail" />
            <path v-for="(contour, index) in track.contours" :key="index" class="poster-contour"
              :class="{ 'is-edge': index === track.contours.length - 1 }" :d="contour" />
          </g>
        </g>
        <line v-for="mark in chart.years" :key="mark.year" class="poster-tick" :class="{ 'is-major': mark.major }"
          :x1="mark.anchor.x" :y1="mark.anchor.y" :x2="mark.tick.x" :y2="mark.tick.y" />
        <g v-for="tick in ticks" :key="tick.year">
          <text :x="tick.label.x" :y="tick.label.y" text-anchor="middle" dominant-baseline="central">{{ tick.year }}</text>
        </g>
      </g>
      <AmbientTrace v-if="observed.length" :orbit="orbit" />
      <g v-if="observed.length" aria-hidden="true" class="poster-register" :transform="`translate(${chart.cx} ${chart.cy})`">
        <text class="poster-register-value" y="2">{{ reading.title }}</text>
        <text class="poster-register-caption" :y="compact ? 17 : 24">{{ reading.detail }}</text>
        <line v-for="segment in reading.segments" :key="segment.type" :stroke="FLOW_COLORS[segment.type]"
          :x1="segment.x" :x2="segment.end" :y1="compact ? 26 : 37" :y2="compact ? 26 : 37" />
      </g>
      <path v-if="inspected" aria-hidden="true" class="poster-trace" :d="inspected.trace" />
      <g v-for="year in observed" :key="year.year" class="poster-year"
        :class="{ 'is-muted': hovered != null && year.year !== hovered }"
        role="button" tabindex="-1" :aria-label="countLabel(year)" :aria-disabled="!visibleCount(year)"
        @pointerenter="hovered = visibleCount(year) ? year.year : null" @pointerleave="hovered = null"
        @click="visibleCount(year) && openYear(year.year)">
        <title>{{ countLabel(year) }}</title>
        <path class="poster-hit" :transform="`translate(${chart.cx} ${chart.cy})`" :d="year.hit" />
        <g class="atlas-orbit-swell" :style="{ '--atlas-wave-phase': year.wavePhase }">
          <path v-for="path in year.paths" :key="path.key" class="poster-marks"
            :class="{ 'is-filtered': relation !== 'all' && relation !== path.type, 'is-weighted': path.level > 0 }"
            :stroke="FLOW_COLORS[path.type]" :stroke-width="strokeWidth(path.level)" :d="path.d" />
        </g>
      </g>
      <g v-for="note in annotations" :key="note.label" class="poster-annotation" role="button"
        tabindex="0" :aria-label="note.label + '，' + countLabel(note.mark)"
        @pointerenter="hovered = note.mark.year" @pointerleave="hovered = null"
        @focus="hovered = note.mark.year" @blur="hovered = null"
        @click="openYear(note.mark.year)" @keydown.enter.prevent="openYear(note.mark.year)"
        @keydown.space.prevent="openYear(note.mark.year)">
        <path :d="note.path" />
        <circle :cx="note.anchor.x" :cy="note.anchor.y" :r="compact ? 2.4 : 3.5" />
        <text :x="note.x" :y="note.y">{{ note.label }}</text>
        <text :x="note.x" :y="note.y + (compact ? 17 : 28)" class="poster-note-value">{{ note.mark.year }} · {{ formatCount(visibleCount(note.mark)) }} 条</text>
        <g v-if="note.detailTypes.length" class="poster-note-details" aria-hidden="true"
          :transform="`translate(${note.x} ${note.y + 41})`">
          <line class="poster-note-rule" x2="118" />
          <g v-for="(type, index) in note.detailTypes" :key="type" :transform="`translate(0 ${16 + 16 * index})`">
            <line class="poster-note-color" x2="8" y1="-4" y2="-4" :stroke="FLOW_COLORS[type]" />
            <text x="14">{{ EDGE_LABELS[type] }}</text>
            <text class="poster-note-count" x="118" text-anchor="end">{{ formatCount(note.mark.counts[type]) }}</text>
          </g>
        </g>
      </g>
    </svg>
    <div class="poster-reading">
      <div class="poster-key" role="group" aria-label="封面引用类型">
        <button v-for="type in shownTypes" :key="type" type="button" :aria-pressed="relation === type"
          @click="emit('relation', relation === type ? 'all' : type)">
          <i :style="{ background: FLOW_COLORS[type] }" />{{ EDGE_LABELS[type] }}
        </button>
      </div>
      <div v-if="active" class="poster-year-picker">
        <select :value="active.year" aria-label="封面年份" @change="pickedYear = Number($event.target.value)">
          <option v-for="row in selectable" :key="row.year" :value="row.year">{{ row.year }} 年</option>
        </select>
        <button type="button" class="poster-date" @click="openYear(active.year)">
          查 {{ formatCount(visibleCount(active)) }} 条{{ relation === 'all' ? '引用' : EDGE_LABELS[relation] }} <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.citation-poster { min-width: 0; position: relative; }
.citation-poster svg { width: 100%; height: auto; display: block; }
.citation-poster.is-compact svg { max-width: 576px; margin-inline: auto; }
.poster-rules, .poster-register, .poster-trace { pointer-events: none; }
.poster-rules path, .poster-trace { fill: none; }
.poster-edge { stroke: #9daeb2; stroke-width: .8; }
.poster-profile { stroke: #506879; stroke-width: .85; opacity: .64; }
.poster-profile.is-fine { stroke-width: .48; opacity: .5; }
.poster-profile.is-deep { stroke: #365369; stroke-width: 1.35; opacity: .83; }
.poster-rail { stroke-width: .68; opacity: .34; }
.poster-contour { stroke-width: .51; opacity: .52; }
.poster-contour.is-edge { stroke-width: .85; opacity: .73; }
.poster-grooves { transition: opacity 180ms var(--atlas-ease); }
.poster-grooves.is-filtered { opacity: .24; }
.poster-tick { stroke: #a3b1b7; stroke-width: .72; }
.poster-tick.is-major { stroke: #536c79; }
.poster-rules text { fill: #4c626c; font: 14px Georgia, serif; font-variant-numeric: tabular-nums; }
.poster-register { text-anchor: middle; }
.poster-register-value { fill: #1b3444; font: 43px Georgia, serif; font-variant-numeric: tabular-nums; }
.poster-register-caption { fill: #4b6069; font-size: 13px; }
.poster-register line { stroke-width: 2.3; }
.poster-trace { stroke: #a34536; stroke-width: .85; stroke-dasharray: 2 3; opacity: .65; }
.poster-year { cursor: pointer; transition: opacity 180ms var(--atlas-ease); }
.poster-year[aria-disabled="true"] { cursor: default; }
.poster-hit { fill: transparent; }
.poster-marks { fill: none; stroke-linecap: round; opacity: .76; pointer-events: none; transition: opacity 180ms var(--atlas-ease); }
.poster-marks.is-weighted { opacity: .96; }
.poster-year.is-muted { opacity: .44; }
.poster-marks.is-filtered { opacity: .09; }
.poster-annotation { color: #a34536; cursor: pointer; outline: none; }
.poster-annotation path { fill: none; stroke: currentColor; stroke-width: 1; }
.poster-annotation circle { stroke: currentColor; fill: #fff8ee; }
.poster-annotation text { fill: currentColor; font-size: 13px; font-weight: 600; }
.poster-annotation .poster-note-value { fill: #233b47; font: 22px Georgia, "Songti SC", SimSun, serif; }
.poster-note-rule { stroke: #c9ccbf; stroke-width: .8; }
.poster-note-color { stroke-width: 1.45; }
.poster-note-details text { fill: #4c626c; font-size: 11.5px; font-weight: 400; }
.poster-note-details .poster-note-count { font-family: Georgia, serif; font-variant-numeric: tabular-nums; }
.poster-annotation:is(:hover, :focus-visible) circle { fill: #a34536; }
.poster-reading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 14px;
  padding: 6px 20px 13px;
  border-top: 1px solid #d8d4cb;
}
.poster-key { display: flex; gap: 4px 13px; flex-wrap: wrap; }
.poster-reading button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 30px;
  padding: 3px 2px;
  border: 0;
  background: transparent;
  color: #263c45;
  cursor: pointer;
  font: 13px/1.35 system-ui, sans-serif;
}
.poster-key button[aria-pressed="true"], .poster-reading button:hover { text-decoration: underline; text-underline-offset: 4px; }
.poster-key i { width: 7px; height: 7px; border-radius: 50%; }
.poster-year-picker { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 5px 9px; }
.poster-year-picker select { min-height: 34px; padding: 4px 5px; border: 1px solid #c8d3d9; border-radius: 6px; background: #fffefa; color: #263c45; font: inherit; font-size: 13px; }
.poster-reading .poster-date { color: #9a4032; }
.is-compact .poster-rules text { font-size: 12px; }
.is-compact .poster-register-value { font-size: 26px; }
.is-compact .poster-register-caption { font-size: 10.5px; }
.is-compact .poster-register line { stroke-width: 1.45; }
.is-compact .poster-profile { stroke-width: .65; }
.is-compact .poster-profile.is-fine { stroke-width: .36; }
.is-compact .poster-profile.is-deep { stroke-width: .9; }
.is-compact .poster-annotation text { font-size: 12px; }
.is-compact .poster-annotation .poster-note-value { font-size: 15px; }
@media (max-width: 680px) {
  .poster-reading { padding-inline: 9px; }
  .poster-key { gap: 2px 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .poster-year, .poster-marks, .poster-grooves { transition: none; }
}
</style>
