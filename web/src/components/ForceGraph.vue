<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { select, zoom, zoomIdentity } from 'd3'
import {
  NODE_COLORS, NODE_RADIUS, INFLUENCE_EDGE_TYPES,
  EDGE_COLOR_CREDIT, EDGE_COLOR_INFLUENCE,
} from '../lib/palette'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  visibleTypes: { type: Array, default: () => [] },
  visibleEdgeTypes: { type: Array, default: () => [] },
  yearRange: { type: Array, default: () => [1975, 2040] },
  focusId: { type: [Number, String], default: null },
  height: { type: String, default: '470px' },
})
const emit = defineEmits(['select'])

const svgEl = ref(null)
const transform = ref('translate(0,0) scale(1)')
const hoverId = ref(null)
let zoomBehavior = null

const bounds = computed(() => {
  if (!props.nodes.length) return { x: -250, y: -250, w: 500, h: 500 }
  const xs = props.nodes.map(node => node.x)
  const ys = props.nodes.map(node => node.y)
  const minX = Math.min(...xs) - 30
  const minY = Math.min(...ys) - 30
  return { x: minX, y: minY, w: Math.max(...xs) + 30 - minX, h: Math.max(...ys) + 30 - minY }
})
const viewBox = computed(() => `${bounds.value.x} ${bounds.value.y} ${bounds.value.w} ${bounds.value.h}`)

const visibleNodes = computed(() => props.nodes.filter(node => props.visibleTypes.includes(node.type)))
const visibleIds = computed(() => new Set(visibleNodes.value.map(node => node.id)))
const nodeById = computed(() => new Map(props.nodes.map(node => [node.id, node])))
const visibleLinks = computed(() => props.links.filter(link =>
  props.visibleEdgeTypes.includes(link.type)
  && visibleIds.value.has(link.source)
  && visibleIds.value.has(link.target),
))
const degree = computed(() => {
  const counts = new Map()
  for (const link of visibleLinks.value) {
    counts.set(link.source, (counts.get(link.source) || 0) + 1)
    counts.set(link.target, (counts.get(link.target) || 0) + 1)
  }
  return counts
})
const segments = computed(() => visibleLinks.value.map(link => {
  const source = nodeById.value.get(link.source)
  const target = nodeById.value.get(link.target)
  if (!source || !target) return null
  return {
    id: link.id, source: link.source, target: link.target, type: link.type,
    x1: source.x, y1: source.y, x2: target.x, y2: target.y,
  }
}).filter(Boolean))
const labelledIds = computed(() => {
  const top = [...degree.value.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7).map(entry => entry[0])
  return new Set([...top, props.focusId, hoverId.value].filter(value => value !== null && value !== undefined))
})

function isInfluence(type) {
  return INFLUENCE_EDGE_TYPES.includes(type)
}
function isDim(node) {
  const year = node.release_year ?? node.written_year ?? node.chart_year
  if (year == null) return false
  return year < props.yearRange[0] || year > props.yearRange[1]
}
function nodeOpacity(node) {
  if (hoverId.value !== null && hoverId.value !== node.id) {
    const related = segments.value.some(segment =>
      (segment.source === hoverId.value && segment.target === node.id)
      || (segment.target === hoverId.value && segment.source === node.id),
    )
    if (!related) return 0.22
  }
  return isDim(node) ? 0.2 : 1
}
function linkOpacity(segment) {
  if (hoverId.value !== null) {
    return segment.source === hoverId.value || segment.target === hoverId.value ? 0.95 : 0.06
  }
  return isInfluence(segment.type) ? 0.6 : 0.42
}
function radius(node) {
  const base = NODE_RADIUS[node.type] || 4
  return props.focusId === node.id ? base * 1.9 : base
}
function reset() {
  if (svgEl.value && zoomBehavior) {
    select(svgEl.value).call(zoomBehavior.transform, zoomIdentity)
  }
}

onMounted(() => {
  if (!svgEl.value) return
  const svg = select(svgEl.value)
  zoomBehavior = zoom().scaleExtent([0.5, 8]).on('zoom', event => {
    transform.value = `translate(${event.transform.x},${event.transform.y}) scale(${event.transform.k})`
  })
  svg.call(zoomBehavior)
  svg.on('dblclick.zoom', null)
})
onBeforeUnmount(() => {
  if (svgEl.value) select(svgEl.value).on('.zoom', null)
})
</script>

<template>
  <div class="op-graph-wrap" :style="{ height }">
    <svg
      ref="svgEl" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet"
      role="img" aria-label="Sailor Shift 两跳关系图，可缩放拖拽并点击节点查看详情"
    >
      <defs>
        <marker id="op-arrow-influence" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0 1L7 4L0 7Z" :fill="EDGE_COLOR_INFLUENCE" />
        </marker>
      </defs>
      <rect
        :x="bounds.x" :y="bounds.y" :width="bounds.w" :height="bounds.h"
        fill="transparent" @click="emit('select', null)"
      />
      <g :transform="transform">
        <line
          v-for="segment in segments"
          :key="segment.id"
          :x1="segment.x1" :y1="segment.y1" :x2="segment.x2" :y2="segment.y2"
          :stroke="isInfluence(segment.type) ? EDGE_COLOR_INFLUENCE : EDGE_COLOR_CREDIT"
          :stroke-width="isInfluence(segment.type) ? 1.1 : 0.7"
          :stroke-opacity="linkOpacity(segment)"
          :marker-end="isInfluence(segment.type) ? 'url(#op-arrow-influence)' : null"
        />
        <g
          v-for="node in visibleNodes"
          :key="node.id"
          style="cursor: pointer"
          @mouseenter="hoverId = node.id"
          @mouseleave="hoverId = null"
          @click.stop="emit('select', node)"
        >
          <circle
            :cx="node.x" :cy="node.y" :r="radius(node)"
            :fill="NODE_COLORS[node.type] || '#718396'"
            :fill-opacity="nodeOpacity(node)"
            :stroke="props.focusId === node.id ? '#17324d' : '#ffffff'"
            :stroke-width="props.focusId === node.id ? 1.4 : 0.7"
          />
          <text
            v-if="labelledIds.has(node.id)"
            :x="node.x + radius(node) + 2.5" :y="node.y + 2.4"
            font-size="7" fill="#17324d" :fill-opacity="nodeOpacity(node)"
            style="pointer-events: none"
          >{{ node.display_name || node.name }}</text>
        </g>
      </g>
    </svg>
    <div class="op-graph-hint">滚轮缩放 · 拖拽平移 · 悬停聚焦 · 点击节点查看证据</div>
    <div class="op-graph-tools">
      <button type="button" class="op-btn" @click="reset">重置视图</button>
    </div>
  </div>
</template>
