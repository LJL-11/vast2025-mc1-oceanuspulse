<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { dataService, friendlyDataError } from "../lib/dataService";
import { useAppStore } from "../stores/useAppStore";
import ForceGraph from "../components/ForceGraph.vue";
import NetworkCanvas from "../components/NetworkCanvas.vue";
import TimeScrubber from "../components/TimeScrubber.vue";
import FilterPanel from "../components/FilterPanel.vue";
import DetailCard from "../components/DetailCard.vue";
import ChartPanel from "../components/ChartPanel.vue";
import AppIcon from "../components/AppIcon.vue";
import { scrollToSection } from "../lib/navigation";
import {
  NODE_COLORS,
  NODE_LABELS,
  CREDIT_EDGE_TYPES,
  INFLUENCE_EDGE_TYPES,
  CHART_MUTED,
  CHART_GRID,
  formatCount,
} from "../lib/palette";
const store = useAppStore();
const loading = ref(true),
  error = ref(""),
  overview = ref(null),
  ego = ref(null),
  sailor = ref(null);
const search = ref(""),
  edgeMode = ref("all"),
  selectedPath = ref(null);
const evidenceSection = ref(null);
const overviewGraph = ref(null),
  graphMode = ref("spatial");
const activeGraph = computed(() =>
  store.focusNode &&
  !ego.value?.nodes.some((n) => n.id === store.focusNode.id) &&
  overviewGraph.value
    ? overviewGraph.value
    : ego.value,
);
onMounted(async () => {
  try {
    const [o, g, s, n] = await Promise.all([
      dataService.overview(),
      dataService.sailorEgo(),
      dataService.sailor(),
      dataService.network(),
    ]);
    overviewGraph.value = n;
    overview.value = o;
    ego.value = g;
    sailor.value = s;
    if (!store.focusNode)
      store.selectNode({
        ...g.nodes.find((n) => n.id === 17255),
        genre: "Oceanus Folk",
      });
  } catch (cause) {
    error.value = friendlyDataError(cause);
  } finally {
    loading.value = false;
    await nextTick();
    document.documentElement.dataset.ready = "1";
  }
});
const typeOptions = Object.keys(NODE_COLORS).map((type) => ({
  value: type,
  label: NODE_LABELS[type]
    .replace("艺人 / 创作者", "艺人")
    .replace("乐队 / 组合", "乐队")
    .replace("唱片厂牌", "厂牌"),
  color: NODE_COLORS[type],
}));
const edgeModes = [
  { key: "all", label: "全部关系" },
  { key: "credit", label: "作品署名" },
  { key: "influence", label: "音乐影响" },
];
const visibleTypes = computed({
  get: () => store.visibleTypes,
  set: (value) => {
    store.visibleTypes = value;
  },
});
const yearRange = computed({
  get: () => store.yearRange,
  set: (value) => store.setYearRange(value),
});
const visibleEdgeTypes = computed(() =>
  edgeMode.value === "influence"
    ? INFLUENCE_EDGE_TYPES
    : edgeMode.value === "credit"
      ? CREDIT_EDGE_TYPES
      : [...CREDIT_EDGE_TYPES, ...INFLUENCE_EDGE_TYPES],
);
const nodeById = computed(
  () =>
    new Map((activeGraph.value?.nodes || []).map((node) => [node.id, node])),
);
const focusId = computed(() => store.focusNode?.id ?? null);
const focusLinks = computed(() =>
  (activeGraph.value?.links || []).filter(
    (l) => l.source === focusId.value || l.target === focusId.value,
  ),
);
const focusLinkTypes = computed(() => {
  const counts = new Map();
  for (const link of focusLinks.value)
    counts.set(link.type, (counts.get(link.type) || 0) + 1);
  return [...counts]
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count);
});
const works = computed(() =>
  (sailor.value?.works || [])
    .map((work) => ({ ...work, node: nodeById.value.get(work.id) }))
    .filter((work) => work.node && work.node.release_year),
);
const careerYears = computed(() => {
  const years = works.value.map((w) => w.node.release_year);
  return years.length
    ? Array.from(
        { length: Math.max(...years) - Math.min(...years) + 1 },
        (_, i) => Math.min(...years) + i,
      )
    : [];
});
const careerOption = computed(() => {
  const perYear = careerYears.value.map(
    (year) => works.value.filter((w) => w.node.release_year === year).length,
  );
  let count = 0;
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 16, top: 16, bottom: 28 },
    xAxis: {
      type: "category",
      data: careerYears.value,
      boundaryGap: false,
      axisLabel: { color: CHART_MUTED, fontSize: 12 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } },
      axisLabel: { color: CHART_MUTED, fontSize: 12 },
    },
    series: [
      {
        name: "累计署名作品",
        type: "line",
        smooth: 0.3,
        showSymbol: false,
        lineStyle: { width: 2, color: "#8fd7f8" },
        itemStyle: { color: "#8fd7f8" },
        areaStyle: { color: "#8fd7f8", opacity: 0.06 },
        data: perYear.map((n) => (count += n)),
      },
      {
        name: "当年新作",
        type: "scatter",
        symbolSize: 6,
        itemStyle: { color: "#e7b58a" },
        data: perYear,
      },
    ],
  };
});
function onCareerClick(params) {
  const year = careerYears.value[params.dataIndex];
  if (year) store.setYearRange([year, year]);
}
const topCollaborators = computed(() =>
  (sailor.value?.collaborators || []).slice(0, 12),
);
const maxShared = computed(() =>
  Math.max(1, ...topCollaborators.value.map((item) => item.shared_work_count)),
);
const upstreamPaths = computed(() =>
  (sailor.value?.upstream_paths || []).slice(0, 12),
);
const searchResults = computed(() => {
  const query = search.value.trim().toLowerCase();
  return query
    ? (overviewGraph.value?.nodes || ego.value?.nodes || [])
        .filter((n) => (n.display_name || n.name).toLowerCase().includes(query))
        .slice(0, 8)
    : [];
});
function selectNode(node) {
  if (!node) return store.clearFocus();
  store.selectNode(
    node.id === 17255 ? { ...node, genre: "Oceanus Folk" } : node,
  );
}
function pickCollaborator(item) {
  selectNode(
    nodeById.value.get(item.id) || {
      id: item.id,
      name: item.name,
      type: "Person",
    },
  );
}
function pathLabel(path) {
  return path.node_path
    .toReversed()
    .map((id) => {
      const n = nodeById.value.get(id);
      return n?.display_name || n?.name || `#${id}`;
    })
    .join(" → ");
}
function pickPath(path) {
  selectedPath.value = selectedPath.value?.id === path.id ? null : path;
  const node = nodeById.value.get(path.node_path.at(-1));
  if (node) selectNode(node);
}
function pickSearchResult(node) {
  selectNode(node);
  search.value = "";
}
function reloadPage() {
  window.location.reload();
}
function showEvidence() {
  scrollToSection(evidenceSection.value);
}
</script>

<template>
  <div
    v-if="loading || error"
    class="op-state"
    :class="{ error }"
    role="status"
  >
    {{ error || "正在加载音乐关系图谱…"
    }}<button v-if="error" class="btn btn--secondary" @click="reloadPage">
      重新加载数据
    </button>
  </div>
  <template v-else>
    <section id="influence" class="analysis-screen hero hero--triptych">
      <div class="wrap">
        <div class="analysis-head">
          <div>
            <h1>
              音乐影响力可视分析<span class="title-english"
                >Influence atlas</span
              >
            </h1>
            <p class="head-description">
              从一位音乐人出发，追溯创作、合作与灵感的来处。
            </p>
          </div>
          <div class="data-overview">
            <div>
              <strong>{{ formatCount(overview.counts.nodes) }}</strong
              ><span>图谱实体</span>
            </div>
            <div>
              <strong>{{ formatCount(overview.counts.links) }}</strong
              ><span>关联关系</span>
            </div>
            <div><strong>1975—2040</strong><span>全图观测年份</span></div>
          </div>
        </div>
        <div
          class="app-frame network-workspace"
          aria-label="音乐影响力分析工作台"
        >
          <div class="graph-panel">
            <div class="graph-toolbar">
              <FilterPanel
                v-model="visibleTypes"
                class="entity-type-filter"
                label="实体类型"
                :options="typeOptions"
              />
              <div
                class="segmented-control graph-mode-control"
                aria-label="图谱空间模式"
              >
                <button
                  class="op-chip"
                  :class="{ on: graphMode === 'spatial' }"
                  :aria-pressed="graphMode === 'spatial'"
                  @click="graphMode = 'spatial'"
                >
                  空间图</button
                ><button
                  class="op-chip"
                  :class="{ on: graphMode === 'flat' }"
                  :aria-pressed="graphMode === 'flat'"
                  @click="graphMode = 'flat'"
                >
                  平面图
                </button>
              </div>
              <div class="segmented-control" aria-label="图谱关系筛选">
                <button
                  v-for="mode in edgeModes"
                  :key="mode.key"
                  class="op-chip"
                  :class="{ on: edgeMode === mode.key }"
                  :aria-pressed="edgeMode === mode.key"
                  @click="edgeMode = mode.key"
                >
                  {{ mode.label }}
                </button>
              </div>
            </div>
            <div class="network-stage">
              <NetworkCanvas
                v-if="graphMode === 'spatial'"
                :nodes="activeGraph.nodes"
                :links="activeGraph.links"
                :visible-types="visibleTypes"
                :visible-edge-types="visibleEdgeTypes"
                :year-range="yearRange"
                :focus-id="focusId"
                :label="
                  activeGraph === ego
                    ? 'Sailor Shift · 两跳影响网络'
                    : '实体概览网络 · 600 个有界实体'
                "
                @select="selectNode"
                @open="(node) => node.genre && store.focusGenre(node.genre)"
              /><ForceGraph
                v-else
                :nodes="activeGraph.nodes"
                :links="activeGraph.links"
                :visible-types="visibleTypes"
                :visible-edge-types="visibleEdgeTypes"
                :year-range="yearRange"
                :focus-id="focusId"
                @select="selectNode"
              />
            </div>
            <div class="graph-footer">
              <TimeScrubber v-model="yearRange" />
              <div class="entity-search">
                <AppIcon name="search" :size="16" class="search-icon" /><input
                  v-model="search"
                  class="search-input"
                  type="search"
                  placeholder="搜索音乐人、作品…"
                  aria-label="搜索关系图中的实体"
                  autocomplete="off"
                  @keydown.enter.prevent="
                    searchResults[0] && pickSearchResult(searchResults[0])
                  "
                  @keydown.esc="search = ''"
                />
                <div
                  v-if="search.trim()"
                  class="search-results"
                  aria-label="实体搜索结果"
                >
                  <button
                    v-for="node in searchResults"
                    :key="node.id"
                    @click="pickSearchResult(node)"
                  >
                    {{ node.display_name || node.name }}
                  </button>
                  <div v-if="!searchResults.length" class="search-empty">
                    当前两跳图中没有匹配的实体
                  </div>
                </div>
              </div>
            </div>
          </div>
          <DetailCard
            :node="store.focusNode"
            :degree="focusLinks.length"
            :link-types="focusLinkTypes"
            @close="store.clearFocus()"
            @jump="store.focusGenre"
          />
        </div>
        <div class="workspace-footline">
          <span
            ><i class="legend-line" />音乐影响
            <span class="muted">来源 → 受影响者</span
            ><i class="legend-line credit" />作品署名 / 录制 / 成员</span
          ><button class="section-link" @click="showEvidence">
            查看创作轨迹与证据
            <AppIcon name="arrow" :size="14" class="down-arrow" />
          </button>
        </div>
      </div>
    </section>
    <section
      id="influence-evidence"
      ref="evidenceSection"
      class="analysis-evidence"
    >
      <div class="wrap">
        <div class="section-heading">
          <div>
            <h2>创作轨迹与影响证据</h2>
            <p>
              {{ works.length }} 部署名作品，{{ sailor.collaborators.length }}
              位共同署名合作者。每一次连接，都能回到原始关系。
            </p>
          </div>
          <button
            class="section-link"
            @click="store.focusGenre('Oceanus Folk')"
          >
            查看传播流向 <AppIcon name="arrow" :size="16" />
          </button>
        </div>
        <DetailCard
          class="mobile-dossier"
          :node="store.focusNode"
          :degree="focusLinks.length"
          :link-types="focusLinkTypes"
          @close="store.clearFocus()"
          @jump="store.focusGenre"
        />
        <div class="evidence-top">
          <article class="op-card">
            <header>
              <h3>Sailor Shift 的创作轨迹</h3>
              <p>累计作品与当年新作 · 点击锁定年份</p>
            </header>
            <ChartPanel
              :option="careerOption"
              height="188px"
              label="Sailor Shift 逐年累计作品和当年新作"
              @chart-click="onCareerClick"
            />
          </article>
          <article class="op-card">
            <header>
              <h3>共同署名合作者</h3>
              <p>Top 12 · 点击聚焦实体</p>
            </header>
            <div class="collaborator-list">
              <button
                v-for="item in topCollaborators"
                :key="item.id"
                class="op-bar-row"
                @click="pickCollaborator(item)"
              >
                <span class="op-bar-name" :title="item.name">{{
                  item.name
                }}</span
                ><span class="op-bar-track"
                  ><span
                    class="op-bar-fill"
                    :style="{
                      display: 'block',
                      width: `${(item.shared_work_count / maxShared) * 100}%`,
                    }" /></span
                ><span class="op-bar-value">{{ item.shared_work_count }}</span>
              </button>
            </div>
          </article>
        </div>
        <article class="op-card evidence-panel">
          <header>
            <h3>可回溯的上游影响路径</h3>
            <p>最多三跳 · 点击路径读取原始边 ID</p>
          </header>
          <div class="op-scroll">
            <table class="op-table">
              <thead>
                <tr>
                  <th>来源实体链路</th>
                  <th class="num">跳数</th>
                  <th class="num">事件年份</th>
                  <th>日期记录</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="path in upstreamPaths" :key="path.id"
                  ><tr data-interactive @click="pickPath(path)">
                    <td>
                      <button
                        class="table-path"
                        :aria-expanded="selectedPath?.id === path.id"
                        @click.stop="pickPath(path)"
                      >
                        {{ pathLabel(path) }}
                      </button>
                    </td>
                    <td class="num">{{ path.hops }}</td>
                    <td class="num">
                      {{
                        path.event_years.filter(Boolean).join(", ") || "未知"
                      }}
                    </td>
                    <td>
                      <span class="op-tag">{{
                        path.fully_dated ? "完整" : "缺失日期"
                      }}</span>
                    </td>
                  </tr>
                  <tr v-if="selectedPath?.id === path.id">
                    <td colspan="4" class="path-proof">
                      原始关系 ID：{{ path.event_ids.join(" / ") }}
                    </td>
                  </tr></template
                >
              </tbody>
            </table>
          </div>
        </article>
        <details class="method-note">
          <summary>
            <AppIcon name="info" :size="14" /> 数据口径与分析边界
          </summary>
          <p>
            音乐影响按「来源 → 受影响者」定向。共同署名只表示参与同一作品。{{
              sailor.directly_influenced.length
            }}
            条下游影响引用均无日期，不能用来推断逐年增长；缺失登榜年份保持未知。全图
            {{ formatCount(overview.chart_status.notable_without_year) }} 部
            notable 作品缺失登榜年份；notable 仅表示上过热榜。
          </p>
        </details>
      </div>
    </section>
  </template>
</template>
