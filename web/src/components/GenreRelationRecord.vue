<script setup>
import { computed, ref } from 'vue'
import { arc } from 'd3'
import { FLOW_TYPES, EDGE_LABELS, formatCount } from '../lib/palette'
import { summarizeNeighbors, orbitRibbons } from '../lib/atlas'
import { voiceColors as FLOW_COLORS, directionColors as inks, scoreGenreColor as genreColor } from '../lib/genreScorePalette'

const props = defineProps({
  flows: { type: Array, required: true },
  genres: { type: Array, required: true },
  genreColors: { type: Object, required: true },
  focus: { type: String, required: true },
  years: { type: Array, required: true },
  selectedYear: { type: Number, default: null },
  selectedPair: { type: Object, default: null },
})
const emit = defineEmits(['select-flow', 'select-year', 'focus', 'inspect'])
const hovered = ref('')
const hoverYear = ref(null)
const direction = ref('all')
const periodFlows = computed(() => props.selectedYear == null ? props.flows : props.flows.filter(flow => flow.year === props.selectedYear))
const neighbors = computed(() => summarizeNeighbors(periodFlows.value, props.focus))
const rim = arc().innerRadius(156).outerRadius(162).cornerRadius(2)
const layout = computed(() => {
  const slice = Math.PI * 2 / Math.max(1, props.genres.length)
  return {
    compact: false, radius: 156,
    points: props.genres.map((name, index) => {
      const offset = (index + .5) * slice
      const peer = neighbors.value.get(name)
      const total = (peer?.in ?? 0) + (peer?.out ?? 0)
      const span = slice * .40
      return {
        id: name, name, offset, span, total, color: props.genreColors[name] ?? genreColor(index),
        x: Math.sin(offset) * 184, y: -Math.cos(offset) * 184,
        labelX: Math.sin(offset) * 210, labelY: -Math.cos(offset) * 210,
        rotation: offset * 180 / Math.PI + (offset > Math.PI / 2 && offset < Math.PI * 1.5 ? 180 : 0),
        band: rim({ startAngle: offset - span, endAngle: offset + span }),
        grooves: [5.5, 8, 10.5],
      }
    }),
  }
})
const routes = computed(() => orbitRibbons(layout.value, props.focus, neighbors.value, direction.value)
  .map(route => ({
    ...route,
    source: route.direction === 'out' ? props.focus : route.peer,
    target: route.direction === 'in' ? props.focus : route.peer,
  })))
const selectedRoute = computed(() => routes.value.find(route =>
  route.source === props.selectedPair?.source && route.target === props.selectedPair?.target))
const active = computed(() => routes.value.find(route => route.id === hovered.value) ?? selectedRoute.value)
const neighborTotal = computed(() => routes.value.reduce((sum, route) => sum + route.value, 0))
const annual = computed(() => {
  const groups = new Map(props.years.map(year => [year, { year, total: 0, types: {} }]))
  for (const flow of props.flows) {
    if (flow.source !== props.focus && flow.target !== props.focus) continue
    const row = groups.get(flow.year)
    if (!row) continue
    row.total += flow.value
    row.types[flow.type] = (row.types[flow.type] ?? 0) + flow.value
  }
  const max = Math.max(1, ...[...groups.values()].flatMap(row => Object.values(row.types)))
  const slice = (Math.PI * 2 - .25) / Math.max(1, props.years.length)
  const draw = arc()
  return [...groups.values()].map((row, index) => {
    const start = .125 + index * slice
    const angle = start + slice / 2
    return {
      ...row, angle,
      labelX: Math.sin(angle) * 292, labelY: -Math.cos(angle) * 292,
      hit: draw({ innerRadius: 236, outerRadius: 277, startAngle: start, endAngle: start + slice }),
      bands: FLOW_TYPES.map((type, lane) => ({
        type,
        count: row.types[type] ?? 0,
        d: draw({ innerRadius: 239 + lane * 7, outerRadius: 243.4 + lane * 7,
          startAngle: start + .008, endAngle: start + Math.max(.018, slice * .88) }),
        opacity: row.types[type] ? .28 + .72 * Math.sqrt(row.types[type] / max) : .045,
      })),
    }
  })
})
const shownYear = computed(() => annual.value.find(row => row.year === hoverYear.value))
function choose(route) { emit('select-flow', { ...route, year: props.selectedYear }) }
function selectYear(value) { emit('select-year', value === '' ? null : Number(value)) }
</script>

<template>
  <div class="genre-record" data-visual>
    <div class="record-controls">
      <div class="record-directions" role="group" aria-label="流派联系方向">
        <button v-for="(label, key) in { all: '双向联系', in: '灵感流入', out: '影响流出' }" :key="key"
          type="button" :aria-pressed="direction === key" @click="direction = key">{{ label }}</button>
      </div>
      <label>年份 <select class="op-select" :value="selectedYear ?? ''" @change="selectYear($event.target.value)">
        <option value="">全部</option>
        <option v-for="year in years" :key="year" :value="year">{{ year }}</option>
      </select></label>
    </div>
    <svg class="record-disc" viewBox="-322 -322 644 644" role="group" aria-label="流派关系唱片，外圈为引用年代，内圈为流派联系">
      <defs>
        <radialGradient id="score-disc-vinyl" cx=".45" cy=".35" r=".72">
          <stop stop-color="#26374a" /><stop offset=".37" stop-color="#101e31" />
          <stop offset=".74" stop-color="#18293d" /><stop offset=".86" stop-color="#101b2a" /><stop offset="1" stop-color="#263345" />
        </radialGradient>
        <marker v-for="(color, side) in inks" :id="'record-tip-' + side" :key="side"
          viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0L6,3L0,6Z" :fill="color" /></marker>
      </defs>
      <g class="record-surface" aria-hidden="true" pointer-events="none">
        <circle r="267" fill="url(#score-disc-vinyl)" />
        <circle v-for="r in [66,72,91,111,136,157,172,194,224,231,262,267]" :key="r" :r="r" fill="none" stroke="#c0d6f2" stroke-opacity=".13" stroke-width=".65" />
      </g>
      <g class="record-hairlines" aria-hidden="true">
        <circle v-for="radius in [65,70,75,80,110,125,143,166,169,229,233,281]" :key="radius" :r="radius" />
      </g>
      <g class="record-years">
        <g v-for="(row,index) in annual" :key="row.year" class="record-year"
          :class="{ 'is-active': selectedYear === row.year || hoverYear === row.year }"
          :data-year="row.year" :data-count="row.total"
          role="button" :tabindex="row.total && (index % 5 === 0 || row.year === selectedYear) ? 0 : -1"
          :aria-label="row.year + ' 年，' + focus + ' 的双向引用 ' + row.total + ' 条'"
          :aria-pressed="selectedYear === row.year"
          @pointerenter="hoverYear = row.year" @pointerleave="hoverYear = null"
          @focus="hoverYear = row.year" @blur="hoverYear = null"
          @click="emit('select-year', row.year)" @keydown.enter.prevent="emit('select-year', row.year)"
          @keydown.space.prevent="emit('select-year', row.year)">
          <path v-for="band in row.bands" :key="band.type" :d="band.d" :fill="FLOW_COLORS[band.type]" :fill-opacity="band.opacity" />
          <path :d="row.hit" class="record-year-hit" />
          <text v-if="row.year % 10 === 0" :x="row.labelX" :y="row.labelY" text-anchor="middle" dominant-baseline="middle">{{ row.year }}</text>
        </g>
      </g>
      <g class="record-links">
        <g v-for="route in routes" :key="route.id" class="record-route"
          :class="{ 'is-active': active?.id === route.id, 'is-muted': active && active.id !== route.id }"
          :data-source="route.source" :data-target="route.target" :data-count="route.value"
          role="button" tabindex="0" :aria-pressed="selectedRoute?.id === route.id"
          :aria-label="route.source + ' → ' + route.target + '，' + route.value + ' 条引用'"
          @pointerenter="hovered = route.id" @pointerleave="hovered = ''" @focus="hovered = route.id" @blur="hovered = ''"
          @click="choose(route)" @keydown.enter.prevent="choose(route)" @keydown.space.prevent="choose(route)">
          <path class="record-ribbon" :d="route.path" :fill="inks[route.direction]" />
          <path class="record-thread" :d="route.trace" :stroke="inks[route.direction]" :marker-end="'url(#record-tip-' + route.direction + ')'" />
        </g>
      </g>
      <g v-if="active" :key="active.id + selectedYear" class="record-signal" aria-hidden="true">
        <path :d="active.trace" pathLength="1" />
        <path :d="active.trace" pathLength="1" class="echo" />
      </g>
      <g class="record-genres">
        <g v-for="node in layout.points" :key="node.name" class="record-genre" :class="{ 'is-focus': node.name === focus }"
          role="button" tabindex="0" :aria-label="'聚焦 ' + node.name" :aria-pressed="node.name === focus"
          @click="emit('focus', node.name)" @keydown.enter.prevent="emit('focus', node.name)"
          @keydown.space.prevent="emit('focus', node.name)">
          <path :d="node.band" :fill="node.color" />
          <line :x1="node.x * .88" :y1="node.y * .88" :x2="node.x" :y2="node.y" :stroke="node.color" />
          <circle :cx="node.x" :cy="node.y" r="14" class="record-medallion" />
          <circle v-for="radius in node.grooves" :key="radius" :cx="node.x" :cy="node.y" :r="radius" :stroke="node.color" class="record-groove" />
          <circle :cx="node.x" :cy="node.y" r="2.2" :fill="node.color" />
          <text :transform="'translate(' + node.labelX + ',' + node.labelY + ') rotate(' + node.rotation + ')'"
            text-anchor="middle" dominant-baseline="middle">{{ node.name }}</text>
        </g>
      </g>
      <g class="record-center" aria-hidden="true">
        <circle r="58" />
        <text y="-16" class="record-center-label">入图引用</text>
        <text y="12" class="record-center-value">{{ formatCount(neighborTotal) }}</text>
        <text y="32">{{ selectedYear ?? '当前时间窗' }}</text>
      </g>
    </svg>
    <div class="record-readout" role="status">
      <template v-if="shownYear"><strong>{{ shownYear.year }} 年</strong><span>{{ focus }} · {{ shownYear.total }} 条双向引用</span></template>
      <template v-else-if="active"><strong>{{ active.source }} → {{ active.target }}</strong><span>{{ formatCount(active.value) }} 条引用</span></template>
      <template v-else><strong>{{ focus }}</strong><span>{{ genres.length }} 个入图流派 · 点击连线选择引用</span></template>
      <button v-if="selectedPair || selectedYear != null" type="button" class="atlas-inline" @click="emit('inspect')">打开证据 →</button>
    </div>
    <div class="record-legend">
      <span><i :style="{ background: inks.in }" />流入</span><span><i :style="{ background: inks.out }" />流出</span>
      <span v-for="type in FLOW_TYPES" :key="type"><i :style="{ background: FLOW_COLORS[type] }" />{{ EDGE_LABELS[type] }}</span>
    </div>
  </div>
</template>

<style scoped>
.genre-record { min-width:0; color:var(--score-ink); }
.record-controls,.record-controls label { display:flex;align-items:center;gap:8px; }
.record-controls { justify-content:space-between;flex-wrap:wrap;font-size:12px;min-height:42px; }
.record-controls select { min-height:30px;padding:3px 7px; }
.record-directions { display:flex;gap:4px; }
.record-directions button { border:0;border-bottom:1px solid transparent;background:transparent;color:var(--score-soft);padding:6px 8px;font:inherit;font-size:12px;cursor:pointer;transition:color 180ms,border-color 180ms; }
.record-directions button[aria-pressed='true'] { color:var(--score-blue);border-color:var(--score-blue); }
.record-disc { display:block;width:100%;max-height:690px;overflow:visible; }
.record-hairlines { fill:none;stroke:var(--score-rule);stroke-width:.55;pointer-events:none; }
.record-year { cursor:pointer;outline:none; }
.record-year-hit { fill:transparent;stroke:transparent;stroke-width:.9; }
.record-year:is(.is-active,:focus-visible) .record-year-hit { stroke:var(--score-gold);fill:var(--score-focus-fill); }
.record-year text { font:11px Georgia,serif;fill:var(--score-soft);pointer-events:none; }
.record-route { cursor:pointer;outline:none;transition:opacity 220ms ease; }
.record-route.is-muted { opacity:.15; }
.record-ribbon { fill-opacity:.15;transition:fill-opacity 220ms ease; }
.record-thread { fill:none;stroke-width:.75;opacity:.65; }
.record-route:is(.is-active,:focus-visible) .record-ribbon { fill-opacity:.32; }
.record-route:is(.is-active,:focus-visible) .record-thread { stroke-width:1.4;opacity:1; }
.record-signal { fill:none;stroke:var(--score-gold);stroke-width:2;pointer-events:none; }
.record-signal path { stroke-dasharray:.07 .93;animation:record-signal 1.6s ease-out both; }
.record-signal .echo { animation-delay:150ms;stroke-width:1; }
@keyframes record-signal { from { stroke-dashoffset:0;opacity:1; } to { stroke-dashoffset:-1;opacity:0; } }
.record-genre { cursor:pointer;outline:none; }
.record-genre line { stroke-width:.7; }
.record-medallion { fill:var(--score-panel);stroke:var(--score-rule);stroke-width:.5; }
.record-groove { fill:none;stroke-width:.6;opacity:.75; }
.record-genre text { font:11px Georgia,serif;fill:var(--score-ink); }
.record-genre:is(:hover,:focus-visible,.is-focus) .record-medallion { fill:var(--score-raised);stroke:var(--score-blue); }
.record-genre.is-focus text { font-weight:700;fill:var(--score-blue); }
.record-center { pointer-events:none; }
.record-center circle { fill:var(--score-panel);stroke:var(--score-rule);stroke-width:.6; }
.record-center text { font:11px Georgia,serif;fill:var(--score-soft);text-anchor:middle; }
.record-center .record-center-value { font-size:29px;fill:var(--score-ink); }
.record-center .record-center-label { font:10px system-ui,sans-serif; }
.record-readout { min-height:58px;display:flex;align-items:baseline;align-content:center;flex-wrap:wrap;gap:4px 12px;padding:10px 0;border-block:1px solid var(--score-rule);font-size:12px; }
.record-readout strong { font-weight:600; }
.record-readout button { margin-left:auto;font-size:12px; }
.record-legend { display:flex;align-items:center;justify-content:center;gap:7px 12px;flex-wrap:wrap;padding:12px 0;font-size:10px;color:var(--score-soft); }
.record-legend span { display:flex;align-items:center;gap:4px; }
.record-legend i { width:8px;height:3px;background:currentColor; }
@media(max-width:600px) {
 .record-genre text { font-size:13px; }
 .record-controls { justify-content:center; }
 .record-legend { font-size:11px; }
}
@media(prefers-reduced-motion:reduce) {
 .record-route,.record-ribbon,.record-directions button { transition:none; }
 .record-signal path { animation:none;display:none; }
}
</style>
