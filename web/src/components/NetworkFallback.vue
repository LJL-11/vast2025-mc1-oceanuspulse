<script setup>
import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
  watch,
} from "vue";
import { useAppStore } from "../stores/useAppStore";
import { useReadingPause, useVisibleMotion } from "../lib/ambientMotion";
import { NODE_COLORS, NODE_LABELS, INFLUENCE_EDGE_TYPES } from "../lib/palette";
import AppIcon from "./AppIcon.vue";

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  visibleTypes: { type: Array, default: null },
  visibleEdgeTypes: { type: Array, default: null },
  yearRange: { type: Array, default: () => [1975, 2040] },
  focusId: { type: [Number, String], default: null },
  flowDirection: { type: String, default: "all" },
  label: { type: String, default: "音乐关系网络" },
  compact: { type: Boolean, default: false },
});
const emit = defineEmits(["select", "open"]);
const store = useAppStore();
const root = ref(null),
  canvas = ref(null),
  hovered = ref(null),
  zoomLabel = ref(100);
const tooltipPosition = ref({ x: 0, y: 0 });
const nodeCount = ref(0),
  edgeCount = ref(0);
const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`,
}));
const reading = useReadingPause();
const inViewport = useVisibleMotion(() => root.value);
const idleMotion = computed(() => store.motionEnabled && inViewport.value && !reading.paused.value);
let ctx,
  observer,
  frame,
  active = true,
  visible = true,
  width = 800,
  height = 500,
  ratio = 1;
let scene = [],
  edges = [],
  projected = [],
  neighbors = new Map(),
  labelIds = new Set();
let pointer = { x: -1000, y: -1000, active: false },
  camera = { x: -0.07, y: 0.1, tx: -0.07, ty: 0.1, zoom: 1 };
let dragging = false,
  dragDistance = 0,
  previousPointer = { x: 0, y: 0 },
  lastFrame = 0,
  dirty = true;
const colors = new Map();
function rgba(hex, alpha) {
  if (!colors.has(hex)) {
    const h = hex.replace("#", "");
    colors.set(
      hex,
      `${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)}`,
    );
  }
  return `rgba(${colors.get(hex)},${alpha})`;
}
function hash(value) {
  let h = 42;
  for (const char of String(value))
    h = Math.imul(h ^ char.charCodeAt(0), 16777619);
  return (h >>> 0) / 4294967295;
}
function inWindow(node) {
  const year = node.release_year ?? node.written_year ?? node.chart_year;
  return (
    year == null || (year >= props.yearRange[0] && year <= props.yearRange[1])
  );
}
function rebuild() {
  if (!props.nodes.length) {
    scene = [];
    edges = [];
    dirty = true;
    return;
  }
  const xs = props.nodes.map((n) => n.x || 0),
    ys = props.nodes.map((n) => n.y || 0);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2,
    cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const xspan = Math.max(1, Math.max(...xs) - Math.min(...xs)),
    yspan = Math.max(1, Math.max(...ys) - Math.min(...ys));
  scene = props.nodes
    .filter(
      (n) => props.visibleTypes === null || props.visibleTypes.includes(n.type),
    )
    .map((node) => ({
      ...node,
      nx: ((node.x || 0) - cx) / xspan,
      ny: ((node.y || 0) - cy) / yspan,
      nz: (hash(node.id) - 0.5) * 0.12,
      color: node.color || NODE_COLORS[node.type] || "#8FD7F8",
      window: inWindow(node),
    }));
  const byId = new Map(scene.map((n) => [n.id, n]));
  neighbors = new Map(scene.map((n) => [n.id, new Set()]));
  edges = props.links
    .filter(
      (l) =>
        props.visibleEdgeTypes === null ||
        props.visibleEdgeTypes.includes(l.type),
    )
    .map((link, index) => {
      const rawSource = link.source?.id ?? link.source,
        rawTarget = link.target?.id ?? link.target;
      const influence = INFLUENCE_EDGE_TYPES.includes(link.type);
      // Pipeline overview assets explicitly retain raw citation direction: borrower -> inspiration.
      const source = byId.get(influence ? rawTarget : rawSource),
        target = byId.get(influence ? rawSource : rawTarget);
      if (!source || !target) return null;
      neighbors.get(source.id).add(target.id);
      neighbors.get(target.id).add(source.id);
      return {
        ...link,
        source,
        target,
        influence,
        curved: link.type === "genre-flow",
        phase: index * 0.127,
        bend: (hash(link.id || `${rawSource}-${rawTarget}`) - 0.5) * 0.2,
      };
    })
    .filter(Boolean);
  const top = [...neighbors]
    .sort((a, b) => b[1].size - a[1].size)
    .slice(0, props.nodes.length < 40 ? 40 : 7)
    .map(([id]) => id);
  labelIds = new Set([...top, 17255]);
  nodeCount.value = scene.length;
  edgeCount.value = edges.length;
  dirty = true;
}
function project(node, time) {
  const sizeX = width * (width < 600 ? 0.66 : 0.73) * camera.zoom,
    sizeY = height * 0.68 * camera.zoom;
  const sway = idleMotion.value
    ? Math.sin(time * 0.34 + hash(node.id) * 6.28) * 0.003
    : 0;
  const x = node.nx,
    y = node.ny + sway,
    z = node.nz;
  const coY = Math.cos(camera.y),
    siY = Math.sin(camera.y),
    coX = Math.cos(camera.x),
    siX = Math.sin(camera.x);
  const rx = x * coY - z * siY,
    rz = x * siY + z * coY,
    ry = y * coX - rz * siX,
    depth = y * siX + rz * coX;
  const perspective = 1 / (1 + depth * 0.55);
  return {
    ...node,
    sx: width * 0.5 + rx * sizeX * perspective,
    sy: height * 0.51 + ry * sizeY * perspective,
    depth,
    perspective,
  };
}
function background() {
  ctx.fillStyle = "#0C1421";
  ctx.fillRect(0, 0, width, height);
  for (const [x, y, r, color] of [
    [width * 0.48, height * 0.45, width * 0.46, "#1F3D64"],
    [width * 0.78, height * 0.72, width * 0.27, "#42302B"],
  ]) {
    const glow = ctx.createRadialGradient(x, y, 0, x, y, r);
    glow.addColorStop(0, rgba(color, 0.28));
    glow.addColorStop(0.5, rgba(color, 0.09));
    glow.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);
  }
  if (pointer.active && store.motionEnabled) {
    const halo = ctx.createRadialGradient(
      pointer.x,
      pointer.y,
      0,
      pointer.x,
      pointer.y,
      180,
    );
    halo.addColorStop(0, "rgba(108,190,247,.09)");
    halo.addColorStop(0.4, "rgba(106,155,225,.025)");
    halo.addColorStop(1, "rgba(90,160,235,0)");
    ctx.fillStyle = halo;
    ctx.fillRect(0, 0, width, height);
  }
}
function draw(now) {
  if (!ctx || !width || !height) return;
  const time = now / 1000;
  const easing = idleMotion.value ? 0.055 : 1;
  camera.x += (camera.tx - camera.x) * easing;
  camera.y += (camera.ty - camera.y) * easing;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  background();
  projected = scene.map((n) => project(n, time));
  const byId = new Map(projected.map((n) => [n.id, n]));
  const activeId = hovered.value?.id ?? props.focusId,
    focusNeighbors = neighbors.get(activeId);
  const flowEdges = [];
  for (const edge of edges) {
    if (
      edge.curved &&
      props.flowDirection !== "all" &&
      props.focusId != null &&
      (props.flowDirection === "in" ? edge.target.id : edge.source.id) !==
        props.focusId
    )
      continue;
    const a = byId.get(edge.source.id),
      b = byId.get(edge.target.id);
    const related = a.id === activeId || b.id === activeId;
    const on = a.window && b.window,
      muted = activeId != null && !related;
    const color = edge.curved
      ? a.id === props.focusId
        ? "#8FD7F8"
        : b.id === props.focusId
          ? "#DFC180"
          : a.color
      : edge.influence
        ? "#E7B58A"
        : "#7092BE";
    const alpha = !on
      ? 0.022
      : related
        ? 0.65
        : muted
          ? 0.045
          : edge.curved
            ? 0.16
            : 0.14;
    const dx = b.sx - a.sx,
      dy = b.sy - a.sy,
      cx = (a.sx + b.sx) / 2 - dy * edge.bend,
      cy = (a.sy + b.sy) / 2 + dx * edge.bend;
    ctx.beginPath();
    ctx.moveTo(a.sx, a.sy);
    ctx.quadraticCurveTo(cx, cy, b.sx, b.sy);
    ctx.strokeStyle = rgba(color, alpha);
    ctx.lineWidth = related
      ? 1.25
      : edge.curved
        ? Math.max(0.7, Math.min(3, Math.log1p(edge.value || 1) * 0.48))
        : 0.55;
    ctx.stroke();
    if (
      on &&
      (related || (activeId == null && (edge.influence || edge.curved))) &&
      flowEdges.length < 60
    )
      flowEdges.push({ a, b, cx, cy, color, phase: edge.phase });
  }
  if (idleMotion.value) {
    for (const edge of flowEdges) {
      const p = (time * 0.19 + edge.phase) % 1;
      for (let trail = 4; trail >= 0; trail--) {
        const t = (p - trail * 0.014 + 1) % 1,
          inv = 1 - t;
        const x =
            inv * inv * edge.a.sx + 2 * inv * t * edge.cx + t * t * edge.b.sx,
          y = inv * inv * edge.a.sy + 2 * inv * t * edge.cy + t * t * edge.b.sy;
        ctx.beginPath();
        ctx.arc(x, y, trail === 0 ? 1.65 : 0.9, 0, Math.PI * 2);
        ctx.fillStyle = rgba(edge.color, (1 - trail / 5) * 0.8);
        ctx.fill();
      }
    }
  }
  for (const node of [...projected].sort((a, b) => b.depth - a.depth)) {
    const selected = node.id === props.focusId,
      hover = node.id === hovered.value?.id,
      related =
        activeId == null ||
        node.id === activeId ||
        focusNeighbors?.has(node.id);
    const alpha = !node.window ? 0.16 : related ? 1 : 0.3;
    const base =
      node.type === "Genre" && width < 600
        ? node.id === props.focusId
          ? 12
          : 6
        : node.radius ||
          (node.id === 17255 ? 7 : node.type === "Genre" ? 10 : 3);
    const r = Math.max(2, base * node.perspective * (selected ? 1.18 : 1)),
      glowR = r * (hover || selected ? 5 : 3);
    const gradient = ctx.createRadialGradient(
      node.sx,
      node.sy,
      0,
      node.sx,
      node.sy,
      glowR,
    );
    gradient.addColorStop(
      0,
      rgba(node.color, (hover || selected ? 0.42 : 0.19) * alpha),
    );
    gradient.addColorStop(1, rgba(node.color, 0));
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(node.sx, node.sy, glowR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = rgba(node.color, alpha);
    ctx.beginPath();
    ctx.arc(node.sx, node.sy, r, 0, Math.PI * 2);
    ctx.fill();
    if (selected || hover) {
      ctx.beginPath();
      ctx.arc(
        node.sx,
        node.sy,
        r + 5 + (idleMotion.value ? Math.sin(time * 1.8) * 1.5 : 0),
        0,
        Math.PI * 2,
      );
      ctx.strokeStyle = rgba(node.color, 0.5);
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(node.sx, node.sy, r + 10, 0, Math.PI * 2);
      ctx.strokeStyle = rgba(node.color, 0.13);
      ctx.stroke();
    }
    if ((width > 600 && labelIds.has(node.id)) || selected || hover) {
      const label = node.display_name || node.name;
      ctx.font = `${selected || hover ? "500" : "400"} ${node.type === "Genre" ? 13 : selected ? 14 : 12}px "Host Grotesk","Microsoft YaHei",sans-serif`;
      const left = node.sx + r + 8 + ctx.measureText(label).width > width - 16,
        labelX = left ? node.sx - r - 8 : node.sx + r + 8;
      ctx.textAlign = left ? "right" : "left";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 4;
      ctx.strokeStyle = rgba("#0C1421", 0.9);
      ctx.strokeText(label, labelX, node.sy);
      ctx.fillStyle = rgba(
        selected || hover ? "#F0F7FF" : "#B4C6DF",
        related ? 0.95 : 0.4,
      );
      ctx.fillText(label, labelX, node.sy);
    }
    node.hitRadius = Math.max(10, r + 5);
  }
  dirty = false;
}
function loop(now) {
  frame = requestAnimationFrame(loop);
  if (!active || !visible || document.hidden || now - lastFrame < 32) return;
  if (!idleMotion.value && !dirty) return;
  lastFrame = now;
  draw(now);
}
function resize() {
  if (!root.value || !canvas.value) return;
  const rect = root.value.getBoundingClientRect();
  width = Math.max(1, rect.width);
  height = Math.max(1, rect.height);
  ratio = Math.min(devicePixelRatio || 1, 2);
  canvas.value.width = Math.round(width * ratio);
  canvas.value.height = Math.round(height * ratio);
  dirty = true;
  draw(performance.now());
}
function hitAt(x, y) {
  let best = null,
    distance = Infinity;
  for (const node of projected) {
    const d = Math.hypot(x - node.sx, y - node.sy);
    if (d < (node.hitRadius || 10) && d < distance) {
      best = node;
      distance = d;
    }
  }
  return best;
}
function move(event) {
  const rect = canvas.value.getBoundingClientRect();
  pointer = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
    active: event.pointerType !== "touch",
  };
  if (dragging) {
    const dx = event.clientX - previousPointer.x,
      dy = event.clientY - previousPointer.y;
    dragDistance += Math.abs(dx) + Math.abs(dy);
    camera.ty += dx * 0.003;
    camera.tx = Math.max(-0.55, Math.min(0.55, camera.tx + dy * 0.003));
    previousPointer = { x: event.clientX, y: event.clientY };
  } else {
    const node = hitAt(pointer.x, pointer.y);
    if (node?.id !== hovered.value?.id) hovered.value = node;
    tooltipPosition.value = {
      x: Math.min(width - 220, Math.max(12, pointer.x + 16)),
      y: Math.max(48, Math.min(height - 80, pointer.y - 28)),
    };
  }
  dirty = true;
}
function down(event) {
  dragging = true;
  dragDistance = 0;
  previousPointer = { x: event.clientX, y: event.clientY };
  canvas.value.setPointerCapture(event.pointerId);
}
function up(event) {
  dragging = false;
  if (dragDistance < 5) {
    const rect = canvas.value.getBoundingClientRect();
    const node = hitAt(event.clientX - rect.left, event.clientY - rect.top);
    emit("select", node || null);
  }
  dirty = true;
}
function leave() {
  pointer.active = false;
  hovered.value = null;
  dirty = true;
}
function zoomBy(factor) {
  camera.zoom = Math.max(0.55, Math.min(3, camera.zoom * factor));
  zoomLabel.value = Math.round(camera.zoom * 100);
  dirty = true;
}
function reset() {
  camera = { x: -0.07, y: 0.1, tx: -0.07, ty: 0.1, zoom: 1 };
  zoomLabel.value = 100;
  dirty = true;
}
function keyboard(event) {
  if (
    [
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "+",
      "-",
      "Enter",
    ].includes(event.key)
  )
    event.preventDefault();
  if (event.key === "ArrowLeft") camera.ty -= 0.12;
  if (event.key === "ArrowRight") camera.ty += 0.12;
  if (event.key === "ArrowUp") camera.tx -= 0.1;
  if (event.key === "ArrowDown") camera.tx += 0.1;
  if (event.key === "+") zoomBy(1.2);
  if (event.key === "-") zoomBy(0.8);
  if (event.key === "Enter" && hovered.value) emit("open", hovered.value);
  dirty = true;
}
function exportImage() {
  draw(performance.now());
  const a = document.createElement("a");
  a.download = "OceanusPulse-network.png";
  a.href = canvas.value.toDataURL("image/png");
  a.click();
}
watch(
  [
    () => props.nodes,
    () => props.links,
    () => props.visibleTypes,
    () => props.visibleEdgeTypes,
    () => props.yearRange,
  ],
  rebuild,
  { deep: true },
);
watch([() => props.focusId, () => props.flowDirection], () => {
  dirty = true;
});
watch(
  idleMotion,
  () => {
    dirty = true;
  },
);
onMounted(() => {
  ctx = canvas.value.getContext("2d", { alpha: false });
  rebuild();
  observer = new ResizeObserver(resize);
  observer.observe(root.value);
  resize();
  frame = requestAnimationFrame(loop);
});
onActivated(() => {
  active = true;
  dirty = true;
  if (ctx) resize();
});
onDeactivated(() => {
  active = false;
});
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  observer?.disconnect();
});
</script>

<template>
  <div
    ref="root"
    class="network-canvas-root"
    :class="{ 'is-dragging': dragging }"
    v-on="reading.events"
  >
    <canvas
      ref="canvas"
      class="network-canvas"
      tabindex="0"
      role="img"
      :aria-label="`${label}。拖拽旋转，滚轮缩放；使用下方控件或外部搜索选择实体。`"
      @pointermove="move"
      @pointerdown="down"
      @pointerup="up"
      @pointerleave="leave"
      @wheel.prevent="zoomBy($event.deltaY > 0 ? 0.93 : 1.07)"
      @keydown="keyboard"
      @dblclick="hovered && emit('open', hovered)"
    />
    <div class="graph-context">
      <span class="graph-status"><i />{{ label }}</span
      ><span>{{ nodeCount }} 个实体 · {{ edgeCount }} 条联系</span>
    </div>
    <div
      v-if="hovered && !dragging"
      class="canvas-tooltip"
      :style="tooltipStyle"
    >
      <i :style="{ background: hovered.color }" /><strong>{{
        hovered.display_name || hovered.name
      }}</strong
      ><span>{{
        hovered.type === "Genre"
          ? `${hovered.value} 部作品 · 双击进入传播分析`
          : `${NODE_LABELS[hovered.type] || hovered.type} · 点击查看档案`
      }}</span>
    </div>
    <div v-if="!nodes.length" class="graph-empty">当前没有匹配的网络实体</div>
    <div class="graph-bottom">
      <span class="graph-gesture">拖拽旋转 · 滚轮缩放 · 双击进入分析</span>
      <div class="op-graph-tools">
        <button
          class="btn btn--secondary icon-button"
          :aria-label="store.motionEnabled ? '暂停图谱动效' : '开启图谱动效'"
          :aria-pressed="store.motionEnabled"
          @click="store.motionEnabled = !store.motionEnabled"
        >
          <AppIcon
            :name="store.motionEnabled ? 'pause' : 'play'"
            :size="13"
          /></button
        ><button
          class="btn btn--secondary icon-button"
          aria-label="缩小关系图"
          @click="zoomBy(0.8)"
        >
          <AppIcon name="minus" :size="15" /></button
        ><span>{{ zoomLabel }}%</span
        ><button
          class="btn btn--secondary icon-button"
          aria-label="放大关系图"
          @click="zoomBy(1.25)"
        >
          <AppIcon name="plus" :size="15" /></button
        ><button
          class="btn btn--secondary icon-button"
          aria-label="重置图谱视角"
          @click="reset"
        >
          <AppIcon name="reset" :size="15" /></button
        ><button
          class="btn btn--secondary icon-button"
          aria-label="导出图谱图片"
          @click="exportImage"
        >
          <AppIcon name="download" :size="15" />
        </button>
      </div>
    </div>
  </div>
</template>
