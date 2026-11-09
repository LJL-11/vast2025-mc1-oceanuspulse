<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { observeChartSize } from '../lib/atlas'

const props = defineProps({
  works: { type: Array, required: true },
  collaborators: { type: Array, required: true },
  yearRange: { type: Array, required: true },
  focusId: { type: [String, Number], default: null },
  visibleTypes: { type: Array, required: true },
})
const emit = defineEmits(['work', 'collaborator', 'year'])
const frame = ref(null)
const width = ref(860)
const hovered = ref(null)
let stopMeasuring

onMounted(() => {
  stopMeasuring = observeChartSize(frame.value, value => { width.value = value })
})
onBeforeUnmount(() => stopMeasuring?.())

const compact = computed(() => width.value < 580)
const people = computed(() => props.collaborators.map((person, index) => ({
  ...person, side: index % 4 === 2 ? 1 : -1, lane: index % 4,
})).filter(person => props.visibleTypes.includes(person.type ?? 'Person')))
const score = computed(() => {
  const byYear = new Map()
  for (const work of props.works) {
    const year = work.node.release_year
    if (!byYear.has(year)) byYear.set(year, [])
    byYear.get(year).push(work)
  }
  if (!byYear.size) return { height: 160, works: [], ticks: [] }
  const step = compact.value ? 15 : 17
  const gutter = compact.value ? 10 : 14
  const first = Math.min(...byYear.keys())
  const last = Math.max(...byYear.keys())
  const marks = []
  const ticks = []
  let y = 40
  for (let year = first; year <= last; year += 1) {
    const works = (byYear.get(year) ?? []).sort((a, b) => a.id - b.id)
    ticks.push({ year, y })
    for (const work of works) {
      marks.push({ ...work, y })
      y += step
    }
    y += gutter + (works.length ? 0 : step)
  }
  const height = y + 29
  const xAt = y => width.value * ((compact.value ? .35 : .38) + .25 * y / height)
  return {
    height,
    works: marks.filter(work => props.visibleTypes.includes(work.node.type)).map(work => ({
      ...work, x: xAt(work.y), collaborators: people.value.filter(person => person.work_ids.includes(work.id)),
    })),
    ticks: ticks.map(tick => ({ ...tick, x: xAt(tick.y) })),
  }
})
const worksById = computed(() => new Map(score.value.works.map(work => [work.id, work])))
const activeId = computed(() => hovered.value ?? props.focusId)
const activeWork = computed(() => worksById.value.get(activeId.value))
const activePerson = computed(() => people.value.find(person => person.id === activeId.value))
const inWindow = year => year >= props.yearRange[0] && year <= props.yearRange[1]
const note = computed(() => {
  const marks = score.value.works
  if (!marks.length) return []
  const first = marks[0]
  const peak = marks.reduce((best, work) => work.collaborators.length > best.collaborators.length ? work : best)
  const last = marks.at(-1)
  const seen = new Set()
  return [
    { work: first, label: '最早显示的署名' },
    { work: peak, label: '入图合作者最多' },
    { work: last, label: '最近显示的署名' },
  ].filter(({ work }) => {
    if (seen.has(work.id)) return false
    seen.add(work.id)
    return true
  })
})
function sweep(from, to, person) {
  const span = to.y - from.y
  const height = Math.min(width.value * .255, 18 + span * .27 + person.lane * 7)
  const taper = Math.min(10, 2 + Math.sqrt(span) * .24)
  const outer = (height + taper) * person.side
  const inner = (height - taper) * person.side
  const y1 = from.y + span * .13
  const y2 = to.y - span * .13
  const start = `M${from.x},${from.y}`
  const curve = offset => `C${from.x + offset},${y1} ${to.x + offset},${y2} ${to.x},${to.y}`
  return start + curve(outer) + `C${to.x + inner},${y2} ${from.x + inner},${y1} ${from.x},${from.y}Z`
}
const routes = computed(() => people.value.flatMap(person => {
  const marks = person.work_ids.map(id => worksById.value.get(id)).filter(Boolean).sort((a, b) => a.y - b.y)
  return marks.slice(1).map((work, index) => ({
    id: person.id + ':' + work.id, person, start: marks[index], end: work,
    path: sweep(marks[index], work, person),
  }))
}))
const spine = computed(() => {
  const first = score.value.works[0]
  const last = score.value.works.at(-1)
  return first && last ? `M${first.x},${first.y}L${last.x},${last.y}` : ''
})
function routeState(route) {
  const selected = route.person.id === activeId.value || route.start.id === activeId.value || route.end.id === activeId.value
  const within = inWindow(route.start.node.release_year) || inWindow(route.end.node.release_year)
  return { 'is-selected': selected, 'is-muted': !selected && (!!activeWork.value || !!activePerson.value || !within) }
}
function workName(work) { return work.node.display_name || work.node.name }
</script>

<template>
  <div ref="frame" class="credit-score" data-visual>
    <div class="credit-score-caption">
      <span v-if="activeWork"><strong>{{ workName(activeWork) }}</strong> · {{ activeWork.node.release_year }} 年</span>
      <span v-else-if="activePerson"><strong>{{ activePerson.name }}</strong> · {{ activePerson.shared_work_count }} 部共同作品</span>
      <span v-else>每个圆点是一部作品，彩色弧线串起同一位合作者参与的作品。</span>
      <span>{{ score.works.length }} 部署名作品</span>
    </div>
    <svg v-if="score.works.length" :viewBox="`0 0 ${width} ${score.height}`" role="group"
      aria-label="Sailor Shift 署名时间长卷，年份自上而下">
      <g class="score-years">
        <g v-for="tick in score.ticks" :key="tick.year" role="button" tabindex="0"
          :aria-label="'筛选 ' + tick.year + ' 年'" :aria-pressed="inWindow(tick.year)"
          @click="emit('year', tick.year)" @keydown.enter.prevent="emit('year', tick.year)"
          @keydown.space.prevent="emit('year', tick.year)">
          <rect x="3" :y="tick.y - 11" :width="compact ? 39 : 61" height="22" fill="transparent" />
          <line :x1="compact ? 47 : 68" :y1="tick.y" :x2="tick.x - 13" :y2="tick.y" />
          <text :x="compact ? 8 : 15" :y="tick.y" dominant-baseline="central">{{ tick.year }}</text>
        </g>
      </g>
      <g>
        <path class="score-spine" :d="spine" aria-hidden="true" />
        <g class="score-routes">
          <path v-for="route in routes" :key="route.id" :d="route.path" :fill="route.person.color"
            :stroke="route.person.color" :class="routeState(route)"
            @pointerenter="hovered = route.person.id" @pointerleave="hovered = null"
            @click="emit('collaborator', route.person)">
            <title>{{ route.person.name }} · {{ workName(route.start) }} → {{ workName(route.end) }}</title>
          </path>
        </g>
        <g v-for="work in score.works" :key="work.id" class="atlas-credit-work"
          :class="{ 'is-selected': work.id === activeId || work.collaborators.some(person => person.id === activeId),
            'is-muted': !inWindow(work.node.release_year) && work.id !== activeId }"
          role="button" tabindex="0" :aria-pressed="work.id === focusId"
          :aria-label="workName(work) + '，' + work.node.release_year + ' 年'"
          @pointerenter="hovered = work.id" @pointerleave="hovered = null" @focus="hovered = work.id" @blur="hovered = null"
          @click="emit('work', work.node)" @keydown.enter.prevent="emit('work', work.node)" @keydown.space.prevent="emit('work', work.node)">
          <title>{{ workName(work) }} · {{ work.node.release_year }}</title>
          <circle :cx="work.x" :cy="work.y" r="8" fill="transparent" />
          <circle class="score-work" :cx="work.x" :cy="work.y" :r="work.node.type === 'Album' ? 5.6 : 4.1"
            :fill="work.node.type === 'Album' ? '#aa5639' : '#235c78'" />
          <circle v-for="(person, index) in work.collaborators" :key="person.id"
            :cx="work.x + 12 + index * 6" :cy="work.y" r="2.25" :fill="person.color" />
        </g>
      </g>
      <g v-if="!compact" class="score-notes" aria-hidden="true">
        <g v-for="item in note" :key="item.work.id">
          <line :x1="item.work.x + 18 + item.work.collaborators.length * 6" :y1="item.work.y"
            :x2="width * .76 - 8" :y2="item.work.y" />
          <text :x="width * .76" :y="item.work.y - 3">{{ item.label }}</text>
          <foreignObject :x="width * .76" :y="item.work.y + 3" :width="width * .22" height="47">
            <div class="score-note-work">{{ workName(item.work) }}</div>
          </foreignObject>
        </g>
      </g>
    </svg>
    <p v-else class="score-empty">当前筛选下没有可绘制的署名作品。</p>
  </div>
</template>

<style scoped>
.credit-score { border-block: 1px solid #d9d1c2; background: #fcfaf4; }
.credit-score svg { display: block; width: 100%; height: auto; }
.credit-score-caption {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 6px 14px;
  padding: 9px 12px;
  background: #f9f5eb;
  border-bottom: 1px solid #e5ded0;
  color: #445861;
  font-size: 13px;
}
.credit-score-caption strong { color: #203b48; font-weight: 650; }
.credit-score-caption > span:last-child { white-space: nowrap; }
.score-years g { cursor: pointer; outline: none; }
.score-years text { fill: #455b64; font: 14px Georgia, serif; }
.score-years line { stroke: #c9c3b8; stroke-dasharray: 2 4; }
.score-years [aria-pressed="false"] { opacity: .5; }
.score-years g:is(:hover, :focus-visible) text { fill: #a04734; font-weight: 700; }
.score-spine { fill: none; stroke: #9eaea7; stroke-width: 1; }
.score-routes path { opacity: .39; stroke-width: .65; cursor: pointer; transition: opacity 180ms var(--atlas-ease); }
.score-routes path.is-selected { opacity: .86; }
.score-routes path.is-muted { opacity: .065; }
.atlas-credit-work { cursor: pointer; outline: none; transition: opacity 170ms var(--atlas-ease); }
.atlas-credit-work.is-muted { opacity: .22; }
.score-work { stroke: #fffcf5; stroke-width: 1.5; transition: stroke 170ms var(--atlas-ease); }
.atlas-credit-work:is(.is-selected, :focus-visible) .score-work { stroke: #253b46; stroke-width: 2; }
.score-notes { pointer-events: none; }
.score-notes line { stroke: #b56c57; stroke-width: .9; }
.score-notes text { fill: #9a4938; font-size: 12px; }
.score-note-work { font: 16px/1.2 var(--atlas-display); color: #2c4048; overflow-wrap: anywhere; }
.score-empty { padding: 24px 14px; margin: 0; }
@media (max-width: 620px) {
  .credit-score-caption { flex-direction: column; padding: 7px 8px; font-size: 12px; }
  .score-years text { font-size: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .score-routes path, .atlas-credit-work, .score-work { transition: none; }
}
</style>
