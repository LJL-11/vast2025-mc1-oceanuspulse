<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from "vue";
import { select, zoom, zoomIdentity } from "d3";
import {
  NODE_COLORS,
  NODE_LABELS,
  NODE_RADIUS,
  INFLUENCE_EDGE_TYPES,
  EDGE_COLOR_CREDIT,
  EDGE_COLOR_INFLUENCE,
} from "../lib/palette";
import AppIcon from "./AppIcon.vue";
const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  visibleTypes: { type: Array, default: () => [] },
  visibleEdgeTypes: { type: Array, default: () => [] },
  yearRange: { type: Array, default: () => [1975, 2040] },
  focusId: { type: [Number, String], default: null },
  height: { type: String, default: "100%" },
});
const emit = defineEmits(["select"]);
const svgEl = ref(null);
const transform = ref("translate(0,0) scale(1)");
const hoverId = ref(null);
const zoomLevel = ref(1);
const id = useId().replace(/:/g, "");
let zoomBehavior;
const bounds = computed(() => {
  if (!props.nodes.length) return { x: -250, y: -250, w: 500, h: 500 };
  const xs = props.nodes.map((n) => n.x),
    ys = props.nodes.map((n) => n.y);
  const x = Math.min(...xs) - 36,
    y = Math.min(...ys) - 36;
  return { x, y, w: Math.max(...xs) + 72 - x, h: Math.max(...ys) + 72 - y };
});
const viewBox = computed(
  () =>
    `${bounds.value.x} ${bounds.value.y} ${bounds.value.w} ${bounds.value.h}`,
);
const visibleNodes = computed(() =>
  props.nodes.filter((n) => props.visibleTypes.includes(n.type)),
);
const visibleIds = computed(() => new Set(visibleNodes.value.map((n) => n.id)));
const nodeById = computed(() => new Map(props.nodes.map((n) => [n.id, n])));
const segments = computed(() =>
  props.links
    .filter(
      (l) =>
        props.visibleEdgeTypes.includes(l.type) &&
        visibleIds.value.has(l.source) &&
        visibleIds.value.has(l.target),
    )
    .map((l) => {
      const influence = INFLUENCE_EDGE_TYPES.includes(l.type);
      const source = influence ? l.target : l.source,
        target = influence ? l.source : l.target;
      return {
        ...l,
        source,
        target,
        a: nodeById.value.get(source),
        b: nodeById.value.get(target),
      };
    }),
);
const adjacency = computed(() => {
  const map = new Map();
  for (const link of segments.value) {
    if (!map.has(link.source)) map.set(link.source, new Set());
    if (!map.has(link.target)) map.set(link.target, new Set());
    map.get(link.source).add(link.target);
    map.get(link.target).add(link.source);
  }
  return map;
});
const labelledIds = computed(
  () =>
    new Set([
      17255,
      props.focusId,
      hoverId.value,
      ...[...adjacency.value]
        .sort((a, b) => b[1].size - a[1].size)
        .slice(0, 4)
        .map(([key]) => key),
    ]),
);
const hovered = computed(() => nodeById.value.get(hoverId.value));
const activeCount = computed(
  () => visibleNodes.value.filter((n) => !isDim(n)).length,
);
const isInfluence = (type) => INFLUENCE_EDGE_TYPES.includes(type);
function isDim(node) {
  const year = node.release_year ?? node.written_year ?? node.chart_year;
  return (
    year != null && (year < props.yearRange[0] || year > props.yearRange[1])
  );
}
function opacity(node) {
  if (
    hoverId.value !== null &&
    hoverId.value !== node.id &&
    !adjacency.value.get(hoverId.value)?.has(node.id)
  )
    return 0.12;
  return isDim(node) ? 0.13 : 1;
}
function lineOpacity(link) {
  if (isDim(link.a) || isDim(link.b)) return 0.035;
  if (hoverId.value !== null)
    return link.source === hoverId.value || link.target === hoverId.value
      ? 0.95
      : 0.035;
  return isInfluence(link.type) ? 0.48 : 0.23;
}
function radius(node) {
  return node.id === 17255
    ? 9
    : props.focusId === node.id
      ? 7.5
      : NODE_RADIUS[node.type] || 4;
}
function reset() {
  if (svgEl.value && zoomBehavior)
    select(svgEl.value).call(zoomBehavior.transform, zoomIdentity);
}
function scale(amount) {
  if (svgEl.value && zoomBehavior)
    select(svgEl.value).call(zoomBehavior.scaleBy, amount);
}
function keyboard(event, node) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    emit("select", node);
  }
  if (event.key === "Escape") emit("select", null);
}
onMounted(() => {
  zoomBehavior = zoom()
    .scaleExtent([0.5, 6])
    .on("zoom", (event) => {
      zoomLevel.value = event.transform.k;
      transform.value = `translate(${event.transform.x},${event.transform.y}) scale(${event.transform.k})`;
    });
  select(svgEl.value).call(zoomBehavior).on("dblclick.zoom", null);
});
onBeforeUnmount(() => {
  if (svgEl.value) select(svgEl.value).on(".zoom", null);
});
</script>
<template>
  <div class="op-graph-wrap" :style="{ height }">
    <div class="graph-context">
      <span class="graph-status"><i />Sailor Shift · 两跳关系网络</span
      ><span
        >{{ activeCount }} 个时段内实体 · {{ segments.length }} 条关系</span
      >
    </div>
    <svg
      ref="svgEl"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      role="group"
      aria-label="Sailor Shift 关系图谱；使用搜索或点击节点查看证据"
    >
      <defs>
        <marker
          :id="`arrow-${id}`"
          viewBox="0 0 8 8"
          refX="13"
          refY="4"
          markerWidth="5"
          markerHeight="5"
          orient="auto"
        >
          <path d="M0 1L7 4L0 7Z" :fill="EDGE_COLOR_INFLUENCE" />
        </marker>
      </defs>
      <rect
        :x="bounds.x"
        :y="bounds.y"
        :width="bounds.w"
        :height="bounds.h"
        fill="transparent"
        @click="emit('select', null)"
      />
      <g :transform="transform">
        <line
          v-for="segment in segments"
          :key="segment.id"
          :x1="segment.a.x"
          :y1="segment.a.y"
          :x2="segment.b.x"
          :y2="segment.b.y"
          :stroke="
            isInfluence(segment.type) ? EDGE_COLOR_INFLUENCE : EDGE_COLOR_CREDIT
          "
          :stroke-width="isInfluence(segment.type) ? 1 : 0.65"
          :stroke-opacity="lineOpacity(segment)"
          :marker-end="isInfluence(segment.type) ? `url(#arrow-${id})` : null"
        />
        <g
          v-for="node in visibleNodes"
          :key="node.id"
          class="network-node"
          role="button"
          :tabindex="node.id === (focusId ?? 17255) ? 0 : -1"
          :aria-label="`${node.display_name || node.name}，${NODE_LABELS[node.type]}`"
          :aria-pressed="focusId === node.id"
          @mouseenter="hoverId = node.id"
          @mouseleave="hoverId = null"
          @focus="hoverId = node.id"
          @blur="hoverId = null"
          @keydown="keyboard($event, node)"
          @click.stop="emit('select', node)"
        >
          <circle
            v-if="node.id === focusId || node.id === 17255"
            :cx="node.x"
            :cy="node.y"
            :r="radius(node) + 5"
            fill="none"
            :stroke="NODE_COLORS[node.type]"
            stroke-width=".7"
            stroke-opacity=".55"
          />
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="radius(node) + 4"
            fill="transparent"
          />
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="radius(node)"
            :fill="NODE_COLORS[node.type]"
            :fill-opacity="opacity(node)"
            stroke="#0d1521"
            stroke-width="1"
          />
          <text
            v-if="labelledIds.has(node.id)"
            :x="node.x + radius(node) + 5"
            :y="node.y + 3"
            :font-size="node.id === 17255 ? 10 : 8"
            :font-weight="node.id === 17255 ? 500 : 400"
            :fill="node.id === 17255 ? '#e8f3ff' : '#aabbd4'"
            :fill-opacity="opacity(node)"
            paint-order="stroke"
            stroke="#0d1521"
            stroke-width="3"
            style="pointer-events: none"
          >
            {{ node.display_name || node.name }}
          </text>
        </g>
      </g>
    </svg>
    <div v-if="hovered" class="graph-hover">
      <i :style="{ background: NODE_COLORS[hovered.type] }" /><strong>{{
        hovered.display_name || hovered.name
      }}</strong
      ><span
        >{{ NODE_LABELS[hovered.type] }} ·
        {{ adjacency.get(hovered.id)?.size || 0 }} 个相邻实体</span
      >
    </div>
    <div v-if="!visibleNodes.length" class="graph-empty">
      未显示任何实体，请开启上方实体类型。
    </div>
    <div class="graph-bottom">
      <span class="graph-gesture">拖拽平移 · 滚轮缩放 · 点击查看证据</span>
      <div class="op-graph-tools">
        <button
          class="btn btn--secondary icon-button"
          aria-label="缩小关系图"
          @click="scale(0.8)"
        >
          <AppIcon name="minus" :size="16" /></button
        ><span>{{ Math.round(zoomLevel * 100) }}%</span
        ><button
          class="btn btn--secondary icon-button"
          aria-label="放大关系图"
          @click="scale(1.25)"
        >
          <AppIcon name="plus" :size="16" /></button
        ><button
          class="btn btn--secondary icon-button"
          aria-label="重置关系图位置"
          title="重置关系图位置"
          @click="reset"
        >
          <AppIcon name="reset" :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>
