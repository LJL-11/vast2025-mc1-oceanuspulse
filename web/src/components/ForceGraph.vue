<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { select, zoom, zoomIdentity } from 'd3'
import { EGO_CENTER_RADIUS, egoCurve, egoTrail, layOutEgo } from '../lib/egoLayout'
import { INFLUENCE_EDGE_TYPES, NODE_COLORS, NODE_LABELS } from '../lib/palette'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  visibleTypes: { type: Array, default: () => [] },
  visibleEdgeTypes: { type: Array, default: () => [] },
  yearRange: { type: Array, default: () => [1975, 2040] },
  anchorId: { type: [Number, String], required: true },
  focusId: { type: [Number, String], default: null },
  pathIds: { type: Array, default: () => [] },
  pathNodes: { type: Array, default: () => [] },
  height: { type: String, default: 'clamp(480px, 43vw, 610px)' },
})
const emit = defineEmits(['select'])
const svgEl = ref(null)
const transform = ref(zoomIdentity)
const hoverId = ref(null)
const keyboardId = ref(null)
const layer = ref('all')
let zoomBehavior

const viewBox = '-350 -321 700 642'
const layout = computed(() => layOutEgo(props.nodes, props.links, props.anchorId))
const root = computed(() => layout.value.marks.get(props.anchorId))
const allMarks = computed(() => [...layout.value.marks.values()])
const shownMarks = computed(() => allMarks.value.filter(mark =>
  props.visibleTypes.includes(mark.node.type) && (layer.value !== 'near' || mark.depth < 2),
))
const shownIds = computed(() => new Set(shownMarks.value.map(mark => mark.id)))
const toggles = computed(() => [
  { key: 'all', name: '全图', count: layout.value.marks.size },
  { key: 'near', name: '一跳', count: layout.value.counts[0] },
  { key: 'far', name: '突出二跳', count: layout.value.counts[1] },
])
const sectorCount = computed(() => {
  const counts = new Map()
  for (const mark of shownMarks.value) if (mark.depth) counts.set(mark.node.type, (counts.get(mark.node.type) ?? 0) + 1)
  return counts
})
const baseSegments = computed(() => {
  const pairs = new Map()
  for (const link of props.links) {
    if (!layout.value.marks.has(link.source) || !layout.value.marks.has(link.target)) continue
    const key = [link.source, link.target].sort().join('|')
    if (!pairs.has(key)) pairs.set(key, [])
    pairs.get(key).push(link)
  }
  return [...pairs.values()].flatMap(links => links.map((link, index) => {
    // The exported influence edge runs from borrower to source.
    const influence = INFLUENCE_EDGE_TYPES.includes(link.type)
    const source = layout.value.marks.get(influence ? link.target : link.source)
    const target = layout.value.marks.get(influence ? link.source : link.target)
    const lane = (index - (links.length - 1) / 2) * (source.id > target.id ? -1 : 1)
    return {
      id: link.id, source: source.id, target: target.id, influence,
      depth: Math.max(source.depth, target.depth), lateral: source.depth === 2 && target.depth === 2, type: link.type,
      d: egoCurve(source, target, influence, lane),
    }
  }))
})
const segments = computed(() => baseSegments.value.filter(link =>
  shownIds.value.has(link.source) && shownIds.value.has(link.target) && props.visibleEdgeTypes.includes(link.type),
))
const selected = computed(() => props.focusId !== props.anchorId ? layout.value.marks.get(props.focusId) : null)
const evidence = computed(() => props.pathIds.length > 0)
const route = computed(() => {
  if (evidence.value) return { nodeIds: props.pathNodes, edgeIds: props.pathIds }
  return egoTrail(segments.value, props.anchorId, selected.value?.id)
})
const routeIds = computed(() => new Set(route.value?.edgeIds ?? []))
const routeNodes = computed(() => new Set(route.value?.nodeIds ?? []))
const connectionFocus = computed(() => hoverId.value ?? selected.value?.id ?? null)
const neighborhood = computed(() => {
  if (connectionFocus.value == null) return null
  const ids = new Set([connectionFocus.value])
  for (const edge of segments.value) {
    if (edge.source === connectionFocus.value) ids.add(edge.target)
    if (edge.target === connectionFocus.value) ids.add(edge.source)
  }
  return ids
})
const pathContext = computed(() => evidence.value || neighborhood.value !== null)
const landmarks = computed(() => {
  const byType = new Map()
  for (const mark of shownMarks.value) {
    if (mark.depth !== 1) continue
    if (!byType.has(mark.node.type) || byType.get(mark.node.type).degree < mark.degree) byType.set(mark.node.type, mark)
  }
  return new Set([...byType.values()].sort((a, b) => b.degree - a.degree).slice(0, 3).map(mark => mark.id))
})
const entryId = computed(() => [keyboardId.value, props.focusId, props.anchorId]
  .find(id => shownIds.value.has(id)) ?? shownMarks.value[0]?.id)
const orderedEdges = computed(() => segments.value.map(edge => {
  const onPath = routeIds.value.has(edge.id)
  const adjacent = edge.source === connectionFocus.value || edge.target === connectionFocus.value
  const emphasis = onPath ? 2 : adjacent && (!evidence.value || hoverId.value != null) ? 1 : 0
  const outside = outOfWindow(layout.value.marks.get(edge.source)) || outOfWindow(layout.value.marks.get(edge.target))
  let alpha = edge.influence ? .52 : .32
  if (edge.lateral) alpha *= .62
  if (!edge.influence && edge.depth === 1) alpha = .45
  if (outside || (layer.value === 'far' && edge.depth === 1)) alpha *= .33
  if (pathContext.value && !emphasis) alpha *= .22
  return { ...edge, emphasis, alpha: emphasis ? 1 : alpha }
}).sort((a, b) => a.emphasis - b.emphasis))

function name(mark) { return mark?.node.display_name || mark?.node.name || '' }
function color(type) { return NODE_COLORS[type] || '#718396' }
function outOfWindow(mark) {
  const year = mark.node.release_year ?? mark.node.written_year ?? mark.node.chart_year
  return year != null && (year < props.yearRange[0] || year > props.yearRange[1])
}
function nodeAlpha(mark) {
  if (routeNodes.value.has(mark.id) || mark.id === connectionFocus.value) return 1
  if (pathContext.value && !neighborhood.value?.has(mark.id)) return .26
  if (outOfWindow(mark)) return .30
  return layer.value === 'far' && mark.depth === 1 ? .57 : .93
}
function selectMark(mark) {
  if (mark && shownIds.value.has(mark.id)) emit('select', mark.node)
}
function moveFocus(mark, step) {
  const sequence = shownMarks.value
  const index = sequence.findIndex(item => item.id === mark.id)
  const next = sequence[(index + step + sequence.length) % sequence.length]
  if (next) svgEl.value?.querySelector(`[data-node-id="${CSS.escape(String(next.id))}"]`)?.focus()
}
function setLayer(mode) {
  hoverId.value = null
  layer.value = mode
}
function zoomBy(factor) {
  if (svgEl.value && zoomBehavior) select(svgEl.value).call(zoomBehavior.scaleBy, factor)
}
function reset() {
  if (svgEl.value && zoomBehavior) select(svgEl.value).call(zoomBehavior.transform, zoomIdentity)
}
watch([() => props.focusId, () => props.pathIds], () => {
  if (evidence.value || (selected.value?.depth === 2 && layer.value === 'near')) layer.value = 'all'
})
onMounted(() => {
  const svg = select(svgEl.value)
  zoomBehavior = zoom().scaleExtent([.85, 5]).on('zoom', event => { transform.value = event.transform })
  svg.call(zoomBehavior).on('dblclick.zoom', null)
})
onBeforeUnmount(() => {
  if (svgEl.value) select(svgEl.value).on('.zoom', null)
})
</script>

<template>
  <div class="ego-map">
    <div class="ego-map-toolbar">
      <div class="atlas-segments ego-layer-tabs" role="group" aria-label="按跳数查看">
        <button v-for="tab in toggles" :key="tab.key" type="button" :aria-pressed="layer === tab.key" @click="setLayer(tab.key)">
          {{ tab.name }} <span>{{ tab.count }}</span>
        </button>
      </div>
      <span class="ego-map-count">当前显示 {{ shownMarks.length }} 个实体</span>
    </div>
    <div class="op-graph-wrap ego-map-stage" :style="{ height }" data-visual>
      <svg ref="svgEl" :viewBox="viewBox" role="group" aria-label="Sailor Shift 两跳关系图，内环一跳，外环二跳">
        <defs>
          <marker id="op-arrow-influence" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 1L7 4L0 7Z" fill="#ae6647" />
          </marker>
          <marker id="op-arrow-ego-selected" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5.2" markerHeight="5.2" orient="auto">
            <path d="M0 1L7 4L0 7Z" fill="#a54a31" />
          </marker>
        </defs>
        <rect x="-350" y="-321" width="700" height="642" fill="transparent" @click="emit('select', null)" />
        <g :transform="transform">
          <g class="ego-rings" aria-hidden="true">
            <circle v-for="r in [115, 160, 175, 267]" :key="r" :r="r" class="ego-guide" />
            <circle r="225" class="ego-guide ego-guide-fine" />
            <g v-for="sector in layout.sectors" :key="sector.type" :style="{ color: color(sector.type) }"
              :class="{ 'is-quiet': !sectorCount.get(sector.type) }">
              <path :d="sector.inner" class="ego-ring-inner" :class="{ 'is-muted': layer === 'far' }" />
              <path :d="sector.outer" class="ego-ring-outer" :class="{ 'is-muted': layer === 'near' }" />
              <path :d="sector.trim" class="ego-sector-trim" />
              <text :x="sector.label.x" :y="sector.label.y" class="ego-sector-label" text-anchor="middle" dominant-baseline="central">
                {{ NODE_LABELS[sector.type] ?? sector.type }}
              </text>
            </g>
          </g>
          <path v-for="edge in orderedEdges" :key="edge.id" :d="edge.d" fill="none" class="atlas-ego-edge"
            :class="{ 'is-influence': edge.influence, 'is-neighbor': edge.emphasis === 1, 'is-evidence': edge.emphasis === 2 }"
            :data-edge-id="edge.id" :data-source="edge.source" :data-target="edge.target"
            :opacity="edge.alpha" :stroke-width="edge.emphasis === 2 ? 2.65 : edge.emphasis ? 1.65 : edge.influence ? 1.15 : .84"
            :marker-end="edge.influence ? (edge.emphasis ? 'url(#op-arrow-ego-selected)' : 'url(#op-arrow-influence)') : null" />
          <g v-if="root && !shownIds.has(root.id)" class="ego-center-guide" aria-hidden="true">
            <circle :r="EGO_CENTER_RADIUS" />
            <text y="3" text-anchor="middle">{{ name(root) }}</text>
          </g>
          <g v-for="mark in shownMarks" :key="mark.id" class="atlas-ego-node"
            :class="{ 'ego-root-node': !mark.depth, 'is-chosen': selected?.id === mark.id, 'is-path': routeNodes.has(mark.id) }"
            :data-node-id="mark.id" :data-hop="mark.depth" :transform="`translate(${mark.x} ${mark.y})`"
            role="button" :tabindex="entryId === mark.id ? 0 : -1" :aria-pressed="focusId === mark.id"
            :aria-label="name(mark) + (mark.depth ? '，距中心 ' + mark.depth + ' 跳' : '，中心实体')"
            @pointerenter="hoverId = mark.id" @pointerleave="hoverId = null"
            @focus="hoverId = mark.id; keyboardId = mark.id" @blur="hoverId = null"
            @click.stop="selectMark(mark)" @keydown.enter.prevent="selectMark(mark)" @keydown.space.prevent="selectMark(mark)"
            @keydown.left.prevent="moveFocus(mark, -1)" @keydown.right.prevent="moveFocus(mark, 1)"
            @keydown.up.prevent="moveFocus(mark, -1)" @keydown.down.prevent="moveFocus(mark, 1)">
            <title>{{ name(mark) }} · {{ mark.depth ? mark.depth + ' 跳' : '中心实体' }}</title>
            <template v-if="!mark.depth">
              <circle class="ego-center-disc" :r="EGO_CENTER_RADIUS" />
              <circle class="ego-center-rule" :r="EGO_CENTER_RADIUS - 6" />
              <text class="ego-center-name" text-anchor="middle" y="1">{{ name(mark) }}</text>
              <text class="ego-center-note" text-anchor="middle" y="21">中心实体</text>
            </template>
            <template v-else>
              <circle r="7.2" fill="transparent" />
              <circle v-if="routeNodes.has(mark.id) || connectionFocus === mark.id" class="ego-node-halo" :r="mark.size + 4" />
              <g class="ego-glyph" :opacity="nodeAlpha(mark)" :style="{ color: color(mark.node.type) }">
                <rect v-if="mark.node.type === 'Album' || mark.node.type === 'RecordLabel'"
                  :x="-mark.size" :y="-mark.size" :width="mark.size * 2" :height="mark.size * 2" rx="1.25"
                  :class="{ 'ego-label-glyph': mark.node.type === 'RecordLabel' }" />
                <path v-else-if="mark.node.type === 'MusicalGroup'"
                  :d="`M0 ${-mark.size - .9}L${mark.size + .9} 0L0 ${mark.size + .9}L${-mark.size - .9} 0Z`" />
                <circle v-else :r="mark.size" />
              </g>
              <text v-if="connectionFocus === mark.id || routeNodes.has(mark.id) || (!pathContext && landmarks.has(mark.id))"
                class="atlas-ego-label" :class="{ 'ego-landmark-label': !pathContext }"
                :x="mark.x > 0 ? -10 : 10" :y="mark.y < -220 ? 19 : -9" :text-anchor="mark.x > 0 ? 'end' : 'start'">
                {{ name(mark).length > 27 ? name(mark).slice(0, 25) + '…' : name(mark) }}
              </text>
            </template>
          </g>
        </g>
      </svg>
      <div v-if="!shownMarks.length" class="ego-empty">当前筛选范围内没有实体</div>
      <div class="op-graph-tools ego-zoom" role="group" aria-label="图谱缩放">
        <button type="button" class="op-btn" aria-label="缩小图谱" :disabled="transform.k <= .85" @click="zoomBy(1 / 1.28)">−</button>
        <button type="button" class="op-btn" aria-label="放大图谱" :disabled="transform.k >= 5" @click="zoomBy(1.28)">+</button>
        <button type="button" class="op-btn" @click="reset">重置视图</button>
      </div>
      <span v-if="hoverId != null" class="ego-hover">{{ name(layout.marks.get(hoverId)) }}</span>
    </div>
    <div class="ego-route" aria-live="polite">
      <template v-if="route">
        <strong>{{ evidence ? '影响路径证据' : '与中心相连的关系链' }}</strong>
        <ol v-if="route.nodeIds.length">
          <li v-for="(id, index) in route.nodeIds" :key="index">
            <AppIcon v-if="index" :name="evidence ? 'arrow' : 'minus'" :size="13" />
            <button type="button" :disabled="!shownIds.has(id)" @click="selectMark(layout.marks.get(id))">
              {{ name(layout.marks.get(id)) || '#' + id }}
            </button>
          </li>
        </ol>
        <div class="ego-route-ids"><code v-for="id in route.edgeIds" :key="id">{{ id }}</code></div>
      </template>
      <template v-else-if="selected">
        <strong>{{ name(selected) }}</strong>
        <span>距中心 {{ selected.depth }} 跳 · 当前筛选下路线未完整显示</span>
      </template>
      <span v-else>内环为一跳，外环为二跳。点选节点可追查与中心相连的关系。</span>
    </div>
  </div>
</template>

<style scoped>
.ego-map { --ego-ink: #1c4158; }
.ego-map-toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 5px 12px;
  margin-block: 8px 10px;
}
.ego-layer-tabs button span { margin-left: 3px; font-variant-numeric: tabular-nums; opacity: .8; }
.ego-map-count { color: #526b78; font-size: 12px; }
.ego-map-stage.op-graph-wrap {
  border-color: #d7d8ce;
  border-radius: 6px;
  background: #fafaf6;
}
.ego-map-stage svg { touch-action: none; }
.ego-rings { pointer-events: none; }
.ego-guide { fill: none; stroke: #b1c3c8; stroke-width: .72; stroke-dasharray: 2 4; }
.ego-guide-fine { stroke-width: .56; opacity: .55; }
.ego-ring-inner { fill: currentColor; fill-opacity: .075; }
.ego-ring-outer { fill: currentColor; fill-opacity: .07; }
.ego-sector-trim { fill: currentColor; fill-opacity: .84; }
.ego-rings .is-muted, .ego-rings .is-quiet { opacity: .34; }
.ego-sector-label { fill: #355467; font-size: 15px; font-weight: 620; letter-spacing: .09em; }
.atlas-ego-edge { stroke: #a1b6c1; transition: opacity 150ms ease; pointer-events: none; }
.atlas-ego-edge.is-influence { stroke: #bd7958; }
.atlas-ego-edge.is-neighbor { stroke: #3b7898; }
.atlas-ego-edge.is-evidence { stroke: #246d95; }
.atlas-ego-edge.is-influence:is(.is-neighbor, .is-evidence) { stroke: #a54a31; }
.atlas-ego-node { cursor: pointer; }
.ego-glyph { fill: currentColor; stroke: #fffef8; stroke-width: .9; }
.ego-glyph .ego-label-glyph { fill: #fffef8; stroke: currentColor; stroke-width: 1.35; }
.ego-node-halo { fill: #fffdf6; stroke: #306a89; stroke-width: 1.25; }
.atlas-ego-node.is-path .ego-node-halo { stroke: #b66043; }
.atlas-ego-node:focus-visible { outline: none; }
.atlas-ego-node:focus-visible .ego-glyph { stroke: #143e62; stroke-width: 2px; }
.atlas-ego-node:focus-visible .ego-center-disc { stroke-width: 2.6; }
.ego-center-disc, .ego-center-guide circle { fill: #f5f5ed; stroke: #7799aa; stroke-width: 1; }
.ego-center-rule { fill: none; stroke: #b4c7cb; stroke-width: .8; stroke-dasharray: 2 3; }
.ego-center-name, .ego-center-guide text { fill: var(--ego-ink); font: 19px Georgia, serif; pointer-events: none; }
.ego-center-note { fill: #516875; font-size: 11px; letter-spacing: .13em; pointer-events: none; }
.atlas-ego-label {
  pointer-events: none;
  font-size: 12px;
  font-weight: 620;
  fill: var(--ego-ink);
  paint-order: stroke;
  stroke: #fafaf6;
  stroke-width: 3.5px;
  stroke-linejoin: round;
}
.ego-zoom { right: 10px; top: 10px; align-items: center; }
.ego-zoom .op-btn { min-height: 30px; padding: 4px 8px; background: #fffefa; }
.ego-zoom .op-btn[aria-label] { min-width: 30px; }
.ego-hover, .ego-empty { position: absolute; z-index: 1; pointer-events: none; }
.ego-hover {
  inset: auto auto 8px 10px;
  max-width: calc(100% - 20px);
  padding: 4px 9px;
  background: #fffefa;
  border: 1px solid #d8e2e4;
  border-radius: 4px;
  color: var(--ego-ink);
  font-size: 12px;
}
.ego-empty { inset: 50% 12px auto; text-align: center; color: var(--ego-ink); }
.ego-route {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px 9px;
  min-height: 39px;
  padding-top: 9px;
  color: #526b78;
  font-size: 13px;
}
.ego-route strong { color: var(--ego-ink); }
.ego-route ol { display: flex; flex-wrap: wrap; gap: 5px 7px; padding: 0; margin: 0; list-style: none; }
.ego-route li { display: flex; align-items: center; gap: 7px; min-width: 0; }
.ego-route button {
  background: #edf3f4;
  color: var(--ego-ink);
  border: 1px solid #d7e4e9;
  border-radius: 4px;
  padding: 2px 6px;
  font: inherit;
  text-align: left;
  overflow-wrap: anywhere;
  cursor: pointer;
}
.ego-route button:disabled { opacity: .6; cursor: default; }
.ego-route-ids { display: flex; flex-wrap: wrap; gap: 4px 8px; }
.ego-route-ids code { padding: 1px 4px; background: #eef3f5; color: #345565; border-radius: 3px; font-size: 11px; }
@media (max-width: 620px) {
  .ego-sector-label { font-size: 21px; }
  .ego-center-name, .ego-center-guide text { font-size: 22px; }
  .ego-center-note { font-size: 15px; }
  .atlas-ego-label { font-size: 17px; }
  .ego-landmark-label { display: none; }
  .ego-zoom { top: 6px; right: 6px; gap: 4px; }
  .ego-zoom .op-btn { min-height: 27px; padding: 2px 5px; font-size: 11px; }
  .ego-zoom .op-btn[aria-label] { min-width: 26px; }
}
@media (prefers-reduced-motion: reduce) {
  .atlas-ego-edge { transition: none; }
}
</style>
