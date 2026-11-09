<script setup>
import { computed } from 'vue'
import { curveCatmullRom, curveStepAfter, line, lineRadial } from 'd3'
import { revolvingWave, wavePhase } from '../lib/ambientMotion'
import AmbientTrace from './AmbientTrace.vue'

const props = defineProps({
  artist: { type: Object, required: true },
  dimensions: { type: Array, required: true },
  years: { type: Array, required: true },
  yearlyMax: { type: Number, required: true },
  cumulativeMax: { type: Number, required: true },
})
const center = 188
const recordWave = computed(() => revolvingWave(center, center, 155, {
  amplitude: 13, seconds: 5.15, delay: -(Math.max(1, props.artist.rank ?? 1) - 1) * .86,
}))
const full = Math.PI * 2
const score = computed(() => Number.isFinite(props.artist.score) ? props.artist.score.toFixed(2) : '—')
const byYear = computed(() => new Map((props.artist.timeline ?? []).map(row => [row.year, row])))
const samples = computed(() => props.years.map((year, index, all) => ({
  year,
  angle: .21 + (full - .42) * index / Math.max(1, all.length - 1),
  works: byYear.value.get(year)?.works,
  cumulative: byYear.value.get(year)?.cumulative_works,
})))
function polar(angle, radius) {
  return { x: center + radius * Math.sin(angle), y: center - radius * Math.cos(angle) }
}
function bead(x, y) {
  return 'M' + x.toFixed(1) + ' ' + y.toFixed(1) + 'h.01'
}
const sectors = computed(() => props.dimensions.map((dimension, index, all) => {
  const width = full / all.length
  const angle = (index + .5) * width
  const value = props.artist.strength_percentiles?.[dimension.key]
  const count = Math.round(Math.max(0, Math.min(100, value ?? 0)))
  const filled = []
  const vacant = []
  for (let position = 0; position < 100; position += 1) {
    const row = Math.floor(position / 10)
    const column = position % 10
    const sample = polar(index * width + width * (.12 + .76 * (column + .5) / 10), 50 + row * 6.2)
    const points = position < count ? filled : vacant
    points.push(bead(sample.x, sample.y))
  }
  return {
    ...dimension, value, filled: filled.join(''), vacant: vacant.join(''),
    labelPos: polar(angle, 118), wavePhase: wavePhase(angle - Math.PI / 2),
  }
}))
const grooves = computed(() => Array.from({ length: 12 }, (_, index) => {
  const path = lineRadial().defined(row => Number.isFinite(row.works)).angle(row => row.angle)
    .radius(row => 128 + index * 1.85 + 14 * row.works / props.yearlyMax)
    .curve(curveCatmullRom.alpha(.5))(samples.value)
  return { index, path }
}))
const ticks = computed(() => samples.value.map(row => ({
  ...row,
  inner: polar(row.angle, 160),
  outer: polar(row.angle, 166 + 4 * (row.works ?? 0) / props.yearlyMax),
  label: polar(row.angle, 178),
})))
const career = computed(() => {
  const values = samples.value.filter(row => Number.isFinite(row.cumulative))
  const x = year => 27 + (year - (props.years[0] ?? year)) * 300
    / Math.max(1, (props.years.at(-1) ?? year) - (props.years[0] ?? year))
  const y = count => 45 - 32 * count / props.cumulativeMax
  const path = line().defined(row => Number.isFinite(row.cumulative))
    .x(row => x(row.year)).y(row => y(row.cumulative)).curve(curveStepAfter)(samples.value)
  return {
    path,
    end: values.length ? { x: x(values.at(-1).year), y: y(values.at(-1).cumulative) } : null,
    count: values.at(-1)?.cumulative,
  }
})
</script>

<template>
  <span class="record-plate">
    <svg viewBox="0 0 376 376" class="record-plate-print" :style="recordWave.style" role="img"
      :aria-label="artist.name + '，综合分 ' + score + '，六维百分位与年度作品量唱片'">
      <g class="plate-rules atlas-wave-body" aria-hidden="true">
        <circle v-for="r in [45, 73, 105, 124, 157]" :key="r" :cx="center" :cy="center" :r="r" />
      </g>
      <g v-for="sector in sectors" :key="sector.key" class="plate-sectors atlas-orbit-swell"
        :style="{ '--atlas-wave-phase': sector.wavePhase, '--atlas-wave-reach': 1.062 }">
        <title>{{ sector.label }} · {{ Number.isFinite(sector.value) ? sector.value.toFixed(1) + ' 百分位' : '百分位未知' }}</title>
        <path class="plate-empty-marks" :d="sector.vacant" />
        <path class="plate-value-marks" :d="sector.filled" :stroke="sector.color" />
      </g>
      <text v-for="sector in sectors" :key="'label-' + sector.key" class="plate-dimension"
        :x="sector.labelPos.x" :y="sector.labelPos.y" text-anchor="middle" dominant-baseline="central">
        {{ sector.label }}
      </text>
      <g class="atlas-wave-body" aria-hidden="true">
        <g :transform="`translate(${center} ${center})`" class="plate-grooves">
          <path v-for="groove in grooves" :key="groove.index" :d="groove.path" :class="{ 'plate-edge': groove.index === 11 }" />
        </g>
      </g>
      <AmbientTrace :orbit="recordWave" />
      <g v-for="(tick, index) in ticks" :key="tick.year" class="plate-year">
        <title>{{ tick.year }} 年 · {{ tick.works == null ? '暂无活动记录' : tick.works + ' 部作品' }}</title>
        <line :x1="tick.inner.x" :y1="tick.inner.y" :x2="tick.outer.x" :y2="tick.outer.y"
          :class="{ 'plate-year-active': tick.works > 0 }" />
        <text v-if="index % 2 === 0 || index === ticks.length - 1" :x="tick.label.x" :y="tick.label.y"
          text-anchor="middle" dominant-baseline="central">{{ tick.year }}</text>
      </g>
      <text x="188" y="191" text-anchor="middle" class="plate-score">{{ score }}</text>
      <text x="188" y="212" text-anchor="middle" class="plate-score-unit">综合分</text>
    </svg>
    <span class="plate-career">
      <span>累计作品 <strong>{{ career.count ?? '—' }}</strong></span>
      <svg viewBox="0 0 354 67" role="img" :aria-label="artist.name + ' 累计作品轨迹，共用刻度'">
        <line x1="27" x2="327" y1="45" y2="45" />
        <line x1="27" x2="327" y1="13" y2="13" />
        <text x="3" y="16">{{ cumulativeMax }}</text>
        <text x="3" y="47">0</text>
        <path :d="career.path" />
        <circle v-if="career.end" :cx="career.end.x" :cy="career.end.y" r="2.8" />
        <text x="27" y="61">{{ years[0] }}</text>
        <text x="327" y="61" text-anchor="end">{{ years.at(-1) }}</text>
      </svg>
    </span>
  </span>
</template>

<style scoped>
.record-plate { display: block; min-width: 0; }
.record-plate-print {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
  --atlas-rotor-ink: var(--record-ink);
}
.plate-rules { fill: none; stroke: #c8d2d8; stroke-width: .65; }
.plate-rules circle:nth-child(even) { stroke-dasharray: 1 3; }
.plate-sectors path { fill: none; stroke-linecap: round; }
.plate-empty-marks { stroke: #c9d5da; stroke-width: 1.2; opacity: .69; }
.plate-value-marks { stroke-width: 2.35; }
.plate-dimension { fill: #415d6e; font: 11px system-ui, sans-serif; }
.plate-grooves { fill: none; stroke: var(--record-ink); stroke-width: .78; }
.plate-grooves path { opacity: .58; }
.plate-grooves .plate-edge { opacity: .94; stroke-width: 1.65; }
.plate-year line { stroke: #9eb2bc; stroke-width: .75; }
.plate-year line.plate-year-active { stroke: var(--record-ink); stroke-width: 1.45; }
.plate-year text { fill: #586c75; font: 11px Georgia, serif; }
.plate-score { fill: #1d384b; font: 500 33px/1 var(--atlas-display); font-variant-numeric: tabular-nums; }
.plate-score-unit { fill: #4a6372; font: 11px system-ui, sans-serif; }
.plate-career { display: block; margin: 6px 5px 0; }
.plate-career > span { display: flex; justify-content: space-between; color: #526675; font-size: 12px; }
.plate-career strong { color: var(--atlas-ink); font-variant-numeric: tabular-nums; }
.plate-career svg { display: block; width: 100%; height: auto; }
.plate-career line { stroke: #d7e1e5; stroke-width: 1; }
.plate-career text { fill: #526675; font: 11px Georgia, serif; }
.plate-career path { fill: none; stroke: var(--record-ink); stroke-width: 1.6; }
.plate-career circle { fill: var(--record-ink); }
</style>
