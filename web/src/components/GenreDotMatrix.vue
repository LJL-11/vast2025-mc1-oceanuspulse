<script setup>
import { computed, ref } from 'vue'
import { formatCount } from '../lib/palette'
import { scoreGenreColor as genreColor } from '../lib/genreScorePalette'
const props = defineProps({
  genres: { type: Array, required: true },
  genreColors: { type: Object, required: true },
  flows: { type: Array, required: true },
  selectedPair: { type: Object, default: null },
})
const emit = defineEmits(['select-flow'])
const hovered = ref(null)
const step = 28
const left = 146
const top = 117
const width = computed(() => left + props.genres.length * step + 45)
const height = computed(() => top + props.genres.length * step + 31)
const matrix = computed(() => {
  const counts = new Map()
  for (const row of props.flows) {
    const key = JSON.stringify([row.source, row.target])
    counts.set(key, (counts.get(key) ?? 0) + row.value)
  }
  const rows = props.genres.map((source, y) => ({
    source, y: top + y * step, color: props.genreColors[source] ?? genreColor(y),
    cells: props.genres.map((target, x) => ({
      source, target, x: left + x * step, y: top + y * step,
      count: counts.get(JSON.stringify([source, target])) ?? 0,
    })),
  }))
  const max = Math.max(1, ...rows.flatMap(row => row.cells.map(cell => cell.count)))
  return rows.map(row => ({
    ...row,
    total: row.cells.reduce((sum, cell) => sum + cell.count, 0),
    cells: row.cells.map(cell => ({ ...cell, radius: 10.8 * Math.sqrt(cell.count / max) })),
  }))
})
const active = computed(() => hovered.value ?? props.selectedPair)
const activeCell = computed(() => matrix.value.flatMap(row => row.cells).find(cell =>
  cell.source === active.value?.source && cell.target === active.value?.target))
function pick(cell) { if (cell.count) emit('select-flow', cell) }
function move(event, cell, offset) {
  event.preventDefault()
  const all = [...event.currentTarget.ownerSVGElement.querySelectorAll('.matrix-cell[data-count]:not([data-count="0"])')]
  const current = all.indexOf(event.currentTarget)
  all[Math.max(0, Math.min(all.length - 1, current + offset))]?.focus()
}
</script>

<template>
  <div class="genre-dot-matrix" data-visual>
    <div class="matrix-description"><span>来源 ↓</span><span>受影响流派 →</span><span>圆面积 ∝ 引用次数</span></div>
    <p class="matrix-scroll-hint">左右滑动，查看完整流向矩阵 →</p>
    <div class="matrix-viewport" tabindex="0" aria-label="流向矩阵，可横向滚动">
      <svg class="matrix-plate" :viewBox="'0 0 ' + width + ' ' + height" role="group" aria-label="流派影响流向矩阵">
        <g v-if="activeCell" class="matrix-coordinates" aria-hidden="true" pointer-events="none">
          <path :d="'M' + (left - 14) + ',' + activeCell.y + 'H' + activeCell.x + 'V' + (top - 16)" />
          <circle :cx="activeCell.x" :cy="activeCell.y" :r="activeCell.radius + 6" />
        </g>
        <g class="matrix-grid" aria-hidden="true">
          <line v-for="(genre, index) in genres" :key="genre" :x1="left + index * step" :x2="left + index * step" :y1="top - 16" :y2="height - 16" />
          <line v-for="row in matrix" :key="row.source" x1="8" :x2="width - 10" :y1="row.y" :y2="row.y" />
        </g>
        <g v-for="(target, index) in genres" :key="target" class="matrix-col"
          :class="{ 'is-active': active?.target === target }">
          <text :transform="'translate(' + (left + index * step) + ',' + (top - 25) + ') rotate(-48)'">{{ target }}</text>
        </g>
        <g v-for="row in matrix" :key="row.source" class="matrix-row" :class="{ 'is-active': active?.source === row.source }">
          <text class="matrix-row-label" :x="left - 19" :y="row.y + 4" text-anchor="end">{{ row.source }}</text>
          <text class="matrix-total" :x="width - 5" :y="row.y + 4" text-anchor="end">{{ formatCount(row.total) }}</text>
          <g v-for="cell in row.cells" :key="cell.target" class="matrix-cell"
            :class="{ 'is-active': active?.source === cell.source && active?.target === cell.target }"
            :data-source="cell.source" :data-target="cell.target" :data-count="cell.count"
            :role="cell.count ? 'button' : undefined" :tabindex="cell.count ? 0 : undefined"
            :aria-label="cell.source + ' → ' + cell.target + '，' + cell.count + ' 条引用'"
            :aria-pressed="cell.count ? selectedPair?.source === cell.source && selectedPair?.target === cell.target : undefined"
            @pointerenter="hovered = cell" @pointerleave="hovered = null" @focus="hovered = cell" @blur="hovered = null"
            @click="pick(cell)" @keydown.enter.prevent="pick(cell)" @keydown.space.prevent="pick(cell)"
            @keydown.right="move($event, cell, 1)" @keydown.left="move($event, cell, -1)">
            <rect :x="cell.x - step / 2" :y="cell.y - step / 2" :width="step" :height="step" class="matrix-hit" />
            <path v-if="cell.source === cell.target" :d="'M' + (cell.x - 3) + ',' + (cell.y + 3) + 'l6,-6'" class="matrix-self" />
            <circle v-else :cx="cell.x" :cy="cell.y" :r="cell.count ? cell.radius : .8"
              :fill="cell.count ? row.color : '#c1ccce'" class="matrix-dot" />
            <circle v-if="cell.count" :cx="cell.x" :cy="cell.y" :r="cell.radius + 2.6" class="matrix-ring" :stroke="row.color" />
          </g>
        </g>
      </svg>
    </div>
    <div class="matrix-readout" role="status">
      <template v-if="activeCell"><strong>{{ activeCell.source }} → {{ activeCell.target }}</strong><span>{{ formatCount(activeCell.count) }} 条引用</span></template>
      <template v-else><span>点选圆点，核对流向的原始引用</span></template>
    </div>
  </div>
</template>

<style scoped>
.genre-dot-matrix { min-width:0;color:var(--score-ink); }
.matrix-description { display:flex;align-items:center;gap:15px;min-height:42px;font-size:11px;color:var(--score-soft); }
.matrix-description span:last-child { margin-left:auto; }
.matrix-scroll-hint { display:none;margin:0 0 8px;font-size:11px;color:var(--score-soft); }
.matrix-viewport { overflow-x:auto;scrollbar-width:thin;scrollbar-color:var(--score-scroll) var(--score-panel); }
.matrix-plate { display:block;width:100%;min-width:490px; }
.matrix-grid { stroke:var(--score-rule);stroke-width:.55; }
.matrix-col text { font:10.5px Georgia,serif;fill:var(--score-soft); }
.matrix-row-label { font:11px Georgia,serif;fill:var(--score-ink);paint-order:stroke;stroke:var(--score-panel);stroke-width:5; }
.matrix-total { fill:var(--score-muted);font:10px system-ui,sans-serif;paint-order:stroke;stroke:var(--score-panel);stroke-width:5; }
.matrix-cell { outline:none; }
.matrix-cell[data-count]:not([data-count='0']) { cursor:pointer; }
.matrix-hit { fill:transparent;transition:fill 180ms ease; }
.matrix-dot { transition:r 260ms ease,opacity 180ms ease;fill-opacity:.83; }
.matrix-ring { opacity:.15;fill:none;stroke-width:.75;transition:opacity 180ms; }
.matrix-cell:is(.is-active,:focus-visible) .matrix-hit { fill:var(--score-focus-fill); }
.matrix-cell:is(.is-active,:focus-visible) .matrix-ring { opacity:1;stroke-width:1.3; }
.matrix-self { fill:none;stroke:var(--score-rule);stroke-width:1; }
.matrix-row.is-active .matrix-row-label,.matrix-col.is-active text { fill:var(--score-gold);font-weight:700; }
.matrix-readout { min-height:58px;display:flex;align-content:center;align-items:baseline;flex-wrap:wrap;gap:4px 12px;padding:10px 0;border-block:1px solid var(--score-rule);font-size:12px;color:var(--score-soft); }
.matrix-readout strong { color:var(--score-ink);font-weight:600; }
@media(max-width:600px) { .matrix-scroll-hint { display:block; } }
@media(prefers-reduced-motion:reduce) { .matrix-hit,.matrix-dot,.matrix-ring { transition:none; } }
</style>
