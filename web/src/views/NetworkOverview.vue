<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { dataService } from "../lib/dataService";
import { useAppStore } from "../stores/useAppStore";
import {
  NODE_COLORS,
  NODE_LABELS,
  GENRE_PALETTE,
  formatCount,
} from "../lib/palette";
import NetworkCanvas from "../components/NetworkCanvas.vue";
import AppIcon from "../components/AppIcon.vue";
import { genreIcons } from "../lib/genre-icons";
import { genreIconNames } from "../lib/genre-icon-map";

const store = useAppStore(),
  loading = ref(true),
  error = ref(""),
  overview = ref(null),
  entities = ref(null),
  flows = ref(null);
const mode = ref("genres"),
  genreGraph = ref({ nodes: [], links: [] }),
  selected = ref(null),
  search = ref("");
const entityTypes = ref(Object.keys(NODE_COLORS));
const flowDirection = ref("all");
onMounted(async () => {
  try {
    const [o, n, f] = await Promise.all([
      dataService.overview(),
      dataService.network(),
      dataService.genreFlows(),
    ]);
    overview.value = o;
    entities.value = n;
    flows.value = f;
    const nodes = Object.entries(o.genre_work_counts).map(
      ([name, value], index) => ({
        id: name,
        name,
        type: "Genre",
        value,
        color: GENRE_PALETTE[index % GENRE_PALETTE.length],
        radius: 7 + Math.sqrt(value) * 0.32,
      }),
    );
    const byPair = new Map();
    for (const f of flows.value.flows) {
      if (f.source === f.target || f.year == null) continue;
      const key = `${f.source}|${f.target}`;
      byPair.set(key, (byPair.get(key) || 0) + f.value);
    }
    const links = [...byPair].map(([key, value]) => {
      const [source, target] = key.split("|");
      return { id: key, source, target, value, type: "genre-flow" };
    });
    // A deterministic volumetric layout; position is spatial navigation, not an analytical metric.
    const strength = new Map(nodes.map((n) => [n.id, 0]));
    for (const link of links) {
      if (link.source === "Oceanus Folk")
        strength.set(link.target, strength.get(link.target) + link.value);
      if (link.target === "Oceanus Folk")
        strength.set(link.source, strength.get(link.source) + link.value);
    }
    const around = nodes
      .filter((n) => n.id !== "Oceanus Folk")
      .sort(
        (a, b) =>
          strength.get(b.id) - strength.get(a.id) ||
          a.name.localeCompare(b.name),
      );
    around.forEach((node, index) => {
      const phi = Math.acos(1 - (2 * (index + 0.5)) / around.length);
      const theta = index * Math.PI * (3 - Math.sqrt(5));
      const radius = 290 + Math.sin(index * 2.1) * 28;
      node.x = radius * Math.sin(phi) * Math.cos(theta);
      node.y = radius * Math.cos(phi);
      node.z = radius * Math.sin(phi) * Math.sin(theta);
    });
    const focal = nodes.find((n) => n.id === "Oceanus Folk");
    focal.x = 0;
    focal.y = 0;
    focal.z = 0;
    focal.color = "#8FD7F8";
    genreGraph.value = { nodes, links };
    selected.value = nodes.find((n) => n.id === "Oceanus Folk");
  } catch (cause) {
    error.value = `全景数据加载失败：${cause.message}`;
  } finally {
    loading.value = false;
    await nextTick();
    document.documentElement.dataset.ready = "1";
  }
});
const graph = computed(() =>
  mode.value === "genres"
    ? genreGraph.value
    : entities.value || { nodes: [], links: [] },
);
const selectedColor = computed(
  () => selected.value?.color || NODE_COLORS[selected.value?.type] || "#8FD7F8",
);
const selectedEdges = computed(() =>
  graph.value.links.filter(
    (l) =>
      (l.source?.id ?? l.source) === selected.value?.id ||
      (l.target?.id ?? l.target) === selected.value?.id,
  ),
);
const incoming = computed(() =>
  genreGraph.value.links
    .filter((l) => l.target === selected.value?.id)
    .reduce((s, l) => s + l.value, 0),
);
const outgoing = computed(() =>
  genreGraph.value.links
    .filter((l) => l.source === selected.value?.id)
    .reduce((s, l) => s + l.value, 0),
);
const strongestSource = computed(
  () =>
    genreGraph.value.links
      .filter((l) => l.target === selected.value?.id)
      .sort((a, b) => b.value - a.value)[0],
);
const strongestTarget = computed(
  () =>
    genreGraph.value.links
      .filter((l) => l.source === selected.value?.id)
      .sort((a, b) => b.value - a.value)[0],
);
const flowDirections = [
  { key: "all", label: "全部路径" },
  { key: "in", label: "灵感流入", color: "#dfc180" },
  { key: "out", label: "影响流出", color: "#8fd7f8" },
];
const searchResults = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return [];
  return [...genreGraph.value.nodes, ...(entities.value?.nodes || [])]
    .filter((n) => (n.display_name || n.name).toLowerCase().includes(q))
    .slice(0, 7);
});
function select(node) {
  selected.value = node;
}
function switchMode(value) {
  mode.value = value;
  search.value = "";
  selected.value =
    value === "genres"
      ? genreGraph.value.nodes.find((n) => n.id === "Oceanus Folk")
      : entities.value.nodes.find((n) => n.id === 17255);
}
function pickSearch(node) {
  mode.value = node.type === "Genre" ? "genres" : "entities";
  if (node.type !== "Genre" && !entityTypes.value.includes(node.type))
    entityTypes.value = [...entityTypes.value, node.type];
  selected.value = node;
  search.value = "";
}
function openNode(node) {
  if (!node) return;
  if (node.type === "Genre") {
    store.focusGenres = [node.name];
    store.setModule("genre");
  } else {
    store.selectNode(
      node.id === 17255 ? { ...node, genre: "Oceanus Folk" } : node,
    );
    store.setModule("influence");
  }
}
function toggleType(type) {
  entityTypes.value = entityTypes.value.includes(type)
    ? entityTypes.value.filter((t) => t !== type)
    : [...entityTypes.value, type];
}
</script>

<template>
  <div
    v-if="loading || error"
    class="op-state"
    :class="{ error }"
    role="status"
  >
    {{ error || "正在构建音乐生态关系网…" }}
  </div>
  <section v-else id="overview" class="analysis-screen overview-screen hero">
    <div class="wrap">
      <div class="analysis-head">
        <div>
          <h1>
            音乐生态全景<span class="title-english">Connected by music</span>
          </h1>
        </div>
        <div class="data-overview">
          <div>
            <strong>{{ formatCount(overview.counts.nodes) }}</strong
            ><span>音乐实体</span>
          </div>
          <div>
            <strong>{{ formatCount(overview.counts.links) }}</strong
            ><span>原始关系</span>
          </div>
          <div>
            <strong>{{ genreGraph.nodes.length }}</strong
            ><span>音乐流派</span>
          </div>
        </div>
      </div>
      <div class="app-frame overview-workspace">
        <div class="overview-graph-panel">
          <div class="graph-toolbar">
            <div class="segmented-control" aria-label="全景图谱类型">
              <button
                class="op-chip"
                :class="{ on: mode === 'genres' }"
                :aria-pressed="mode === 'genres'"
                @click="switchMode('genres')"
              >
                流派关系网</button
              ><button
                class="op-chip"
                :class="{ on: mode === 'entities' }"
                :aria-pressed="mode === 'entities'"
                @click="switchMode('entities')"
              >
                音乐实体网
              </button>
            </div>
            <div class="entity-search overview-search">
              <AppIcon name="search" :size="16" class="search-icon" /><input
                v-model="search"
                class="search-input"
                aria-label="搜索全景图中的流派或实体"
                placeholder="搜索流派、音乐人、作品…"
                autocomplete="off"
                @keydown.enter.prevent="
                  searchResults[0] && pickSearch(searchResults[0])
                "
                @keydown.esc="search = ''"
              />
              <div v-if="search.trim()" class="search-results">
                <button
                  v-for="node in searchResults"
                  :key="node.id"
                  @click="pickSearch(node)"
                >
                  {{ node.display_name || node.name
                  }}<small>{{
                    node.type === "Genre" ? "流派" : NODE_LABELS[node.type]
                  }}</small>
                </button>
                <p v-if="!searchResults.length" class="search-empty">
                  当前概览中没有匹配的实体
                </p>
              </div>
            </div>
          </div>
          <div class="network-stage">
            <NetworkCanvas
              :nodes="graph.nodes"
              :links="graph.links"
              :visible-types="mode === 'entities' ? entityTypes : null"
              :focus-id="selected?.id ?? null"
              :flow-direction="mode === 'genres' ? flowDirection : 'all'"
              :label="
                mode === 'genres'
                  ? '音乐流派 · 全期影响网络'
                  : '音乐实体 · 有界概览网络'
              "
              @select="select"
              @open="openNode"
            />
          </div>
          <div class="overview-legend">
            <template v-if="mode === 'genres'"
              ><span><i style="background: #8fd7f8" />流派节点</span>
              <div
                class="flow-directions"
                role="group"
                aria-label="选择流派影响方向"
              >
                <button
                  v-for="direction in flowDirections"
                  :key="direction.key"
                  :aria-pressed="flowDirection === direction.key"
                  :class="{ on: flowDirection === direction.key }"
                  @click="flowDirection = direction.key"
                >
                  <i
                    v-if="direction.color"
                    class="line"
                    :style="{ background: direction.color }"
                  />{{ direction.label }}
                </button>
              </div>
              <span class="legend-explanation">大小表示作品数量</span></template
            ><template v-else
              ><button
                v-for="(color, type) in NODE_COLORS"
                :key="type"
                :class="{ off: !entityTypes.includes(type) }"
                :aria-pressed="entityTypes.includes(type)"
                @click="toggleType(type)"
              >
                <i :style="{ background: color }" />{{ NODE_LABELS[type] }}
              </button></template
            >
          </div>
        </div>
        <aside class="overview-inspector" aria-live="polite">
          <div class="inspector-label">
            <span>图谱导航</span
            ><span class="inspector-index">{{
              mode === "genres" ? "01 / 流派" : "02 / 实体"
            }}</span>
          </div>
          <template v-if="selected"
            ><div
              class="inspector-orbit"
              :style="{ '--node-color': selectedColor }"
            >
              <span
                class="inspector-topic-icon"
                v-html="
                  genreIcons[genreIconNames[selected.name]] ||
                  genreIcons['music-2']
                "
              /><i /><b />
            </div>
            <span class="entity-kind"
              ><i :style="{ background: selectedColor }" />{{
                selected.type === "Genre"
                  ? "音乐流派"
                  : NODE_LABELS[selected.type]
              }}</span
            >
            <h2 class="overview-node-title">
              {{ selected.display_name || selected.name }}
            </h2>
            <p class="overview-node-copy">
              {{
                selected.type === "Genre"
                  ? strongestSource && strongestTarget
                    ? `主要灵感来源为 ${strongestSource.source}；主要影响去向为 ${strongestTarget.target}。`
                    : "沿着流入与流出的路径，查看灵感来源与传播证据。"
                  : "进入关系网络，查看该实体的作品、相邻关系与图谱档案。"
              }}
            </p>
            <div class="overview-node-metrics" v-if="selected.type === 'Genre'">
              <div>
                <strong>{{ formatCount(selected.value) }}</strong
                ><span>该流派作品</span>
              </div>
              <div>
                <strong>{{ selectedEdges.length }}</strong
                ><span>跨流派关系</span>
              </div>
            </div>
            <dl class="entity-facts" v-if="selected.type === 'Genre'">
              <div>
                <dt>流入影响事件</dt>
                <dd>{{ formatCount(incoming) }}</dd>
              </div>
              <div>
                <dt>流出影响事件</dt>
                <dd>{{ formatCount(outgoing) }}</dd>
              </div>
              <div>
                <dt>观测窗口</dt>
                <dd>1975—2040</dd>
              </div>
            </dl>
            <dl class="entity-facts" v-else>
              <div>
                <dt>实体编号</dt>
                <dd>#{{ selected.id }}</dd>
              </div>
              <div>
                <dt>概览内关系</dt>
                <dd>{{ selectedEdges.length }}</dd>
              </div>
              <div v-if="selected.genre">
                <dt>所属流派</dt>
                <dd>{{ selected.genre }}</dd>
              </div>
              <div>
                <dt>已知发行年</dt>
                <dd>{{ selected.release_year ?? "未知" }}</dd>
              </div>
            </dl>
            <button
              class="btn btn--primary overview-open"
              @click="openNode(selected)"
            >
              {{ selected.type === "Genre" ? "进入传播分析" : "进入关系分析"
              }}<AppIcon name="arrow" :size="16" /></button></template
          ><template v-else
            ><div class="inspector-orbit"><span /><i /></div>
            <h2 class="overview-node-title">选择你的分析线索</h2>
            <p class="overview-node-copy">
              悬停读取名称，点击选择实体；双击节点或使用下方入口进入分析。
            </p></template
          >
          <div class="overview-next">
            <span class="field-label">继续研究</span
            ><button @click="store.setModule('rising')">
              <AppIcon name="star" :size="16" /><span>谁会是下一位新星</span
              ><AppIcon name="arrow" :size="15" />
            </button>
          </div>
          <p class="overview-scope">
            {{
              mode === "genres"
                ? "流派按有日期的跨流派音乐影响聚合；空间距离仅用于布局，不表示相似性。"
                : "概览展示 600 个有界实体，优先包含 Sailor 邻域和高连接实体，并非全图的代表性抽样。"
            }}
          </p>
        </aside>
      </div>
      <div class="overview-mobile-selection" v-if="selected">
        <span>{{ selected.display_name || selected.name }}</span
        ><button class="section-link" @click="openNode(selected)">
          {{ selected.type === "Genre" ? "进入传播分析" : "进入关系分析"
          }}<AppIcon name="arrow" :size="14" />
        </button>
      </div>
      <div class="workspace-footline">
        <span><i class="legend-line" />关系流光表示方向，不代表传播速度</span
        ><span>单击选择 · 双击进入分析 · 可导出图谱</span>
      </div>
    </div>
  </section>
</template>
