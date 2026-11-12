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
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { useAppStore } from "../stores/useAppStore";
import { useReadingPause } from "../lib/ambientMotion";
import { NODE_COLORS, NODE_LABELS, INFLUENCE_EDGE_TYPES } from "../lib/palette";
import AppIcon from "./AppIcon.vue";
import { genreIcons } from "../lib/genre-icons";
import { genreIconNames } from "../lib/genre-icon-map";

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  visibleTypes: { type: Array, default: null },
  visibleEdgeTypes: { type: Array, default: null },
  yearRange: { type: Array, default: () => [1975, 2040] },
  focusId: { type: [String, Number], default: null },
  flowDirection: { type: String, default: "all" },
  label: { type: String, default: "音乐关系网络" },
});
const emit = defineEmits(["select", "open", "unsupported"]);
const store = useAppStore(),
  root = ref(null),
  canvas = ref(null),
  hovered = ref(null),
  zoomLabel = ref(100),
  nodeCount = ref(0),
  edgeCount = ref(0),
  shownEdgeCount = ref(0),
  labelItems = ref([]),
  tooltipPosition = ref({ x: 0, y: 0 });
const tooltipStyle = computed(() => ({
  left: `${tooltipPosition.value.x}px`,
  top: `${tooltipPosition.value.y}px`,
}));
const reading = useReadingPause();
const idleMotion = computed(() => store.motionEnabled && !reading.paused.value);
const labelElements = new Map(),
  nodesById = new Map(),
  instanceMeshes = new Map(),
  textures = new Map(),
  neighbors = new Map();
let renderer,
  scene,
  camera,
  controls,
  observer,
  visibilityObserver,
  frame,
  active = true,
  visible = true,
  width = 800,
  height = 500,
  lastFrame = 0,
  dirty = true,
  initialDistance = 800,
  group,
  lineMesh,
  particleMesh,
  selectionRing,
  hoverRing,
  starDust,
  interacted = false;
let edges = [],
  pickable = [],
  dragNode = null,
  dragDistance = 0,
  downPoint = null,
  hoverId = null,
  disposed = false,
  rendererFailed = false,
  baseGeometry = new Map(),
  pointTexture;
const raycaster = new THREE.Raycaster(),
  pointer = new THREE.Vector2(),
  dragPlane = new THREE.Plane(),
  dragPoint = new THREE.Vector3(),
  dragOffset = new THREE.Vector3(),
  scratch = new THREE.Object3D();
function hash(value) {
  let n = 42;
  for (const c of String(value)) n = Math.imul(n ^ c.charCodeAt(0), 16777619);
  return (n >>> 0) / 4294967295;
}
function inWindow(node) {
  const y = node.release_year ?? node.written_year ?? node.chart_year;
  return y == null || (y >= props.yearRange[0] && y <= props.yearRange[1]);
}
function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const x = c.getContext("2d");
  const g = x.createRadialGradient(16, 16, 0, 16, 16, 16);
  g.addColorStop(0, "#fff");
  g.addColorStop(0.15, "#ffffff");
  g.addColorStop(0.42, "#ffffff90");
  g.addColorStop(1, "#ffffff00");
  x.fillStyle = g;
  x.fillRect(0, 0, 32, 32);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
function badgeTexture(name) {
  const key = `icon:${name}`;
  if (textures.has(key)) return textures.get(key);
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  const image = new Image();
  image.onload = () => {
    const context = c.getContext("2d");
    context.clearRect(0, 0, 128, 128);
    context.drawImage(image, 24, 24, 80, 80);
    texture.needsUpdate = true;
    dirty = true;
  };
  image.src =
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      (genreIcons[name] || genreIcons["music-2"]).replaceAll(
        "currentColor",
        "#F1F7FF",
      ),
    );
  textures.set(key, texture);
  return texture;
}
function merge(parts) {
  return mergeGeometries(parts.map((g) => (g.index ? g.toNonIndexed() : g)));
}
function entityGeometry(type) {
  if (baseGeometry.has(type)) return baseGeometry.get(type);
  let result;
  if (type === "Person")
    result = merge(
      [10, 18, 26, 18, 10].map((h, i) =>
        new THREE.BoxGeometry(3.5, h, 4).translate((i - 2) * 5.5, 0, 0),
      ),
    );
  else if (type === "Song")
    result = merge([
      new THREE.CylinderGeometry(6, 6, 4, 16)
        .rotateX(Math.PI / 2)
        .translate(-5, -8, 0),
      new THREE.BoxGeometry(3, 25, 4).translate(0, 3, 0),
      new THREE.BoxGeometry(11, 3, 4).rotateZ(-0.3).translate(4, 16, 0),
    ]);
  else if (type === "Album")
    result = merge([
      new THREE.BoxGeometry(23, 26, 4),
      new THREE.BoxGeometry(3, 28, 5).translate(-11, 0, 0),
    ]);
  else if (type === "MusicalGroup")
    result = merge(
      [-8, 0, 8].map((x, i) =>
        new THREE.CylinderGeometry(7, 7, 3, 20)
          .rotateX(Math.PI / 2)
          .translate(x, i === 1 ? 4 : -3, i),
      ),
    );
  else
    result = merge([
      new THREE.BoxGeometry(27, 15, 4),
      new THREE.BoxGeometry(20, 2, 5).translate(0, 4, 0),
      new THREE.BoxGeometry(12, 2, 5).translate(-4, -1, 0),
    ]);
  baseGeometry.set(type, result);
  return result;
}
function disposeObject(object) {
  object.traverse((child) => {
    if (child.geometry && !baseGeometry.has(child.userData.type))
      child.geometry.dispose();
    if (child.material) {
      for (const m of Array.isArray(child.material)
        ? child.material
        : [child.material])
        m.dispose();
    }
  });
}
function labels() {
  const selected = nodesById.get(props.focusId),
    hover = nodesById.get(hoverId),
    all = [...nodesById.values()];
  const top =
    all[0]?.data.type === "Genre"
      ? all
      : all
          .sort(
            (a, b) =>
              (neighbors.get(b.data.id)?.size || 0) -
              (neighbors.get(a.data.id)?.size || 0),
          )
          .slice(0, 7);
  labelItems.value = [
    ...new Map(
      [selected, hover, ...top].filter(Boolean).map((n) => [
        n.data.id,
        {
          id: n.data.id,
          name: n.data.display_name || n.data.name,
          color: n.color,
        },
      ]),
    ).values(),
  ];
}
function rebuild() {
  if (!scene) return;
  if (group) {
    scene.remove(group);
    disposeObject(group);
  }
  group = new THREE.Group();
  scene.add(group);
  nodesById.clear();
  instanceMeshes.clear();
  neighbors.clear();
  pickable = [];
  const nodes = props.nodes.filter(
    (n) => props.visibleTypes === null || props.visibleTypes.includes(n.type),
  );
  const xs = props.nodes.map((n) => n.x || 0),
    ys = props.nodes.map((n) => n.y || 0);
  const midX = xs.length ? (Math.min(...xs) + Math.max(...xs)) / 2 : 0,
    midY = ys.length ? (Math.min(...ys) + Math.max(...ys)) / 2 : 0;
  const spanX = Math.max(1, Math.max(...xs) - Math.min(...xs)),
    spanY = Math.max(1, Math.max(...ys) - Math.min(...ys));
  const zs = props.nodes.map((n) => n.z || 0),
    spanZ = Math.max(1, Math.max(...zs) - Math.min(...zs)),
    midZ = (Math.max(...zs) + Math.min(...zs)) / 2;
  const sphereScale = 650 / Math.max(spanX, spanY, spanZ);
  for (const data of nodes) {
    const color = data.color || NODE_COLORS[data.type] || "#8FD7F8",
      genre = data.type === "Genre";
    const position = genre
      ? new THREE.Vector3(
          (data.x - midX) * sphereScale,
          -(data.y - midY) * sphereScale,
          ((data.z || 0) - midZ) * sphereScale,
        )
      : new THREE.Vector3(
          ((data.x - midX) / spanX) * 820,
          (-(data.y - midY) / spanY) * (width < 600 ? 700 : 450),
          (hash(data.id) - 0.5) * 180,
        );
    const radius = genre ? 20 + Math.sqrt(data.value || 1) * 0.8 : 14;
    nodesById.set(data.id, {
      data: { ...data },
      position,
      original: position.clone(),
      color,
      radius,
      genre,
      object: null,
      instance: null,
    });
    neighbors.set(data.id, new Set());
  }
  const types = [
    ...new Set(nodes.filter((n) => n.type !== "Genre").map((n) => n.type)),
  ];
  for (const type of types) {
    const ofType = [...nodesById.values()].filter((n) => n.data.type === type);
    const material = new THREE.MeshStandardMaterial({
      color: "#ffffff",
      roughness: 0.42,
      metalness: 0.3,
    });
    const mesh = new THREE.InstancedMesh(
      entityGeometry(type),
      material,
      ofType.length,
    );
    mesh.userData.ids = ofType.map((n) => n.data.id);
    mesh.userData.type = type;
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    group.add(mesh);
    instanceMeshes.set(type, mesh);
    pickable.push(mesh);
    ofType.forEach((node, index) => {
      node.object = mesh;
      node.instance = index;
      updateNode(node);
    });
  }
  for (const node of nodesById.values()) {
    if (!node.genre) continue;
    const record = new THREE.Group();
    record.position.copy(node.position);
    record.userData.nodeId = node.data.id;
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(node.radius, 28, 20),
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(node.color).multiplyScalar(0.34),
        emissive: node.color,
        emissiveIntensity: 0.09,
        roughness: 0.28,
        metalness: 0.48,
      }),
    );
    record.add(sphere);
    node.core = sphere;
    const icon = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: badgeTexture(genreIconNames[node.data.name] || "music-2"),
        transparent: true,
        depthWrite: false,
      }),
    );
    icon.scale.setScalar(node.radius * 1.32);
    record.add(icon);
    node.icon = icon;
    node.object = record;
    group.add(record);
    pickable.push(sphere, icon);
  }
  if (nodes[0]?.type === "Genre") {
    const positions = new Float32Array(1100 * 3),
      colors = new Float32Array(1100 * 3);
    for (let i = 0; i < 1100; i++) {
      const u = hash(`dust-u-${i}`),
        v = hash(`dust-v-${i}`),
        theta = u * Math.PI * 2,
        cos = 2 * v - 1,
        sin = Math.sqrt(1 - cos * cos),
        radius = 180 + hash(`dust-r-${i}`) * 640;
      positions.set(
        [
          Math.cos(theta) * sin * radius,
          cos * radius * 0.8,
          Math.sin(theta) * sin * radius,
        ],
        i * 3,
      );
      const color = new THREE.Color(
        i % 5 === 0 ? "#D5B287" : "#7CA3D1",
      ).multiplyScalar(0.35 + hash(i) * 0.3);
      colors.set([color.r, color.g, color.b], i * 3);
    }
    const dustGeometry = new THREE.BufferGeometry();
    dustGeometry.setAttribute(
      "position",
      new THREE.BufferAttribute(positions, 3),
    );
    dustGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    starDust = new THREE.Points(
      dustGeometry,
      new THREE.PointsMaterial({
        vertexColors: true,
        size: 1.5,
        map: pointTexture,
        transparent: true,
        opacity: 0.4,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    group.add(starDust);
  } else starDust = null;
  edges = props.links
    .filter(
      (l) =>
        props.visibleEdgeTypes === null ||
        props.visibleEdgeTypes.includes(l.type),
    )
    .map((data, index) => {
      const rawSource = data.source?.id ?? data.source,
        rawTarget = data.target?.id ?? data.target,
        reverse = INFLUENCE_EDGE_TYPES.includes(data.type);
      const a = nodesById.get(reverse ? rawTarget : rawSource),
        b = nodesById.get(reverse ? rawSource : rawTarget);
      if (!a || !b) return null;
      neighbors.get(a.data.id).add(b.data.id);
      neighbors.get(b.data.id).add(a.data.id);
      return {
        data,
        a,
        b,
        phase: index * 0.173,
        bend: (hash(data.id || index) - 0.5) * 50,
      };
    })
    .filter(Boolean);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(edges.length * 18), 3),
  );
  geometry.setAttribute(
    "color",
    new THREE.BufferAttribute(new Float32Array(edges.length * 18), 3),
  );
  lineMesh = new THREE.LineSegments(
    geometry,
    new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
    }),
  );
  group.add(lineMesh);
  const particles = new THREE.BufferGeometry();
  particles.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(120 * 3), 3),
  );
  particles.setAttribute(
    "color",
    new THREE.BufferAttribute(new Float32Array(120 * 3), 3),
  );
  particleMesh = new THREE.Points(
    particles,
    new THREE.PointsMaterial({
      size: 5,
      map: pointTexture,
      vertexColors: true,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    }),
  );
  group.add(particleMesh);
  const ringGeometry = new THREE.RingGeometry(1, 1.025, 64);
  selectionRing = new THREE.Mesh(
    ringGeometry,
    new THREE.MeshBasicMaterial({
      color: "#8FD7F8",
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  group.add(selectionRing);
  hoverRing = new THREE.Mesh(
    ringGeometry.clone(),
    new THREE.MeshBasicMaterial({
      color: "#E7B58A",
      transparent: true,
      opacity: 0.65,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  group.add(hoverRing);
  nodeCount.value = nodesById.size;
  edgeCount.value = edges.length;
  labels();
  updateLines();
  fit();
  dirty = true;
}
function updateNode(node) {
  if (node.instance != null) {
    scratch.position.copy(node.position);
    scratch.rotation.set(0, 0, 0);
    scratch.scale.setScalar(node.data.id === 17255 ? 1.3 : 1);
    scratch.updateMatrix();
    node.object.setMatrixAt(node.instance, scratch.matrix);
    node.object.instanceMatrix.needsUpdate = true;
    node.object.setColorAt(
      node.instance,
      new THREE.Color(node.color).multiplyScalar(
        inWindow(node.data) ? 1 : 0.14,
      ),
    );
    node.object.instanceColor.needsUpdate = true;
  } else if (node.object) node.object.position.copy(node.position);
}
function curve(edge, t, out) {
  out.copy(edge.a.position).lerp(edge.b.position, t);
  out.z += edge.bend * Math.sin(t * Math.PI);
  return out;
}
function flowVisible(edge) {
  if (
    edge.data.type !== "genre-flow" ||
    props.flowDirection === "all" ||
    props.focusId == null
  )
    return true;
  return (
    (props.flowDirection === "in" ? edge.b.data.id : edge.a.data.id) ===
    props.focusId
  );
}
function flowColor(edge) {
  if (edge.data.type !== "genre-flow")
    return INFLUENCE_EDGE_TYPES.includes(edge.data.type)
      ? "#E7B58A"
      : "#6F93C0";
  return edge.a.data.id === props.focusId
    ? "#8FD7F8"
    : edge.b.data.id === props.focusId
      ? "#DFC180"
      : edge.a.color;
}
const tempA = new THREE.Vector3(),
  tempB = new THREE.Vector3(),
  tempC = new THREE.Vector3();
function updateLines() {
  if (!lineMesh) return;
  const positions = lineMesh.geometry.attributes.position.array,
    colors = lineMesh.geometry.attributes.color.array,
    focus = hoverId ?? props.focusId;
  edges.forEach((edge, index) => {
    const isFocused = edge.a.data.id === focus || edge.b.data.id === focus;
    const base = new THREE.Color(flowColor(edge));
    const strength = !flowVisible(edge)
      ? 0
      : !inWindow(edge.a.data) || !inWindow(edge.b.data)
        ? 0.025
        : isFocused
          ? 0.65
          : focus != null
            ? 0.035
            : 0.15;
    base.multiplyScalar(strength);
    for (let segment = 0; segment < 3; segment++) {
      curve(edge, segment / 3, tempA);
      curve(edge, (segment + 1) / 3, tempB);
      const offset = index * 18 + segment * 6;
      positions.set(
        [tempA.x, tempA.y, tempA.z, tempB.x, tempB.y, tempB.z],
        offset,
      );
      colors.set([base.r, base.g, base.b, base.r, base.g, base.b], offset);
    }
  });
  lineMesh.geometry.attributes.position.needsUpdate = true;
  lineMesh.geometry.attributes.color.needsUpdate = true;
  shownEdgeCount.value = edges.filter(flowVisible).length;
  for (const node of nodesById.values()) {
    if (!node.core) continue;
    const connected =
      focus == null ||
      node.data.id === focus ||
      (props.flowDirection === "all"
        ? neighbors.get(focus)?.has(node.data.id)
        : edges.some(
            (e) =>
              flowVisible(e) &&
              (e.a.data.id === node.data.id || e.b.data.id === node.data.id),
          ));
    node.core.material.color
      .set(node.color)
      .multiplyScalar(connected ? 0.34 : 0.12);
    node.core.material.emissiveIntensity = connected ? 0.09 : 0.025;
    if (node.icon) node.icon.material.opacity = connected ? 1 : 0.3;
  }
}
function fit() {
  if (!camera || !controls) return;
  const aspect = Math.max(0.4, width / height);
  const distance =
    props.nodes[0]?.type === "Genre"
      ? Math.max(930, 850 / aspect)
      : Math.max(
          540 / Math.tan(THREE.MathUtils.degToRad(25)) / 2,
          900 / aspect / Math.tan(THREE.MathUtils.degToRad(25)) / 2,
        ) * (width < 600 ? 1.26 : 1.2);
  initialDistance = distance;
  camera.position.set(0, 55, distance);
  controls.target.set(0, 0, 0);
  controls.update();
  zoomLabel.value = 100;
  dirty = true;
}
function reset() {
  interacted = false;
  for (const node of nodesById.values()) {
    node.position.copy(node.original);
    updateNode(node);
  }
  updateLines();
  fit();
}
function zoomBy(factor) {
  interacted = true;
  controls.autoRotate = false;
  camera.position
    .sub(controls.target)
    .multiplyScalar(1 / factor)
    .add(controls.target);
  controls.update();
  dirty = true;
}
function resize() {
  if (!renderer || !root.value) return;
  const r = root.value.getBoundingClientRect();
  width = Math.max(1, r.width);
  height = Math.max(1, r.height);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  if (group && !interacted) fit();
  dirty = true;
}
function ring(object, node, time) {
  object.visible = Boolean(node);
  if (!node) return;
  object.position.copy(node.position);
  object.quaternion.copy(camera.quaternion);
  const radius =
    node.radius * (node.genre ? 1.3 : 1.2) +
    (idleMotion.value ? Math.sin(time * 1.4) : 0);
  object.scale.setScalar(radius);
  object.material.color.set(node.color);
}
function updateLabels() {
  const boxes = [],
    ordered = [...labelItems.value].sort(
      (a, b) =>
        Number(b.id === props.focusId || b.id === hoverId) -
        Number(a.id === props.focusId || a.id === hoverId),
    );
  for (const item of ordered) {
    const element = labelElements.get(item.id),
      node = nodesById.get(item.id);
    if (!element || !node) continue;
    tempC.copy(node.position).project(camera);
    const x = (tempC.x * 0.5 + 0.5) * width,
      y = (-tempC.y * 0.5 + 0.5) * height,
      selected = item.id === props.focusId,
      hover = item.id === hoverId;
    element.dataset.centerX = x.toFixed(2);
    element.dataset.centerY = y.toFixed(2);
    tempA
      .copy(node.position)
      .addScaledVector(
        new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion),
        node.radius,
      );
    tempA.project(camera);
    const labelWidth = Math.min(190, item.name.length * 7.2 + 12),
      offset = Math.abs(tempA.x - tempC.x) * width * 0.5 + 7;
    let left = x + offset,
      top = y - 9;
    if (left + labelWidth > width - 10) left = x - offset - labelWidth;
    left = Math.max(8, left);
    const box = { x: left, y: top, w: labelWidth, h: 21 },
      collision = boxes.some(
        (b) =>
          box.x < b.x + b.w + 8 &&
          box.x + box.w + 8 > b.x &&
          box.y < b.y + b.h + 5 &&
          box.y + box.h + 5 > b.y,
      );
    const show =
      tempC.z < 1 &&
      tempC.z > 0 &&
      y > 40 &&
      y < height - 40 &&
      ((!collision && width >= 600) || selected || hover);
    element.style.visibility = show ? "visible" : "hidden";
    if (show) {
      boxes.push(box);
      element.style.transform = `translate3d(${left}px,${top}px,0)`;
      element.style.color =
        selected || hover
          ? "#f0f7ff"
          : neighbors.get(props.focusId)?.has(item.id)
            ? "#c3d6ed"
            : "#9eafc7";
      element.style.opacity =
        selected || hover || props.focusId == null ? "1" : ".76";
    }
  }
}
function animate(now) {
  if (disposed) return;
  frame = requestAnimationFrame(animate);
  if (!active || !visible || document.hidden || now - lastFrame < 40) return;
  lastFrame = now;
  if (!renderer || !scene) return;
  const idle = idleMotion.value;
  controls.autoRotate = idle && !interacted && props.nodes[0]?.type === "Genre";
  controls.update();
  if (!idle && !dirty) return;
  const time = now / 1000,
    focus = hoverId ?? props.focusId,
    selected = nodesById.get(props.focusId);
  if (starDust && idle) starDust.rotation.y = time * 0.006;
  if (particleMesh) particleMesh.visible = idle;
  if (particleMesh && idle) {
    const p = particleMesh.geometry.attributes.position.array,
      c = particleMesh.geometry.attributes.color.array;
    let count = 0;
    for (const edge of edges) {
      if (count >= 120) break;
      if (!flowVisible(edge)) continue;
      if (!inWindow(edge.a.data) || !inWindow(edge.b.data)) continue;
      if (focus != null && edge.a.data.id !== focus && edge.b.data.id !== focus)
        continue;
      if (
        !edge.data.type.includes("flow") &&
        !INFLUENCE_EDGE_TYPES.includes(edge.data.type) &&
        count % 3
      )
        continue;
      const color = new THREE.Color(flowColor(edge));
      for (let tail = 0; tail < 2 && count < 120; tail++) {
        const t = (time * 0.16 + edge.phase - tail * 0.025 + 100) % 1;
        curve(edge, t, tempA);
        p.set([tempA.x, tempA.y, tempA.z], count * 3);
        c.set(
          [
            color.r * (tail ? 0.4 : 1),
            color.g * (tail ? 0.4 : 1),
            color.b * (tail ? 0.4 : 1),
          ],
          count * 3,
        );
        count++;
      }
    }
    particleMesh.geometry.setDrawRange(0, count);
    particleMesh.geometry.attributes.position.needsUpdate = true;
    particleMesh.geometry.attributes.color.needsUpdate = true;
  }
  for (const node of nodesById.values()) {
    if (node.icon)
      node.icon.position
        .copy(camera.position)
        .sub(node.position)
        .normalize()
        .multiplyScalar(node.radius * 1.03);
  }
  ring(selectionRing, selected, time);
  ring(hoverRing, nodesById.get(hoverId), time);
  updateLabels();
  renderer.render(scene, camera);
  dirty = false;
}
function ray(event) {
  const r = canvas.value.getBoundingClientRect();
  pointer.set(
    ((event.clientX - r.left) / r.width) * 2 - 1,
    (-(event.clientY - r.top) / r.height) * 2 + 1,
  );
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(pickable, false);
  for (const hit of hits) {
    if (hit.instanceId != null)
      return nodesById.get(hit.object.userData.ids[hit.instanceId]);
    const id = hit.object.parent?.userData.nodeId;
    if (id != null) return nodesById.get(id);
  }
  return null;
}
function pointerDown(event) {
  if (!camera) return;
  interacted = true;
  controls.autoRotate = false;
  const node = ray(event);
  downPoint = { x: event.clientX, y: event.clientY };
  dragDistance = 0;
  if (node) {
    dragNode = node;
    controls.enabled = false;
    camera.getWorldDirection(tempA);
    dragPlane.setFromNormalAndCoplanarPoint(tempA, node.position);
    raycaster.ray.intersectPlane(dragPlane, dragPoint);
    dragOffset.copy(node.position).sub(dragPoint);
    canvas.value.setPointerCapture(event.pointerId);
    event.stopPropagation();
  }
}
function pointerMove(event) {
  if (!camera) return;
  const r = canvas.value.getBoundingClientRect();
  if (downPoint)
    dragDistance = Math.hypot(
      event.clientX - downPoint.x,
      event.clientY - downPoint.y,
    );
  const node = ray(event);
  if (dragNode) {
    if (raycaster.ray.intersectPlane(dragPlane, dragPoint)) {
      dragNode.position.copy(dragPoint).add(dragOffset);
      updateNode(dragNode);
      updateLines();
      dirty = true;
    }
    return;
  }
  if (node?.data.id !== hoverId) {
    hoverId = node?.data.id ?? null;
    hovered.value = node?.data ?? null;
    labels();
    updateLines();
    dirty = true;
    canvas.value.style.cursor = node ? "grab" : "grab";
  }
  tooltipPosition.value = {
    x: Math.max(12, Math.min(width - 230, event.clientX - r.left + 18)),
    y: Math.max(44, Math.min(height - 90, event.clientY - r.top - 35)),
  };
}
function pointerUp(event) {
  if (dragNode) {
    const node = dragNode;
    dragNode = null;
    controls.enabled = true;
    emit("select", node.data);
    event.stopPropagation();
  } else if (downPoint && dragDistance < 5) {
    emit("select", ray(event)?.data || null);
  }
  downPoint = null;
  dirty = true;
}
function pointerLeave() {
  if (dragNode) return;
  hoverId = null;
  hovered.value = null;
  updateLines();
  dirty = true;
}
function open(event) {
  const node = ray(event);
  if (node) emit("open", node.data);
}
function keyboard(event) {
  if (!camera) return;
  interacted = true;
  controls.autoRotate = false;
  const delta = new THREE.Vector3().subVectors(
    camera.position,
    controls.target,
  );
  if (event.key === "ArrowLeft")
    delta.applyAxisAngle(new THREE.Vector3(0, 1, 0), 0.12);
  else if (event.key === "ArrowRight")
    delta.applyAxisAngle(new THREE.Vector3(0, 1, 0), -0.12);
  else if (event.key === "+" || event.key === "=") delta.multiplyScalar(0.85);
  else if (event.key === "-") delta.multiplyScalar(1.15);
  else return;
  event.preventDefault();
  camera.position.copy(controls.target).add(delta);
  controls.update();
  dirty = true;
}
function exportImage() {
  renderer.render(scene, camera);
  const output = document.createElement("canvas"),
    source = renderer.domElement;
  output.width = source.width;
  output.height = source.height;
  const context = output.getContext("2d");
  context.drawImage(source, 0, 0);
  const scale = output.width / width,
    canvasBox = source.getBoundingClientRect();
  context.scale(scale, scale);
  context.font = '13px "Host Grotesk","Microsoft YaHei",sans-serif';
  context.textBaseline = "top";
  for (const item of labelItems.value) {
    const el = labelElements.get(item.id);
    if (el?.style.visibility !== "visible") continue;
    const rect = el.getBoundingClientRect();
    const x = rect.x - canvasBox.x,
      y = rect.y - canvasBox.y;
    context.fillStyle = "#0c1421dd";
    context.fillRect(x, y, rect.width, rect.height);
    context.fillStyle = el.style.color || "#dbe9fa";
    context.fillText(item.name, x + 5, y + 2);
  }
  const a = document.createElement("a");
  a.download = "OceanusPulse-3D-network.png";
  a.href = output.toDataURL("image/png");
  a.click();
}
onMounted(() => {
  try {
    renderer = new THREE.WebGLRenderer({
      canvas: canvas.value,
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
      powerPreference: "low-power",
    });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
    renderer.debug.onShaderError = () => {
      if (rendererFailed) return;
      rendererFailed = true;
      active = false;
      emit("unsupported");
    };
    renderer.setClearColor("#0C1421");
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.4;
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2("#0C1421", 0.0005);
    camera = new THREE.PerspectiveCamera(50, 1, 1, 4000);
    scene.add(new THREE.HemisphereLight("#B6D8FF", "#172438", 2));
    const key = new THREE.DirectionalLight("#D5E8FF", 3);
    key.position.set(-200, 400, 700);
    scene.add(key);
    const rim = new THREE.DirectionalLight("#E7B58A", 1.4);
    rim.position.set(400, -200, 300);
    scene.add(rim);
    controls = new OrbitControls(camera, canvas.value);
    controls.enableDamping = true;
    controls.dampingFactor = 0.075;
    controls.rotateSpeed = 0.6;
    controls.autoRotateSpeed = 0.26;
    controls.zoomSpeed = 0.75;
    controls.minDistance = 250;
    controls.maxDistance = 2000;
    controls.addEventListener("change", () => {
      dirty = true;
      zoomLabel.value = Math.round(
        (initialDistance / camera.position.distanceTo(controls.target)) * 100,
      );
    });
    pointTexture = glowTexture();
    resize();
    rebuild();
    observer = new ResizeObserver(resize);
    observer.observe(root.value);
    visibilityObserver = new IntersectionObserver(
      (entries) => {
        visible = entries[0].isIntersecting;
        dirty = true;
      },
      { threshold: 0 },
    );
    visibilityObserver.observe(root.value);
    frame = requestAnimationFrame(animate);
  } catch {
    emit("unsupported");
  }
});
watch(
  [
    () => props.nodes,
    () => props.links,
    () => props.visibleTypes,
    () => props.visibleEdgeTypes,
  ],
  () => {
    rebuild();
  },
  { deep: true },
);
watch(
  () => props.focusId,
  () => {
    labels();
    updateLines();
    dirty = true;
  },
);
watch(
  () => props.flowDirection,
  () => {
    updateLines();
    dirty = true;
  },
);
watch(
  () => props.yearRange,
  () => {
    for (const node of nodesById.values()) updateNode(node);
    updateLines();
    dirty = true;
  },
  { deep: true },
);
watch(
  idleMotion,
  () => {
    dirty = true;
  },
);
onActivated(() => {
  active = true;
  dirty = true;
  if (renderer) resize();
});
onDeactivated(() => {
  active = false;
});
onBeforeUnmount(() => {
  disposed = true;
  cancelAnimationFrame(frame);
  observer?.disconnect();
  visibilityObserver?.disconnect();
  controls?.dispose();
  if (group) disposeObject(group);
  for (const g of baseGeometry.values()) g.dispose();
  for (const t of textures.values()) t.dispose();
  pointTexture?.dispose();
  renderer?.dispose();
  renderer?.forceContextLoss();
});
</script>

<template>
  <div ref="root" class="network-canvas-root spatial-network" v-on="reading.events">
    <canvas
      ref="canvas"
      class="network-canvas"
      tabindex="0"
      role="img"
      :aria-label="`${label}。音乐主题的三维网络；拖空白旋转，拖节点调整位置，滚轮缩放。`"
      @pointerdown.capture="pointerDown"
      @pointermove="pointerMove"
      @pointerup.capture="pointerUp"
      @pointerleave="pointerLeave"
      @dblclick="open"
      @keydown="keyboard"
    />
    <div class="network-labels">
      <button
        v-for="item in labelItems"
        :key="item.id"
        :ref="
          (el) =>
            el ? labelElements.set(item.id, el) : labelElements.delete(item.id)
        "
        class="network-node-label"
        :aria-pressed="item.id === focusId"
        @click="emit('select', nodesById.get(item.id).data)"
        @dblclick="emit('open', nodesById.get(item.id).data)"
      >
        {{ item.name }}
      </button>
    </div>
    <div class="graph-context">
      <span class="graph-status"><i />{{ label }}</span
      ><span
        >{{ nodeCount }} 个实体 ·
        {{ flowDirection === "all" ? edgeCount : shownEdgeCount }} 条{{
          flowDirection === "all"
            ? "联系"
            : flowDirection === "in"
              ? "流入路径"
              : "流出路径"
        }}</span
      >
    </div>
    <div v-if="hovered" class="canvas-tooltip" :style="tooltipStyle">
      <i
        :style="{ background: hovered.color || NODE_COLORS[hovered.type] }"
      /><strong>{{ hovered.display_name || hovered.name }}</strong
      ><span
        >{{
          hovered.type === "Genre"
            ? `${hovered.value} 部作品 · 双击进入传播分析`
            : NODE_LABELS[hovered.type]
        }}<br />按住节点可拖动 · 拖空白处旋转</span
      >
    </div>
    <div class="graph-bottom">
      <span class="graph-gesture">拖空白旋转 · 拖节点布局 · 滚轮缩放</span>
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
          aria-label="重置图谱布局和视角"
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
