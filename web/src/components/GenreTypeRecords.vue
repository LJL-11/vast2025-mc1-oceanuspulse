<script setup>
import { computed, ref } from 'vue'
import { range } from 'd3'
import { EDGE_LABELS, FLOW_TYPES, formatCount } from '../lib/palette'
import { voiceColors as FLOW_COLORS } from '../lib/genreScorePalette'
const props = defineProps({
  flows: { type: Array, required: true },
  extent: { type: Array, required: true },
  selectedYear: { type: Number, default: null },
  selectedType: { type: String, default: '' },
  visibleTypes: { type: Array, required: true },
})
const emit = defineEmits(['select-type'])
const hover = ref(null)
const years = computed(() => range(props.extent[0], props.extent[1] + 1))
const ringStep = computed(() => 80 / Math.max(1, years.value.length - 1))
const summary = computed(() => {
  const totals = new Map()
  for (const flow of props.flows) {
    const key = flow.type + '|' + flow.year
    totals.set(key, (totals.get(key) ?? 0) + flow.value)
  }
  return FLOW_TYPES.map(type => {
    const rows = years.value.map((year, i) => ({
      type, year, value: totals.get(type + '|' + year) ?? 0, radius: 28 + i * ringStep.value,
    }))
    const peak = rows.reduce((best, row) => row.value > best.value ? row : best, rows[0])
    return { type, color: FLOW_COLORS[type], rows, peak, total: rows.reduce((sum, row) => sum + row.value, 0) }
  })
})
const max = computed(() => Math.max(1, ...summary.value.flatMap(record => record.rows.map(row => row.value))))
const start = Math.PI * .78
const span = Math.PI * 1.78
const records = computed(() => {
  return summary.value.map(record => ({
    ...record,
    rows: record.rows.map(row => {
      const end = start + row.value / max.value * span
      const x0 = Math.sin(start) * row.radius
      const y0 = -Math.cos(start) * row.radius
      const x1 = Math.sin(end) * row.radius
      const y1 = -Math.cos(end) * row.radius
      const unit = row.radius * span / max.value
      return {
        ...row,
        path: row.value ? 'M' + x0 + ',' + y0 + 'A' + row.radius + ',' + row.radius + ',0,' + (end - start > Math.PI ? 1 : 0) + ',1,' + x1 + ',' + y1 : '',
        dash: unit * .74 + ' ' + unit * .26,
      }
    }),
  }))
})
const previewYear = computed(() => hover.value?.year ?? props.selectedYear)
const ticks = computed(() => years.value.filter(year => year % 10 === 0).map(year => ({
  year, radius: 28 + (year - props.extent[0]) * ringStep.value,
})))
const activeRows = computed(() => records.value.map(record => ({
  ...record,
  current: record.rows.find(row => row.year === previewYear.value) ?? record.peak,
})))
function pointerRow(event, record) {
  const transform = event.currentTarget.getScreenCTM()
  if (!transform) return null
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(transform.inverse())
  const radius = Math.hypot(point.x, point.y)
  if (radius < 25 || radius > 114) return null
  const index = Math.max(0, Math.min(record.rows.length - 1, Math.round((radius - 28) / ringStep.value)))
  return record.rows[index]
}
function preview(event, record) {
  if (event.pointerType === 'touch') return
  const row = pointerRow(event, record)
  hover.value = row ? { year: row.year, type: record.type } : null
}
function choose(record, year = previewYear.value ?? record.peak.year) {
  emit('select-type', { type: record.type, year })
}
function pick(event, record) {
  const row = pointerRow(event, record)
  if (row) choose(record, row.year)
}
function move(event, record, offset) {
  event.preventDefault()
  const current = previewYear.value ?? record.peak.year
  const year = Math.max(props.extent[0], Math.min(props.extent[1], current + offset))
  hover.value = { year, type: record.type }
}
</script>

<template>
  <div class="genre-type-records" data-visual>
    <div class="type-record-grid">
      <article v-for="record in activeRows" :key="record.type" class="type-record"
        :class="{ 'is-selected': selectedType === record.type, 'is-disabled': !visibleTypes.includes(record.type) }"
        :style="{ '--record-color': record.color }">
        <h3><button type="button" :aria-pressed="selectedType === record.type" :disabled="!visibleTypes.includes(record.type)"
          @click="choose(record)">{{ EDGE_LABELS[record.type] }}<span>{{ formatCount(record.total) }} 条</span></button></h3>
        <svg viewBox="-124 -124 248 248" class="type-disc"
          role="button" :tabindex="visibleTypes.includes(record.type) ? 0 : -1"
          :data-type="record.type" :data-total="record.total"
          :aria-label="EDGE_LABELS[record.type] + '，当前 ' + record.current.year + ' 年 ' + record.current.value + ' 条，方向键切换年份，回车查看证据'"
          @pointermove="preview($event, record)" @pointerleave="hover = null"
          @click="pick($event, record)" @keydown.enter.prevent="choose(record)" @keydown.space.prevent="choose(record)"
          @keydown.right="move($event, record, 1)" @keydown.left="move($event, record, -1)" @blur="hover = null">
          <defs>
            <linearGradient :id="'score-lacquer-' + record.type" x1="0" y1="1" x2=".9" y2="0">
              <stop stop-color="#0c1726" /><stop offset=".27" :stop-color="record.color" stop-opacity=".20" />
              <stop offset=".43" stop-color="#172a3d" /><stop offset=".63" stop-color="#0c1626" />
              <stop offset=".84" :stop-color="record.color" stop-opacity=".29" /><stop offset="1" stop-color="#102035" />
            </linearGradient>
          </defs>
          <circle r="112" :fill="'url(#score-lacquer-' + record.type + ')'" aria-hidden="true" />
          <g class="type-grooves" aria-hidden="true">
            <circle v-for="r in [24,37,43,49,55,61,67,73,79,85,91,97,103,109]" :key="'groove-' + r" :r="r" class="type-etch" />
            <circle v-for="tick in ticks" :key="tick.year" :r="tick.radius" />
            <circle r="112" />
          </g>
          <g class="type-year-arcs">
            <path v-for="row in record.rows" :key="row.year" :d="row.path" class="type-year-arc" :data-year="row.year" :data-count="row.value"
              :stroke-dasharray="row.dash" :stroke-width="ringStep * .78"
              :class="{ 'is-current': row.year === previewYear }" />
          </g>
          <g class="type-stylus" aria-hidden="true">
            <circle v-if="previewYear != null" :r="record.current.radius" />
            <path class="type-arm" :d="'M105 85L98 68L' + (.866 * record.current.radius) + ' ' + (.5 * record.current.radius)" />
            <circle cx="105" cy="85" r="4.3" class="type-pivot" />
            <circle :cx=".866 * record.current.radius" :cy=".5 * record.current.radius" r="2.6" class="type-needle" />
          </g>
          <g class="type-labels" aria-hidden="true">
            <text v-for="tick in ticks.filter((_, i) => i % 2 === 0)" :key="tick.year" :x="-tick.radius * .56" :y="tick.radius * .84">{{ tick.year }}</text>
          </g>
          <g class="type-center" aria-hidden="true">
            <circle r="22" /><circle r="3" />
            <text y="-8">{{ extent[0] }}</text><text y="15">{{ extent[1] }}</text>
          </g>
        </svg>
        <button class="type-readout" type="button" :disabled="!visibleTypes.includes(record.type)" @click="choose(record, record.current.year)">
          <span>{{ previewYear == null ? '峰值 ' : '' }}{{ record.current.year }}</span>
          <strong>{{ record.current.value }}<small> 条</small></strong>
          <span class="type-readout-arrow" aria-hidden="true">↗</span>
        </button>
      </article>
    </div>
    <div class="type-scale">
      <span>圆环由内到外对应 {{ extent.join('—') }} 年，圆弧角度对应当年引用次数，五张图共用尺度。</span>
      <span>悬停对照年份 · 点选打开证据</span>
    </div>
  </div>
</template>

<style scoped>
.genre-type-records { color:var(--score-ink);min-width:0; }
.type-record-grid { display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:clamp(12px,2.2vw,32px); }
.type-record { min-width:0;transition:opacity 220ms ease; }
.type-record.is-disabled { opacity:.34;pointer-events:none; }
.type-record h3 { margin:0 0 8px; }
.type-record h3 button { width:100%;display:flex;justify-content:space-between;align-items:baseline;gap:4px;background:none;border:0;border-top:2px solid var(--record-color);padding:13px 0 0;font:500 clamp(18px,1.9vw,26px) var(--atlas-display);color:var(--record-color);cursor:pointer; }
.type-record h3 span { font:11px system-ui,sans-serif;white-space:nowrap;color:var(--score-soft); }
.type-disc { display:block;width:100%;overflow:visible;cursor:crosshair;outline:none; }
.type-grooves { fill:none;stroke:var(--score-rule);stroke-width:.45; }
.type-year-arc { fill:none;stroke:var(--record-color);stroke-opacity:.9;transition:stroke 180ms ease; }
.type-year-arc.is-current { stroke:var(--score-gold);stroke-opacity:1; }
.type-labels text { font:8px Georgia,serif;fill:var(--score-soft);paint-order:stroke;stroke:var(--score-panel);stroke-width:3; }
.type-center { pointer-events:none; }
.type-center circle:first-child { fill:var(--score-panel);stroke:var(--record-color);stroke-opacity:.4;stroke-width:.6; }
.type-center circle+circle { fill:var(--score-panel);stroke:var(--record-color);stroke-width:.7; }
.type-center text { text-anchor:middle;font:8px Georgia,serif;fill:var(--score-soft); }
.type-stylus { stroke:var(--score-gold);fill:none;stroke-width:.65;pointer-events:none; }
.type-stylus circle:first-child { transition:r 130ms ease-out; }
.type-stylus .type-needle { fill:var(--score-gold); }
.type-readout { width:100%;display:flex;align-items:baseline;gap:9px;border:0;border-bottom:1px solid var(--score-rule);background:none;color:var(--score-soft);padding:6px 0 12px;text-align:left;cursor:pointer;font-size:12px; }
.type-readout strong { font:500 27px var(--atlas-display);color:var(--record-color); }
.type-readout strong small { font:11px system-ui,sans-serif; }
.type-readout-arrow { margin-left:auto;transition:transform 200ms; }
.type-readout:hover .type-readout-arrow { transform:translate(2px,-2px); }
.type-record.is-selected h3 button { color:var(--score-gold); }
.type-disc:focus-visible { outline:2px solid var(--score-blue);outline-offset:1px;border-radius:50%; }
.type-scale { display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:18px;font-size:12px;color:var(--score-soft);line-height:1.7; }
@media(max-width:1050px) { .type-record-grid { grid-template-columns:repeat(3,minmax(0,1fr));gap:22px; } }
@media(max-width:600px) { .type-record-grid { grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 15px; } .type-record h3 span { font-size:10px; } .type-readout strong { font-size:23px; } }
@media(prefers-reduced-motion:reduce) { .type-record,.type-year-arc,.type-stylus circle:first-child,.type-readout-arrow { transition:none; } }
</style>
