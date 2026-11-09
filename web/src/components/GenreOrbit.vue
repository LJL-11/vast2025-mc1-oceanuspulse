<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { FLOW_TONES, observeChartSize, orbitLayout, orbitRibbons } from '../lib/atlas'
import { EDGE_LABELS, FLOW_COLORS, FLOW_TYPES } from '../lib/palette'

const props = defineProps({
  genres: { type: Array, required: true },
  focus: { type: String, required: true },
  neighbors: { type: Map, required: true },
  selected: { type: String, default: '' },
  direction: { type: String, default: 'all' },
  motion: { type: Boolean, default: true },
  years: { type: Array, required: true },
  yearRange: { type: Array, required: true },
  preview: { type: Object, default: null },
  previewNeighbors: { type: Map, default: null },
})
const emit = defineEmits(['select', 'focus', 'year', 'preview-year'])
const canvas = ref(null)
const hovered = ref('')
const size = ref({ width: 900, height: 515 })
const inks = FLOW_TONES
let stopMeasuring

onMounted(() => {
  stopMeasuring = observeChartSize(canvas.value, (width, height) => {
    if (width !== size.value.width || height !== size.value.height) size.value = { width, height }
  })
})
onBeforeUnmount(() => stopMeasuring?.())

const layout = computed(() => orbitLayout(props.genres, size.value.width, size.value.height))
const visibleNeighbors = computed(() => props.previewNeighbors ?? props.neighbors)
const activePeer = computed(() => props.preview ? '' : hovered.value || props.selected)
const links = computed(() => orbitRibbons(layout.value, props.focus, visibleNeighbors.value, props.direction))
const traces = computed(() => props.motion
  ? links.value.filter(link => link.peer === activePeer.value)
  : [])
const activeCount = computed(() => links.value.reduce((sum, link) => sum + link.value, 0))
const activeStats = computed(() => visibleNeighbors.value.get(activePeer.value))
const yearRing = computed(() => {
  const max = Math.max(1, ...props.years.flatMap(row => [row.in, row.out]))
  const height = layout.value.compact ? 9 : 12
  return props.years.map((row, index) => {
    const angle = index * Math.PI * 2 / props.years.length - Math.PI / 2
    const from = ringPoint(angle, 0)
    const outTip = ringPoint(angle, height * Math.sqrt(row.out / max))
    const inTip = ringPoint(angle, -height * Math.sqrt(row.in / max))
    const label = ringPoint(angle, -8)
    const beads = size.value.width < 860 ? [] : FLOW_TYPES.flatMap((type, index) => {
      const counts = row.types[type]
      const count = counts ? yearCount(counts) : 0
      return count ? [{
        type, count, ...ringPoint(angle, 14 + index * 4.4),
        radius: 1.3 + Math.min(2.9, Math.sqrt(count) * .55),
      }] : []
    })
    return { ...row, angle, from, outTip, inTip, label, beads }
  })
})
function yearCount(row) {
  return props.direction === 'all' ? row.in + row.out : row[props.direction]
}
const landmarks = computed(() => {
  if (size.value.width < 860) return []
  const active = yearRing.value.filter(yearCount)
  if (!active.length) return []
  const first = active[0]
  const peak = active.reduce((best, row) => yearCount(row) > yearCount(best) ? row : best)
  return first === peak
    ? [{ ...peak, title: '引用峰年' }]
    : [{ ...first, title: '最早引用' }, { ...peak, title: '引用峰年' }]
})
const threadYears = computed(() => {
  const yearById = new Map(yearRing.value.map(row => [row.year, row]))
  const guide = !props.preview && !activePeer.value
  const guidePeers = guide ? new Set([...visibleNeighbors.value.values()]
    .filter(yearCount).sort((a, b) => yearCount(b) - yearCount(a)).slice(0, 3).map(row => row.id)) : null
  return layout.value.points.flatMap(node => {
    if (guide ? !guidePeers.has(node.id) : !props.preview && node.id !== activePeer.value) return []
    const groups = new Map()
    for (const row of visibleNeighbors.value.get(node.id)?.rows ?? []) {
      const dir = row.source === props.focus ? 'out' : 'in'
      if (props.direction !== 'all' && dir !== props.direction) continue
      const key = row.year + ':' + dir
      if (!groups.has(key)) groups.set(key, { year: row.year, dir, value: 0 })
      groups.get(key).value += row.value
    }
    const rows = [...groups]
    if (guide) rows.sort((a, b) => b[1].value - a[1].value).splice(2)
    return rows.flatMap(([id, item], index) => {
      const mark = yearById.get(item.year)
      if (!mark) return []
      const offset = -13 - (index % 5) * (layout.value.compact ? 2 : 4)
      const start = ringPoint(mark.angle, 0)
      const arcStart = ringPoint(mark.angle, offset)
      const elbow = ringPoint(node.angle, offset)
      const radius = layout.value.radius + layout.value.ringGap + offset
      const delta = Math.atan2(Math.sin(node.angle - mark.angle), Math.cos(node.angle - mark.angle))
      const arc = 'A ' + radius + ' ' + radius + ' 0 0 ' + (delta >= 0 ? 1 : 0) + ' ' + elbow.x + ' ' + elbow.y
      return [{
        ...item, guide, id: node.id + ':' + id,
        path: 'M ' + start.x + ' ' + start.y + ' L ' + arcStart.x + ' ' + arcStart.y + ' ' + arc + ' L ' + node.x + ' ' + node.y,
      }]
    })
  })
})
const yearsWithThreads = computed(() => new Set(threadYears.value.filter(row => !row.guide).map(row => row.year)))
const previewPeriod = computed(() => {
  if (!props.preview) return ''
  const { start, end } = props.preview
  return start === end ? String(start) : start + '—' + end
})

function ringPoint(angle, offset) {
  const radius = layout.value.radius + layout.value.ringGap + offset
  return {
    x: layout.value.cx + radius * Math.cos(angle),
    y: layout.value.cy + radius * Math.sin(angle),
  }
}
function yearLabel(row) {
  return row.year + ' 年，流入 ' + row.in + '，流出 ' + row.out
}
function previewYear(row) {
  emit('preview-year', { start: row.year, end: row.year, in: row.in, out: row.out })
}

function nodeLabel(node) {
  if (node.id === props.focus) return node.name + '，当前焦点流派'
  const pair = visibleNeighbors.value.get(node.id)
  return `${node.name}，流入 ${pair?.in ?? 0}，流出 ${pair?.out ?? 0}`
}
</script>

<template>
  <div ref="canvas" class="atlas-orbit" :class="{ 'has-motion': motion }" data-visual>
    <svg :viewBox="`0 0 ${size.width} ${size.height}`" role="group"
      aria-label="流派关系图，选择外围流派查看双向引用">
      <g aria-hidden="true" class="atlas-grooves">
        <circle v-for="offset in [-9, 12, layout.ringGap * .46, layout.ringGap - 9]" :key="offset"
          :cx="layout.cx" :cy="layout.cy" :r="layout.radius + offset" />
        <circle class="atlas-year-groove" :cx="layout.cx" :cy="layout.cy" :r="layout.radius + layout.ringGap" />
      </g>
      <g :key="focus + ':' + direction" class="atlas-routes" aria-hidden="true" :transform="`translate(${layout.cx},${layout.cy})`">
        <path v-for="link in links" :key="link.id" :d="link.path" class="atlas-ribbon"
          :fill="inks[link.direction]" :stroke="inks[link.direction]"
          :class="{ 'is-dim': activePeer && activePeer !== link.peer, 'is-active': activePeer === link.peer }" />
        <path v-for="link in traces" :key="`${link.id}:${link.trace}`" :d="link.trace"
          class="atlas-trace" pathLength="1" stroke-width="1.7" />
      </g>
      <g aria-hidden="true" class="atlas-year-threads">
        <path v-for="thread in threadYears" :key="thread.id" :d="thread.path"
          :class="{ 'is-guide': thread.guide }"
          :stroke="inks[thread.dir]" :stroke-width=".75 + Math.min(2, Math.sqrt(thread.value) * .38)" />
      </g>
      <g v-for="mark in yearRing" :key="mark.year" class="atlas-year-mark"
        :class="{ 'is-outside': mark.year < yearRange[0] || mark.year > yearRange[1], 'is-linked': yearsWithThreads.has(mark.year) }"
        role="button" tabindex="-1" :aria-label="yearLabel(mark)" @click="emit('year', mark.year)"
        @pointerenter="previewYear(mark)" @pointerleave="emit('preview-year', null)">
        <title>{{ yearLabel(mark) }}</title>
        <circle :cx="mark.from.x" :cy="mark.from.y" r="6" fill="transparent" />
        <circle :cx="mark.from.x" :cy="mark.from.y" :r="yearsWithThreads.has(mark.year) ? 3 : 1.3" class="atlas-year-dot" />
        <line v-if="mark.out && direction !== 'in'" :x1="mark.from.x" :y1="mark.from.y"
          :x2="mark.outTip.x" :y2="mark.outTip.y" :stroke="inks.out" />
        <line v-if="mark.in && direction !== 'out'" :x1="mark.from.x" :y1="mark.from.y"
          :x2="mark.inTip.x" :y2="mark.inTip.y" :stroke="inks.in" />
        <circle v-for="bead in mark.beads" :key="bead.type" class="atlas-type-bead"
          :cx="bead.x" :cy="bead.y" :r="bead.radius" :fill="FLOW_COLORS[bead.type]">
          <title>{{ mark.year }} · {{ EDGE_LABELS[bead.type] }} · {{ bead.count }} 条</title>
        </circle>
        <text v-if="!layout.compact && mark.year % 10 === 0 && mark.year !== yearRing.at(-1)?.year"
          :x="mark.label.x" :y="mark.label.y" text-anchor="middle" dominant-baseline="central">{{ mark.year }}</text>
      </g>
      <g v-for="node in layout.points" :key="node.id"
        class="atlas-orbit-node" :class="{ 'is-active': activePeer === node.id, 'is-home': node.id === focus, 'is-quiet': !visibleNeighbors.has(node.id) }"
        role="button" tabindex="0" :aria-label="nodeLabel(node)" :aria-pressed="selected === node.id || node.id === focus"
        @pointerenter="hovered = node.id === focus ? '' : node.id" @pointerleave="hovered = ''"
        @focus="hovered = node.id === focus ? '' : node.id" @blur="hovered = ''"
        @click="emit('select', node.id === focus ? '' : node.id)" @dblclick="emit('focus', node.id)"
        @keydown.enter.prevent="emit('select', node.id === focus ? '' : node.id)"
        @keydown.space.prevent="emit('select', node.id === focus ? '' : node.id)">
        <title>{{ nodeLabel(node) }}</title>
        <circle :cx="node.x" :cy="node.y" :r="layout.compact ? 12 : 16" fill="transparent" />
        <path v-if="!layout.compact" class="atlas-leader" aria-hidden="true"
          :d="`M${node.x},${node.y} L${node.labelX + (node.left ? 5 : -5)},${node.labelY}`" />
        <path class="atlas-node-band" :d="node.band" :fill="node.color"
          :transform="`translate(${layout.cx},${layout.cy})`" />
        <text v-if="!layout.compact" :x="node.labelX" :y="node.labelY"
          :text-anchor="node.left ? 'end' : 'start'" dominant-baseline="central">{{ node.name }}</text>
      </g>
    </svg>
    <div v-if="landmarks.length" class="atlas-orbit-landmarks" aria-label="引用年份标记">
      <button v-for="mark in landmarks" :key="mark.year" type="button" @click="emit('year', mark.year)"
        @pointerenter="previewYear(mark)" @pointerleave="emit('preview-year', null)"
        @focus="previewYear(mark)" @blur="emit('preview-year', null)">
        <span>{{ mark.title }}</span>
        <strong>{{ mark.year }}<small>{{ yearCount(mark) }} 条</small></strong>
      </button>
    </div>
    <div class="atlas-orbit-caption">
      <div class="atlas-orbit-core">
        <strong>{{ focus }}</strong><span>{{ previewPeriod ? previewPeriod + ' · ' : '' }}{{ activeCount.toLocaleString('zh-CN') }} 条引用</span>
      </div>
      <div v-if="activePeer" class="atlas-orbit-readout">
        <strong>{{ activePeer }}</strong>
        <span><i class="in" />{{ activeStats?.in ?? 0 }}</span>
        <span><i class="out" />{{ activeStats?.out ?? 0 }}</span>
      </div>
      <div v-else-if="size.width >= 860" class="atlas-orbit-type-key" aria-label="外圈引用类型">
        <span v-for="type in FLOW_TYPES" :key="type">
          <i :style="{ background: FLOW_COLORS[type] }" />{{ EDGE_LABELS[type] }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.atlas-orbit {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 290px;
  overflow: hidden;
  background: radial-gradient(circle at 50% 49%, #f0f6f8, var(--journal-stock) 72%);
}
.atlas-orbit svg { display: block; width: 100%; height: 100%; overflow: visible; }
.atlas-grooves { fill: none; stroke: #b1c1c9; stroke-width: .8; }
.atlas-grooves circle:nth-child(3) { stroke-dasharray: 2 4; }
.atlas-grooves .atlas-year-groove { stroke: #819fac; stroke-dasharray: 1 3; }
.atlas-routes { stroke-linecap: round; pointer-events: none; }
.atlas-orbit.has-motion .atlas-routes { animation: atlas-routes-in 330ms ease both; }
@keyframes atlas-routes-in { from { opacity: .42; } to { opacity: 1; } }
.atlas-ribbon { opacity: .64; stroke-width: .55; transition: opacity 180ms ease; }
.atlas-ribbon.is-dim { opacity: .075; }
.atlas-ribbon.is-active { opacity: .96; stroke-width: .9; }
.atlas-routes > .atlas-trace {
  fill: none;
  stroke: #f9fdff;
  stroke-dasharray: .15 1;
  animation: atlas-route-travel 1250ms cubic-bezier(.22,.65,.35,1) both;
}
@keyframes atlas-route-travel {
  0% { stroke-dashoffset: .17; opacity: 0; }
  15% { opacity: 1; }
  82% { opacity: 1; }
  100% { stroke-dashoffset: -1; opacity: 0; }
}
.atlas-orbit-node { cursor: pointer; outline: none; }
.atlas-node-band { stroke: #fefdfa; stroke-width: .7; transition: opacity 180ms ease; }
.atlas-orbit-node.is-quiet .atlas-node-band { opacity: .5; }
.atlas-orbit-node:is(.is-active, .is-home, :focus-visible) .atlas-node-band { fill: #224e69; stroke: #fefdf8; stroke-width: 1.4; opacity: 1; }
.atlas-leader { fill: none; stroke: #93aab7; stroke-width: .8; opacity: .7; }
.atlas-orbit-node:is(.is-active, .is-home) .atlas-leader { stroke: #406a82; opacity: 1; }
.atlas-orbit-node text { font-size: 13px; fill: #35566a; paint-order: stroke; stroke: #faf9f4; stroke-width: 3; }
.atlas-orbit-node:is(.is-active, .is-home) text { fill: #18354c; font-weight: 700; }
.atlas-year-threads { fill: none; pointer-events: none; }
.atlas-year-threads path { opacity: .61; stroke-linecap: round; }
.atlas-year-threads path.is-guide { opacity: .31; }
.atlas-year-mark { cursor: pointer; transition: opacity 150ms ease; }
.atlas-year-mark.is-outside { opacity: .25; }
.atlas-year-mark:hover, .atlas-year-mark.is-linked { opacity: 1; }
.atlas-year-dot { fill: #718c9e; }
.atlas-year-mark.is-linked .atlas-year-dot { fill: #275875; }
.atlas-year-mark line { stroke-width: 2; stroke-linecap: round; }
.atlas-year-mark text { fill: #3e6177; font-size: 12px; paint-order: stroke; stroke: #faf9f4; stroke-width: 3.5; pointer-events: none; }
.atlas-type-bead { stroke: #fdfaf2; stroke-width: .55; }
.atlas-orbit-landmarks {
  position: absolute;
  inset: 12px 16px auto;
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}
.atlas-orbit-landmarks button {
  display: grid;
  gap: 2px;
  padding: 4px 10px;
  border: 0;
  border-left: 1px solid #a1b7c4;
  background: transparent;
  color: #486579;
  text-align: left;
  font-size: 12px;
  cursor: pointer;
  pointer-events: auto;
}
.atlas-orbit-landmarks button:is(:hover, :focus-visible) { border-color: var(--journal-accent); color: var(--journal-accent); }
.atlas-orbit-landmarks strong { font: 500 24px/1 var(--atlas-display); color: var(--atlas-ink); }
.atlas-orbit-landmarks small { margin-left: 8px; font: 13px/1.3 system-ui, sans-serif; color: #486579; }
.atlas-orbit-caption {
  position: absolute;
  inset: auto 16px 12px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 14px;
  color: var(--atlas-ink);
  pointer-events: none;
}
.atlas-orbit-core, .atlas-orbit-readout { display: flex; align-items: baseline; flex-wrap: wrap; gap: 3px 9px; }
.atlas-orbit-core span { font-size: 13px; color: #486579; }
.atlas-orbit-core strong {
  font: 500 clamp(17px, 1.6vw, 23px)/1.08 var(--atlas-display);
}
.atlas-orbit-readout {
  color: var(--atlas-ink);
  font-size: 13px;
}
.atlas-orbit-readout strong { font-weight: 600; }
.atlas-orbit-readout span { display: inline-flex; gap: 4px; align-items: center; }
.atlas-orbit-readout i { display: inline-block; width: 6px; height: 6px; border-radius: 50%; }
.atlas-orbit-readout .in { background: #b36935; }
.atlas-orbit-readout .out { background: #26799f; }
.atlas-orbit-type-key { display: flex; flex-wrap: wrap; gap: 4px 10px; color: #486579; font-size: 12px; }
.atlas-orbit-type-key span { display: inline-flex; align-items: center; gap: 4px; }
.atlas-orbit-type-key i { width: 6px; height: 6px; border-radius: 50%; }
@media (prefers-reduced-motion: reduce) {
  .atlas-ribbon, .atlas-node-band, .atlas-year-mark { transition: none; }
  .atlas-orbit.has-motion .atlas-routes { animation: none; }
  .atlas-routes > .atlas-trace { animation: none; display: none; }
}
</style>
