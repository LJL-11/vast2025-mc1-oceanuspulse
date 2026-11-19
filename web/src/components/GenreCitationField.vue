<script setup>
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { line, range } from 'd3'
import { observeChartSize } from '../lib/atlas'
import { EDGE_LABELS, FLOW_TYPES, formatCount } from '../lib/palette'
import { citationFrame, citationKey, citationOrbit, citationPosition, layoutCitations } from '../lib/genreCitationLayout'
import { drawCitationSky, mountCitationMotion } from '../lib/genreCitationSky'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  flows: { type: Array, required: true },
  visibleFlows: { type: Array, required: true },
  extent: { type: Array, required: true },
  genre: { type: String, required: true },
  selectedYear: { type: Number, default: null },
  selectedPair: { type: Object, default: null },
})
const emit = defineEmits(['select-year', 'select-citation', 'inspect'])
const DIRECTIONS = { out: { label: '影响流出', color: '#a8d4ff' }, in: { label: '灵感流入', color: '#f3cb91' } }
const NOTE_COLORS = {
  InStyleOf: '#a1cdf1',
  CoverOf: '#f1b783',
  DirectlySamples: '#8fdbc9',
  InterpolatesFrom: '#bac0ee',
  LyricalReferenceTo: '#e1d4a5',
}
const plate = ref(null)
const sky = ref(null)
const movingSky = ref(null)
let motion
const plateWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const compact = computed(() => plateWidth.value <= 600)
const placed = shallowRef(null)
const hovered = shallowRef(null)
const keyboardPoint = shallowRef(null)
const frame = computed(() => citationFrame(compact.value))
const viewBox = computed(() => '0 0 ' + frame.value.width + ' ' + frame.value.height)
const directionOf = flow => flow.source === props.genre ? 'out' : 'in'
const layoutExtent = computed(() => props.flows.length
  ? [Math.min(...props.flows.map(flow => flow.year)), props.extent[1]] : props.extent)

const visibleKeys = computed(() => new Set(props.visibleFlows.map(citationKey)))
const points = computed(() => (placed.value ?? []).flatMap((position, index) => {
  const flow = props.flows[index]
  if (!flow) return []
  const key = citationKey(flow)
  return visibleKeys.value.has(key) ? [{ ...position, key, flow, weight: flow.value, direction: directionOf(flow) }] : []
}))
const byKey = computed(() => new Map(points.value.map(point => [point.key, point])))
const waveBands = computed(() => {
  const [first, last] = layoutExtent.value
  const groups = new Map()
  for (const point of points.value) {
    const slot = Math.round(12 * (point.flow.year - first) / Math.max(1, last - first))
    const key = point.direction + slot
    if (!groups.has(key)) groups.set(key, { key, direction: point.direction, progress: slot / 12, notes: [] })
    groups.get(key).notes.push(point)
  }
  return [...groups.values()]
})
const picked = computed(() => props.selectedPair?.type
  ? byKey.value.get(citationKey({ ...props.selectedPair, year: props.selectedYear })) : null)
const active = computed(() => hovered.value ?? keyboardPoint.value ?? picked.value)
const readingYear = computed(() => active.value?.flow.year ?? props.selectedYear)
const orderedNotes = computed(() => [...points.value].sort((a, b) => a.flow.year - b.flow.year || a.x - b.x))

const yearCounts = computed(() => {
  const counts = new Map()
  for (const flow of props.visibleFlows) counts.set(flow.year, (counts.get(flow.year) ?? 0) + flow.value)
  return counts
})
const years = computed(() => range(props.extent[0], props.extent[1] + 1))
const firstYear = computed(() => years.value.find(year => yearCounts.value.has(year)))
const tally = computed(() => props.visibleFlows.reduce((total, flow) => total + flow.value, 0))

function strongestYear(counts) {
  let peak = null
  for (const [year, count] of counts) {
    if (!peak || count > peak.count || (count === peak.count && year < peak.year)) peak = { year, count }
  }
  return peak
}

const peak = computed(() => strongestYear(yearCounts.value))
const trackStats = computed(() => Object.entries(DIRECTIONS).map(([direction, style]) => {
  const counts = new Map()
  for (const flow of props.visibleFlows) {
    if (directionOf(flow) === direction) counts.set(flow.year, (counts.get(flow.year) ?? 0) + flow.value)
  }
  return { direction, ...style, peak: strongestYear(counts), total: [...counts.values()].reduce((a, b) => a + b, 0) }
}))
const typeTotals = computed(() => FLOW_TYPES.map(type => ({
  type, total: props.visibleFlows.reduce((sum, flow) => flow.type === type ? sum + flow.value : sum, 0),
})))
const beacons = computed(() => trackStats.value.flatMap(track => {
  const brightest = points.value.filter(point => point.direction === track.direction && point.flow.year === track.peak?.year)
    .reduce((best, point) => !best || point.radius > best.radius ? point : best, null)
  return brightest ? [brightest] : []
}))
const beaconKeys = computed(() => new Set(beacons.value.map(point => point.key)))

function traceOrbit(direction, offset) {
  return line().x(point => point.x).y(point => point.y)(
    range(121).map(step => citationOrbit(step / 120, direction, offset, compact.value)),
  )
}

const orbits = computed(() => Object.entries(DIRECTIONS).map(([direction, style]) => {
  const [start, end] = layoutExtent.value
  const ticks = range(start, end + 1).map(year => {
    const major = year === start || year === end || (year % 10 === 0 && year - start >= 5 && end - year >= 5)
    const from = citationPosition(year, layoutExtent.value, direction, 39, compact.value)
    const to = citationPosition(year, layoutExtent.value, direction, major ? 49 : 43, compact.value)
    const labelX = Math.max(32, Math.min(frame.value.width - 32, to.x))
    return { year, from, to, major, labelX }
  })
  return {
    direction, ...style, ticks,
    grooves: [-32, -24, -18, -12, -6, 0, 6, 12, 18, 24, 32].map(offset => traceOrbit(direction, offset)),
    path: traceOrbit(direction, 0),
  }
}))

const markers = computed(() => {
  const year = readingYear.value
  if (year == null || year < layoutExtent.value[0] || year > layoutExtent.value[1]) return []
  return Object.keys(DIRECTIONS).map(direction => ({
    direction,
    start: citationPosition(year, layoutExtent.value, direction, -34, compact.value),
    end: citationPosition(year, layoutExtent.value, direction, 52, compact.value),
  }))
})

const periods = computed(() => {
  const [start, end] = props.extent
  const max = Math.max(1, ...yearCounts.value.values())
  return [[start, 1999], [2000, 2009], [2010, 2019], [2020, end]]
    .map(([a, b]) => [Math.max(a, start), Math.min(b, end)])
    .filter(([a, b]) => a <= b)
    .map(([begin, last]) => {
      const counts = new Map(range(begin, last + 1).map(year => [year, yearCounts.value.get(year) ?? 0]))
      const step = 234 / counts.size
      const bars = [...counts].map(([year, count], i) => ({
        year, x: i * step + 1, width: Math.max(1, step - 1.65), height: 30 * count / max,
      }))
      return { begin, last, total: [...counts.values()].reduce((sum, count) => sum + count, 0), peak: strongestYear(counts), bars }
    })
})

function findPoint(event) {
  const reach = event.pointerType === 'touch' ? 14 : 9
  const key = event.target.getAttribute('data-citation') ?? motion?.nearest(event, reach)
  return byKey.value.get(key) ?? null
}
function preview(event) {
  if (event.pointerType === 'touch') return
  hovered.value = findPoint(event)
  motion?.aim(hovered.value?.key)
}
function clearPreview() {
  hovered.value = null
  motion?.aim(keyboardPoint.value?.key)
}
function holdPoint(event) {
  if (event.pointerType === 'touch') motion?.aim(findPoint(event)?.key)
  else preview(event)
}
function pick(event) {
  const point = findPoint(event)
  if (!point) return
  keyboardPoint.value = null
  if (event.pointerType === 'touch') hovered.value = null
  emit('select-citation', point.flow)
}
function moveNote(offset) {
  hovered.value = null
  const index = orderedNotes.value.findIndex(point => point.key === (keyboardPoint.value ?? picked.value)?.key)
  const next = Math.max(0, Math.min(orderedNotes.value.length - 1, index + offset))
  keyboardPoint.value = orderedNotes.value[next] ?? null
  motion?.aim(keyboardPoint.value?.key)
}
function pickNote() {
  if (keyboardPoint.value) emit('select-citation', keyboardPoint.value.flow)
}
function pickYear(event) {
  emit('select-year', event.target.value === '' ? null : Number(event.target.value))
}

function syncNoteBodies() {
  if (!motion || !plate.value) return
  const elements = new Map([...plate.value.querySelectorAll('[data-star-body]')].map(element => [element.dataset.starBody, element]))
  const containers = new Map([...plate.value.querySelectorAll('[data-wave-band]')].map(el => [el.dataset.waveBand, el]))
  const bands = []
  const entries = []
  for (const group of waveBands.value) {
    const { direction, progress } = group
    const p = citationOrbit(progress, direction, 0, compact.value)
    const n = citationOrbit(progress, direction, 1, compact.value)
    const band = { direction, progress, nx: n.x - p.x, ny: n.y - p.y, x: 0, y: 0, element: containers.get(group.key) }
    if (!band.element) continue
    bands.push(band)
    for (const point of group.notes) entries.push({
      key: point.key, x: point.x, y: point.y, radius: point.radius, waveBand: band,
      element: elements.get(point.key), radialLimit: compact.value ? 28 : 23, tangentLimit: 9,
    })
  }
  motion.setBodies(entries, bands)
}

watch(() => [props.visibleFlows, props.genre, compact.value], () => {
  keyboardPoint.value = null
  clearPreview()
})
watch(plate, (element, _, onCleanup) => {
  if (!element) return
  onCleanup(observeChartSize(element, width => { plateWidth.value = width }))
})
watch([sky, frame, plateWidth, points, beacons], ([canvas, bounds, width, notes, highlights]) => {
  if (canvas) drawCitationSky(canvas, bounds, width, notes, highlights, compact.value)
}, { flush: 'post' })
watch([movingSky, plate], ([canvas, element], _, onCleanup) => {
  if (!canvas || !element) return
  motion = mountCitationMotion(canvas, element)
  const stop = watch([frame, plateWidth, compact], ([bounds, width, useCompact]) => {
    motion.resize(bounds, width, useCompact)
  }, { immediate: true, flush: 'post' })
  syncNoteBodies()
  onCleanup(() => {
    stop()
    motion.dispose()
    motion = undefined
  })
}, { flush: 'post' })
watch(points, syncNoteBodies, { flush: 'post' })

let entrancePending = true
let pageActive = true
let entranceAnimations = []
const reducedEntrance = window.matchMedia('(prefers-reduced-motion: reduce)')

function finishEntrance() {
  entrancePending = false
  for (const animation of entranceAnimations) animation.cancel()
  entranceAnimations = []
}

function playEntrance() {
  if (!entrancePending || !pageActive || !plate.value || placed.value == null) return
  entrancePending = false
  if (reducedEntrance.matches || !points.value.length) return
  const element = plate.value
  const animations = []
  entranceAnimations = animations
  const reveal = (target, keyframes, duration, delay = 0) => {
    const animation = target.animate(keyframes, {
      duration, delay, easing: 'cubic-bezier(.22,.75,.2,1)', fill: 'both',
    })
    animation.id = 'citation-entrance'
    animations.push(animation)
  }
  const expansion = [
    { transform: 'scale(.22) rotate(-8deg)', opacity: 0 },
    { transform: 'scale(1) rotate(0deg)', opacity: 1 },
  ]
  reveal(sky.value, expansion, 1400)
  reveal(movingSky.value, expansion, 1280, 140)
  reveal(element.querySelector('.citation-engraving'), expansion, 1320, 80)

  // Whole year bands unfold together, outside the transforms used for picking and the idle wave.
  const arrivals = new Map([...element.querySelectorAll('[data-arrival-band]')]
    .map(group => [group.dataset.arrivalBand, group]))
  for (const band of waveBands.value) {
    const center = band.notes.reduce((sum, note) => ({ x: sum.x + note.x, y: sum.y + note.y }), { x: 0, y: 0 })
    const dx = (frame.value.width / 2 - center.x / band.notes.length) * .5
    const dy = (frame.value.height / 2 - center.y / band.notes.length) * .5
    const turn = band.direction === 'out' ? -8 : 8
    reveal(arrivals.get(band.key), [
      { transform: 'translate(' + dx + 'px,' + dy + 'px) rotate(' + turn + 'deg) scale(.55)', opacity: 0 },
      { offset: .55, opacity: .04 },
      { offset: .82, opacity: .92 },
      { transform: 'translate(0px,0px) rotate(0deg) scale(1)', opacity: 1 },
    ], 1180, 80 + band.progress * 130 + (band.direction === 'in' ? 80 : 0))
  }
  for (const dates of element.querySelectorAll('.citation-dates')) {
    reveal(dates, [{ opacity: 0 }, { opacity: 1 }], 400, 680)
  }
  for (const label of element.querySelectorAll('.citation-track-label')) {
    reveal(label, [{ opacity: 0, transform: 'translateY(5px)' }, { opacity: 1, transform: 'translateY(0)' }], 440, 700)
  }
  Promise.all(animations.map(animation => animation.finished)).then(() => {
    if (entranceAnimations === animations) finishEntrance()
  }, () => {})
}

function updateEntrancePreference() {
  if (reducedEntrance.matches) finishEntrance()
}
reducedEntrance.addEventListener('change', updateEntrancePreference)
watch([placed, plate], () => {
  if (entranceAnimations.length) finishEntrance()
  playEntrance()
}, { flush: 'post' })
onActivated(() => {
  finishEntrance()
  pageActive = true
  entrancePending = true
  playEntrance()
})
onDeactivated(() => {
  pageActive = false
  finishEntrance()
})
onBeforeUnmount(() => {
  finishEntrance()
  reducedEntrance.removeEventListener('change', updateEntrancePreference)
})

onMounted(() => {
  watch([() => props.flows, layoutExtent, compact], ([flows, bounds, compactLayout], _, onCleanup) => {
    placed.value = null
    const samples = flows.map(({ year, value, type, source }) => ({
      year, value, type, direction: source === props.genre ? 'out' : 'in',
    }))
    const extent = [...bounds]
    const fallback = () => { placed.value = layoutCitations(samples, extent, compactLayout) }
    try {
      const worker = new Worker(new URL('../lib/genreCitationLayout.worker.js', import.meta.url), { type: 'module' })
      onCleanup(() => worker.terminate())
      worker.onmessage = event => {
        placed.value = event.data
        worker.terminate()
      }
      worker.onerror = event => {
        event.preventDefault()
        worker.terminate()
        fallback()
      }
      worker.postMessage({ samples, extent, compact: compactLayout })
    } catch {
      fallback()
    }
  }, { immediate: true })
})
</script>

<template>
  <figure class="citation-field" aria-labelledby="genre-plate-title">
    <div ref="plate" class="citation-plate" data-visual :aria-busy="placed == null"
      @pointermove.capture="finishEntrance" @pointerdown.capture="finishEntrance" @focusin="finishEntrance"
      @pointermove="motion?.move($event)" @pointerleave="motion?.leave()">
      <canvas ref="sky" class="citation-sky" aria-hidden="true" />
      <canvas ref="movingSky" class="citation-sky citation-sky-motion" aria-hidden="true" />
      <div class="citation-intro"><slot name="intro" /></div>
      <svg class="citation-art" :class="{ 'is-compact': compact }" :viewBox="viewBox" role="group"
        :tabindex="points.length ? 0 : -1" aria-label="引用星轨。方向键浏览符头，回车查看原始引用。"
        @pointermove="preview" @pointerdown="holdPoint" @pointerup="$event.pointerType === 'touch' && motion?.aim(null)"
        @pointercancel="clearPreview" @pointerleave="clearPreview" @click="pick"
        @focus="$event.currentTarget.matches(':focus-visible') && moveNote(1)" @blur="keyboardPoint = null; motion?.aim(hovered?.key)"
        @keydown.left.prevent="moveNote(-1)" @keydown.right.prevent="moveNote(1)"
        @keydown.enter.prevent="pickNote" @keydown.space.prevent="pickNote">
        <g aria-hidden="true">
          <g class="citation-engraving">
          <g v-for="orbit in orbits" :key="orbit.direction" class="citation-orbit"
            v-memo="[orbit, active != null && active.direction !== orbit.direction]"
            :class="{ 'is-muted': active && active.direction !== orbit.direction }"
            :style="{ '--orbit-color': orbit.color }" :data-orbit="orbit.direction">
            <path v-for="(groove, index) in orbit.grooves" :key="index"
              class="citation-groove" :class="{ 'is-center': index === 5 }" :d="groove" />
            <g class="citation-dates">
            <g v-for="tick in orbit.ticks" :key="tick.year" class="citation-tick" :class="{ 'is-major': tick.major }">
              <line :x1="tick.from.x" :y1="tick.from.y" :x2="tick.to.x" :y2="tick.to.y" />
              <text v-if="tick.major" :x="tick.labelX"
                :y="tick.to.y + (orbit.direction === 'in' ? (compact && tick.year === layoutExtent[1] ? 36 : 17) : -9)"
                text-anchor="middle">{{ tick.year }}</text>
            </g>
            </g>
          </g>
          <g v-for="marker in markers" :key="marker.direction" class="citation-playhead" :stroke="DIRECTIONS[marker.direction].color">
            <line :x1="marker.start.x" :y1="marker.start.y" :x2="marker.end.x" :y2="marker.end.y" />
            <circle :cx="marker.end.x" :cy="marker.end.y" r="2.7" />
          </g>
          <path v-if="active" :key="active.direction" class="citation-phrase"
            :d="orbits.find(orbit => orbit.direction === active.direction).path" :stroke="DIRECTIONS[active.direction].color" pathLength="1000" />
          </g>
          <g v-if="placed" class="citation-cloud" :class="{ 'has-year': selectedYear != null }">
            <g v-for="band in waveBands" :key="band.key" class="citation-arrival-band" :data-arrival-band="band.key">
            <g :data-wave-band="band.key">
            <g v-for="point in band.notes" :key="point.key" :data-star-body="point.key"
              v-memo="[point, beaconKeys, selectedYear, active?.key === point.key]">
              <g v-if="beaconKeys.has(point.key)" class="citation-beacon"
                :class="{ 'is-dimmed': selectedYear != null && selectedYear !== point.flow.year }"
                :transform="'translate(' + point.x + ',' + point.y + ')'" :stroke="DIRECTIONS[point.direction].color">
                <path d="M-30 0H30 M0 -30V30 M-11 -11L11 11 M11 -11L-11 11" />
                <circle :r="point.radius + 4" />
              </g>
              <g class="citation-note"
                :class="{ 'is-year': point.flow.year === selectedYear, 'is-picked': active?.key === point.key }"
                :style="{ '--note-color': NOTE_COLORS[point.flow.type] }">
                <path class="citation-stem" :d="point.direction === 'out'
                  ? 'M' + (point.x + point.radius * .76) + ',' + point.y + 'v-11'
                  : 'M' + (point.x - point.radius * .76) + ',' + point.y + 'v11'" />
                <ellipse class="citation-dot" :class="{ 'is-outgoing': point.direction === 'out' }"
                  :data-citation="point.key" :data-year="point.flow.year" :data-count="point.flow.value"
                  :data-type="point.flow.type" :data-direction="point.direction"
                  :cx="point.x" :cy="point.y" :rx="point.radius" :ry="point.radius * .72"
                  :transform="'rotate(-22,' + point.x + ',' + point.y + ')'" />
              </g>
              <g v-if="active?.key === point.key" class="citation-highlight"
                :transform="'translate(' + point.x + ',' + point.y + ')'" :stroke="NOTE_COLORS[point.flow.type]">
                <circle class="citation-halo" :r="point.radius + 4" />
              </g>
            </g>
            </g>
            </g>
          </g>
        </g>
      </svg>
      <div v-for="track in trackStats" :key="track.direction" class="citation-track-label"
        :class="'is-' + track.direction" :style="{ '--orbit-color': track.color }">
        <span>{{ track.label }}</span>
        <strong>{{ formatCount(track.total) }} <small>条引用</small></strong>
      </div>
    </div>

    <figcaption class="citation-caption">
      <div class="citation-toolbar">
        <div class="citation-control">
          <slot name="focus-control" />
          <label class="citation-year">查看年份
            <select :value="selectedYear ?? ''" class="op-select" @change="pickYear">
              <option value="">全部年份</option>
              <option v-for="year in years" :key="year" :value="year" :disabled="!yearCounts.has(year) && selectedYear !== year">{{ year }}</option>
            </select>
          </label>
        </div>
        <div class="citation-readout">
          <div role="status">
            <template v-if="active">
              <strong>{{ active.flow.source }} → {{ active.flow.target }}</strong>
              <span>{{ active.flow.year }} 年 · {{ EDGE_LABELS[active.flow.type] }} · {{ formatCount(active.flow.value) }} 条</span>
            </template>
            <template v-else-if="selectedYear != null">
              <strong>{{ selectedYear }} 年</strong>
              <span>{{ formatCount(yearCounts.get(selectedYear) ?? 0) }} 条跨流派引用</span>
            </template>
            <span v-else-if="tally">沿星轨查看年份，点选符头查证引用。</span>
            <span v-else>当前筛选下没有跨流派引用。</span>
          </div>
          <button v-if="selectedYear != null || selectedPair" class="citation-inspect" type="button" @click="emit('inspect')">
            查看原始证据 <AppIcon name="arrow" :size="15" />
          </button>
        </div>
      </div>

      <div class="citation-reading">
        <div class="citation-key">
          <span>由左向右读年份，彩色符头面积表示引用次数</span>
          <span><i class="citation-sample" aria-hidden="true" />实心流出</span>
          <span><i class="citation-sample is-in" aria-hidden="true" />空心流入</span>
        </div>
        <div class="citation-findings" v-if="peak">
          <button type="button" @click="emit('select-year', firstYear)">{{ firstYear }} 年最早记录</button>
          <button type="button" @click="emit('select-year', peak.year)">{{ peak.year }} 年双向峰值 · {{ formatCount(peak.count) }} 条 <AppIcon name="arrow" :size="13" /></button>
        </div>
      </div>
      <div class="citation-voice-key" aria-label="五类引用及其数量">
        <span v-for="voice in typeTotals" :key="voice.type" :data-voice="voice.type" :data-total="voice.total">
          <i :style="{ background: NOTE_COLORS[voice.type] }" aria-hidden="true" />{{ EDGE_LABELS[voice.type] }} <small>{{ formatCount(voice.total) }}</small>
        </span>
      </div>
    </figcaption>

    <div class="citation-eras" aria-label="四个时段的引用次数">
      <button v-for="period in periods" :key="period.begin" type="button" class="citation-era"
        :disabled="!period.total" :aria-pressed="period.peak.year === selectedYear"
        :aria-label="period.begin + ' 至 ' + period.last + ' 年共 ' + formatCount(period.total) + ' 条，查看峰值年份 ' + period.peak.year"
        @click="emit('select-year', period.peak.year)">
        <div><span>{{ period.begin }}—{{ period.last }}</span><strong>{{ formatCount(period.total) }}</strong></div>
        <svg viewBox="0 0 236 34" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0,32H236" />
          <rect v-for="bar in period.bars" :key="bar.year" :class="{ 'is-current': bar.year === selectedYear }"
            :x="bar.x" :y="32 - bar.height" :width="bar.width" :height="bar.height" />
        </svg>
      </button>
    </div>
  </figure>
</template>

<style scoped>
.citation-field {
  --sky-ink: #f4f7fb;
  --sky-muted: #aabbd0;
  --sky-deep: #070f1e;
  margin: 0;
  min-width: 0;
}

.citation-plate {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border-radius: clamp(13px, 1.65vw, 24px);
  background:
    radial-gradient(ellipse at 66% 13%, #182e4b 0%, transparent 56%),
    radial-gradient(ellipse at 62% 88%, #282132 0%, transparent 59%),
    linear-gradient(150deg, #07101e, #060911 62%, #0a1421);
  color: var(--sky-ink);
  box-shadow: inset 0 0 0 1px #a5c7ed28;
}

.citation-sky {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.citation-intro {
  position: absolute;
  z-index: 2;
  inset: 50% 0 auto;
  width: min(88%, 660px);
  margin-inline: auto;
  transform: translateY(-50%);
  text-align: center;
  pointer-events: none;
}

.citation-intro :deep(a) { pointer-events: auto; }

.citation-art {
  position: relative;
  display: block;
  width: 100%;
  height: auto;
  touch-action: pan-y;
}

.citation-art:focus-visible {
  outline: 1px solid #a8d4ff;
  outline-offset: -5px;
  border-radius: inherit;
}

.citation-engraving,
.citation-arrival-band {
  transform-box: view-box;
  transform-origin: 50% 50%;
}

.citation-orbit,
.citation-tick,
.citation-playhead,
.citation-stem,
.citation-beacon,
.citation-highlight,
.citation-phrase {
  pointer-events: none;
}

.citation-orbit {
  fill: none;
  stroke: var(--orbit-color);
  transition: opacity 180ms ease;
}

.citation-orbit.is-muted { opacity: .4; }

.citation-groove {
  stroke-width: .62;
  stroke-opacity: .10;
}

.citation-groove.is-center {
  stroke-width: .85;
  stroke-opacity: .34;
}

.citation-tick {
  stroke-width: .65;
  stroke-opacity: .34;
}

.citation-tick.is-major { stroke-opacity: .69; }

.citation-tick text {
  fill: #cad9ea;
  stroke: #09111d;
  stroke-width: 3;
  stroke-opacity: .8;
  paint-order: stroke;
  font: 500 13px/1 system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}

.citation-phrase {
  fill: none;
  stroke-width: 1.55;
  stroke-linecap: round;
  stroke-dasharray: 56 944;
  opacity: 0;
  animation: citation-travel 1.5s ease-out backwards;
}

@keyframes citation-travel {
  0% { stroke-dashoffset: 1056; opacity: 0; }
  15% { opacity: .88; }
  80% { opacity: .7; }
  100% { stroke-dashoffset: 0; opacity: 0; }
}

.citation-note { transition: opacity 180ms ease; }

.citation-dot {
  fill: var(--sky-deep);
  stroke: var(--note-color);
  stroke-width: 1.1;
  cursor: pointer;
}

.citation-dot.is-outgoing { fill: var(--note-color); }
.citation-stem { stroke: var(--note-color); stroke-width: .66; stroke-opacity: .47; }
.citation-cloud.has-year .citation-note { opacity: .24; }
.citation-cloud.has-year .citation-note:is(.is-year, .is-picked) { opacity: 1; }

.citation-playhead { fill: var(--sky-deep); stroke-width: 1.1; }
.citation-playhead line { stroke-dasharray: 3 4; }
.citation-beacon { fill: none; stroke-width: .75; opacity: .82; }
.citation-beacon.is-dimmed { opacity: .16; }
.citation-highlight { fill: none; }
.citation-halo { stroke-width: 1.6; }
.citation-track-label {
  position: absolute;
  display: grid;
  gap: 5px;
  min-width: 106px;
  color: var(--orbit-color);
  pointer-events: none;
}

.citation-track-label.is-out { top: 20px; left: clamp(18px, 3vw, 46px); }
.citation-track-label.is-in { bottom: 22px; right: clamp(18px, 3vw, 46px); text-align: right; }

.citation-track-label > span {
  font-size: 11px;
  letter-spacing: .12em;
}

.citation-track-label strong {
  font: 500 clamp(23px, 3vw, 43px)/1 var(--atlas-display);
  font-variant-numeric: lining-nums tabular-nums;
  color: var(--sky-ink);
}

.citation-track-label small { font: 11px/1.4 system-ui, sans-serif; color: var(--sky-muted); }

.citation-caption { padding-inline: clamp(0px, 1.6vw, 24px); }

.citation-toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 14px clamp(20px, 3vw, 45px);
  padding-block: 18px;
}

.citation-control,
.citation-year,
.citation-reading,
.citation-key,
.citation-findings,
.citation-readout,
.citation-inspect,
.citation-voice-key {
  display: flex;
  align-items: center;
}

.citation-control { gap: 12px 22px; flex-wrap: wrap; }
.citation-year { gap: 8px; color: #43647a; font-size: 13px; }
.citation-year select { min-height: 40px; }
.citation-readout { flex-wrap: wrap; justify-content: space-between; gap: 9px 16px; color: #536b80; font-size: 13px; }
.citation-readout strong { color: #193853; margin-right: 9px; font-weight: 650; }
.citation-readout span { display: inline-block; }
.citation-inspect {
  min-height: 40px;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #d2dfe9;
  border-radius: 6px;
  color: #164d75;
  background: #f3f7fb;
  cursor: pointer;
  font-size: 13px;
}
.citation-inspect:hover { background: #e7f0f8; }

.citation-reading {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 7px 18px;
  padding: 10px 0;
  border-top: 1px solid #d2dbe2;
  color: #4b6577;
  font-size: 12px;
}

.citation-key { flex-wrap: wrap; gap: 6px 16px; }
.citation-key span { display: inline-flex; align-items: center; gap: 6px; }
.citation-sample {
  width: 9px;
  height: 6px;
  border-radius: 50%;
  background: #426483;
  border: 1px solid #426483;
  transform: rotate(-22deg);
}
.citation-sample.is-in { background: transparent; }

.citation-findings { flex-wrap: wrap; gap: 4px 15px; }
.citation-findings button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 0;
  border: 0;
  border-bottom: 1px solid transparent;
  background: none;
  color: #285d82;
  font: inherit;
  cursor: pointer;
}
.citation-findings button:hover { border-color: currentColor; }

.citation-voice-key {
  flex-wrap: wrap;
  gap: 7px 18px;
  padding: 2px 0 13px;
  color: #496575;
  font-size: 11px;
}
.citation-voice-key span { display: inline-flex; align-items: center; gap: 6px; }
.citation-voice-key i { width: 10px; height: 6px; border: 1px solid #182d4a50; border-radius: 50%; }
.citation-voice-key small { color: #526f81; font-variant-numeric: tabular-nums; }

.citation-eras {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 13px clamp(0px, 1.6vw, 24px);
  border-block: 1px solid #d2dbe2;
}

.citation-era {
  min-width: 0;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 5px;
  text-align: left;
  background: transparent;
  color: #33556b;
  font: 12px system-ui, sans-serif;
  cursor: pointer;
}

.citation-era:is(:hover, :focus-visible, [aria-pressed='true']):not(:disabled) {
  border-color: #afc3d1;
  background: #edf4f9;
}

.citation-era:disabled { cursor: default; color: #6d818e; }
.citation-era div { display: flex; justify-content: space-between; gap: 5px; align-items: baseline; }
.citation-era strong { color: #1c3c55; font: 600 17px var(--atlas-display); }
.citation-era svg { display: block; width: 100%; height: 32px; }
.citation-era path { stroke: #a3b6c4; fill: none; }
.citation-era rect { fill: #90aabd; }
.citation-era rect.is-current { fill: #33688d; }

@media (max-width: 1120px) {
  .citation-art:not(.is-compact) .citation-tick text { font-size: 17px; }
}

@media (max-width: 800px) {
  .citation-toolbar { grid-template-columns: minmax(0, 1fr); }
}

@media (max-width: 630px) {
  .citation-caption { padding-inline: 4px; }
  .citation-tick text { font-size: 21px; }
  .citation-track-label.is-out { top: 15px; left: 16px; }
  .citation-track-label.is-in { bottom: 16px; right: 16px; }
  .citation-track-label > span { font-size: 10px; }
  .citation-track-label small { font-size: 10px; }
  .citation-toolbar { row-gap: 12px; }
  .citation-control { display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:12px; }
  .citation-control :deep(.genre-poster-focus), .citation-year { display:grid;gap:5px;min-width:0; }
  .citation-control :deep(select) { width:100%;max-width:100%; }
  .citation-eras { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 10px; }
  .citation-era svg { height: 25px; }
}

@media (prefers-reduced-motion: reduce) {
  .citation-phrase { animation: none; }
  .citation-orbit, .citation-note { transition: none; }
}
</style>
