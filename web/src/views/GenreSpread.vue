<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { dataService, friendlyDataError } from "../lib/dataService";
import { useAppStore } from "../stores/useAppStore";
import ChartPanel from "../components/ChartPanel.vue";
import TimeScrubber from "../components/TimeScrubber.vue";
import FilterPanel from "../components/FilterPanel.vue";
import AppIcon from "../components/AppIcon.vue";
import { scrollToSection } from "../lib/navigation";
import {
  FLOW_TYPES,
  FLOW_COLORS,
  EDGE_LABELS,
  genreColor,
  CHART_MUTED,
  CHART_GRID,
  formatCount,
} from "../lib/palette";

const store = useAppStore();
const loading = ref(true);
const error = ref("");
const trends = ref(null);
const flows = ref(null);
const events = ref(null);
const overview = ref(null);
const selectedCell = ref(null);
const selectedYear = ref(null);
const visual = ref("flow");

onMounted(async () => {
  try {
    const [t, f, e, o] = await Promise.all([
      dataService.genreTrends(),
      dataService.genreFlows(),
      dataService.influenceEvents(),
      dataService.overview(),
    ]);
    trends.value = t;
    flows.value = f;
    events.value = e;
    overview.value = o;
  } catch (cause) {
    error.value = friendlyDataError(cause);
  } finally {
    loading.value = false;
    await nextTick();
    document.documentElement.dataset.ready = "1";
  }
});

const metricOptions = [
  { value: "outbound_events", label: "外向影响事件" },
  { value: "inbound_events", label: "内向吸收事件" },
  { value: "outbound_trailing_5y_mean", label: "5 年滚动均值" },
  { value: "external_work_coverage", label: "受影响作品覆盖率" },
];
const flowTypeOptions = FLOW_TYPES.map((type) => ({
  value: type,
  label: EDGE_LABELS[type],
  color: FLOW_COLORS[type],
}));
const metric = computed({
  get: () => store.trendMetric,
  set: (value) => {
    store.trendMetric = value;
  },
});
const yearRange = computed({
  get: () => store.yearRange,
  set: (value) => store.setYearRange(value),
});
const focusGenres = computed({
  get: () => store.focusGenres,
  set: (value) => {
    store.focusGenres = value;
  },
});
const visibleFlowTypes = computed({
  get: () => store.visibleFlowTypes,
  set: (value) => {
    store.visibleFlowTypes = value;
  },
});

const allGenres = computed(() => trends.value?.genres || []);
const genreOptions = computed(() => {
  const totals = new Map();
  for (const flow of flows.value?.flows || []) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value);
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value);
  }
  const ranked = [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .map((entry) => entry[0]);
  const head = [
    "Oceanus Folk",
    ...ranked.filter((name) => name !== "Oceanus Folk"),
  ].slice(0, 12);
  return [...new Set([...head, ...focusGenres.value])].map((name) => ({
    value: name,
    label: name,
  }));
});
function addGenre(event) {
  const value = event.target.value;
  if (value && !focusGenres.value.includes(value))
    focusGenres.value = [...focusGenres.value, value];
  event.target.value = "";
}

const rowsInWindow = computed(() =>
  (trends.value?.rows || []).filter(
    (row) => row.year >= yearRange.value[0] && row.year <= yearRange.value[1],
  ),
);
const chartYears = computed(() =>
  [...new Set(rowsInWindow.value.map((row) => row.year))].sort((a, b) => a - b),
);
const rowLookup = computed(
  () =>
    new Map(rowsInWindow.value.map((row) => [`${row.genre}|${row.year}`, row])),
);
const isRatio = computed(() => metric.value === "external_work_coverage");

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: {
    type: "scroll",
    top: 0,
    textStyle: { fontSize: 11, color: CHART_MUTED },
  },
  grid: { left: 52, right: 20, top: 34, bottom: 30 },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: chartYears.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    axisLine: { lineStyle: { color: CHART_GRID } },
  },
  yAxis: {
    type: "value",
    name: isRatio.value ? "覆盖率" : "事件数",
    nameTextStyle: { fontSize: 10, color: CHART_MUTED },
    axisLabel: {
      fontSize: 10,
      color: CHART_MUTED,
      formatter: (value) =>
        isRatio.value ? `${(value * 100).toFixed(0)}%` : value,
    },
    splitLine: { lineStyle: { color: CHART_GRID } },
  },
  series: focusGenres.value.map((genre, index) => ({
    name: genre,
    type: "line",
    smooth: true,
    showSymbol: false,
    lineStyle: { width: index === 0 ? 2.8 : 1.7, color: genreColor(index) },
    itemStyle: { color: genreColor(index) },
    areaStyle: index === 0 ? { color: "rgba(232,115,74,0.10)" } : undefined,
    data: chartYears.value.map(
      (year) =>
        rowLookup.value.get(`${genre}|${year}`)?.[metric.value] ??
        (isRatio.value ? null : 0),
    ),
  })),
}));

const filteredFlows = computed(() =>
  (flows.value?.flows || []).filter(
    (flow) =>
      flow.year != null &&
      flow.year >= yearRange.value[0] &&
      flow.year <= yearRange.value[1] &&
      visibleFlowTypes.value.includes(flow.type) &&
      flow.source !== flow.target,
  ),
);
const matrixGenres = computed(() => {
  const totals = new Map();
  for (const flow of filteredFlows.value) {
    totals.set(flow.source, (totals.get(flow.source) || 0) + flow.value);
    totals.set(flow.target, (totals.get(flow.target) || 0) + flow.value);
  }
  const ranked = [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .map((entry) => entry[0]);
  return [
    "Oceanus Folk",
    ...ranked.filter((name) => name !== "Oceanus Folk"),
  ].slice(0, 12);
});
const matrixCells = computed(() => {
  const aggregate = new Map();
  for (const flow of filteredFlows.value) {
    if (
      !matrixGenres.value.includes(flow.source) ||
      !matrixGenres.value.includes(flow.target)
    )
      continue;
    const key = `${flow.source}|${flow.target}`;
    aggregate.set(key, (aggregate.get(key) || 0) + flow.value);
  }
  return [...aggregate.entries()].map(([key, value]) => {
    const [source, target] = key.split("|");
    return [
      matrixGenres.value.indexOf(target),
      matrixGenres.value.indexOf(source),
      value,
    ];
  });
});
const matrixMax = computed(() => {
  const values = matrixCells.value.map((cell) => cell[2]).sort((a, b) => a - b);
  return values.length
    ? Math.max(1, values[Math.floor(values.length * 0.92)])
    : 1;
});
const matrixOption = computed(() => ({
  tooltip: {
    position: "top",
    formatter: (params) => {
      const source = matrixGenres.value[params.data[1]];
      const target = matrixGenres.value[params.data[0]];
      return `${source} <b>→</b> ${target}<br>影响事件 ${params.data[2]} 条 · 点击查看证据`;
    },
  },
  grid: { left: 112, right: 16, top: 14, bottom: 76 },
  xAxis: {
    type: "category",
    data: matrixGenres.value,
    axisLabel: { rotate: 42, fontSize: 10, color: CHART_MUTED },
    splitArea: { show: true },
  },
  yAxis: {
    type: "category",
    data: matrixGenres.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    splitArea: { show: true },
  },
  visualMap: {
    min: 0,
    max: matrixMax.value,
    calculable: false,
    orient: "horizontal",
    left: "center",
    bottom: 0,
    itemWidth: 12,
    itemHeight: 90,
    textStyle: { fontSize: 10, color: CHART_MUTED },
    inRange: { color: ["#152539", "#2d4764", "#649bc3", "#8fd7f8"] },
  },
  series: [
    {
      type: "heatmap",
      data: matrixCells.value,
      itemStyle: { borderColor: "#101925", borderWidth: 2 },
      emphasis: { itemStyle: { borderColor: "#8fd7f8", borderWidth: 2 } },
    },
  ],
}));

const flowTypeOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0, textStyle: { fontSize: 11, color: CHART_MUTED } },
  grid: { left: 46, right: 18, top: 32, bottom: 28 },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: chartYears.value,
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    axisLine: { lineStyle: { color: CHART_GRID } },
  },
  yAxis: {
    type: "value",
    name: "事件数",
    nameTextStyle: { fontSize: 10, color: CHART_MUTED },
    axisLabel: { fontSize: 10, color: CHART_MUTED },
    splitLine: { lineStyle: { color: CHART_GRID } },
  },
  series: FLOW_TYPES.filter((type) =>
    visibleFlowTypes.value.includes(type),
  ).map((type) => ({
    name: EDGE_LABELS[type],
    type: "line",
    stack: "flow",
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 0 },
    areaStyle: { color: FLOW_COLORS[type], opacity: 0.78 },
    itemStyle: { color: FLOW_COLORS[type] },
    data: chartYears.value.map((year) =>
      filteredFlows.value
        .filter((flow) => flow.type === type && flow.year === year)
        .reduce((sum, flow) => sum + flow.value, 0),
    ),
  })),
}));

function onMatrixClick(params) {
  if (!params.data) return;
  selectedCell.value = {
    source: matrixGenres.value[params.data[1]],
    target: matrixGenres.value[params.data[0]],
  };
}
function onTrendClick(params) {
  selectedYear.value = chartYears.value[params.dataIndex] ?? null;
}
const drillRows = computed(() => {
  if (selectedCell.value) {
    return filteredFlows.value.filter(
      (flow) =>
        flow.source === selectedCell.value.source &&
        flow.target === selectedCell.value.target,
    );
  }
  if (selectedYear.value != null) {
    return filteredFlows.value.filter(
      (flow) => flow.year === selectedYear.value,
    );
  }
  return filteredFlows.value.slice(0, 12);
});
const eventById = computed(
  () => new Map((events.value?.events || []).map((event) => [event.id, event])),
);
function evidenceFor(flow) {
  return (flow.event_ids || []).slice(0, 3).map((id) => {
    const event = eventById.value.get(id);
    return event ? `${id} · ${event.type} · ${event.year ?? "无日期"}` : id;
  });
}

const folkRows = computed(() =>
  (trends.value?.rows || []).filter((row) => row.genre === "Oceanus Folk"),
);
const peakRow = computed(() =>
  folkRows.value.reduce(
    (best, row) =>
      !best || row.outbound_events > best.outbound_events ? row : best,
    null,
  ),
);
const folkTotal = computed(() =>
  folkRows.value.reduce((sum, row) => sum + row.outbound_events, 0),
);
const concentration = computed(() =>
  peakRow.value && folkTotal.value
    ? peakRow.value.outbound_events / folkTotal.value
    : 0,
);
const folkActiveYears = computed(
  () => folkRows.value.filter((row) => row.outbound_events > 0).length,
);
const boomShare = computed(() =>
  folkTotal.value
    ? folkRows.value
        .filter((row) => row.year >= 2023 && row.year <= 2030)
        .reduce((sum, row) => sum + row.outbound_events, 0) / folkTotal.value
    : 0,
);
const lateShare = computed(() =>
  folkTotal.value
    ? folkRows.value
        .filter((row) => row.year >= 2032)
        .reduce((sum, row) => sum + row.outbound_events, 0) / folkTotal.value
    : 0,
);
const trailingPeak = computed(() =>
  folkRows.value.reduce(
    (best, row) =>
      !best || row.outbound_trailing_5y_mean > best.outbound_trailing_5y_mean
        ? row
        : best,
    null,
  ),
);
const spreadLabel = computed(() =>
  concentration.value < 0.2 && folkActiveYears.value >= 10
    ? "多波次扩散"
    : concentration.value < 0.4
      ? "脉冲式扩散"
      : "单年爆发",
);
function topFlow(side, fixed) {
  const totals = new Map();
  for (const flow of filteredFlows.value) {
    if (side === "out" && flow.source !== fixed) continue;
    if (side === "in" && flow.target !== fixed) continue;
    const key = side === "out" ? flow.target : flow.source;
    if (key === "Oceanus Folk") continue;
    totals.set(key, (totals.get(key) || 0) + flow.value);
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
}
const topOut = computed(() => topFlow("out", "Oceanus Folk"));
const topIn = computed(() => topFlow("in", "Oceanus Folk"));
const issues = computed(() => overview.value?.issue_counts || {});
const folkWorks = computed(
  () => overview.value?.genre_work_counts?.["Oceanus Folk"] ?? 0,
);
const focalGenre = computed(() => focusGenres.value[0] || "Oceanus Folk");
function flowsAround(side) {
  const totals = new Map();
  for (const flow of filteredFlows.value) {
    if (
      side === "in"
        ? flow.target !== focalGenre.value
        : flow.source !== focalGenre.value
    )
      continue;
    const name = side === "in" ? flow.source : flow.target;
    totals.set(name, (totals.get(name) || 0) + flow.value);
  }
  return [...totals].sort((a, b) => b[1] - a[1]).slice(0, 5);
}
const inbound = computed(() => flowsAround("in"));
const outbound = computed(() => flowsAround("out"));
const sankeyOption = computed(() => ({
  tooltip: {
    trigger: "item",
    formatter: (p) =>
      p.dataType === "edge"
        ? `${p.data.flowSource} → ${p.data.flowTarget}<br>影响事件 ${p.value} 条 · 点击回查证据`
        : p.name.replace(/^(in|out):/, ""),
  },
  series: [
    {
      type: "sankey",
      left: 104,
      right: 104,
      top: 28,
      bottom: 24,
      nodeWidth: 12,
      nodeGap: 28,
      draggable: false,
      layoutIterations: 48,
      nodeAlign: "justify",
      data: [
        ...inbound.value.map(([name]) => ({
          name: `in:${name}`,
          depth: 0,
          itemStyle: { color: "#7eadd8" },
          label: { position: "left" },
        })),
        {
          name: focalGenre.value,
          depth: 1,
          itemStyle: { color: "#8fd7f8" },
          label: {
            position: "top",
            color: "#e8f3ff",
            fontSize: 14,
            fontWeight: 500,
          },
        },
        ...outbound.value.map(([name]) => ({
          name: `out:${name}`,
          depth: 2,
          itemStyle: { color: "#e7b58a" },
          label: { position: "right" },
        })),
      ],
      links: [
        ...inbound.value.map(([name, value]) => ({
          source: `in:${name}`,
          target: focalGenre.value,
          value,
          flowSource: name,
          flowTarget: focalGenre.value,
        })),
        ...outbound.value.map(([name, value]) => ({
          source: focalGenre.value,
          target: `out:${name}`,
          value,
          flowSource: focalGenre.value,
          flowTarget: name,
        })),
      ],
      label: {
        color: "#c8d8ef",
        fontSize: 12,
        formatter: (p) => p.name.replace(/^(in|out):/, ""),
      },
      itemStyle: { borderWidth: 0, borderRadius: 2 },
      lineStyle: { color: "gradient", opacity: 0.24, curveness: 0.55 },
      emphasis: { focus: "adjacency", lineStyle: { opacity: 0.55 } },
    },
  ],
}));
function onSankeyClick(params) {
  if (params.dataType === "edge") {
    selectedCell.value = {
      source: params.data.flowSource,
      target: params.data.flowTarget,
    };
    selectedYear.value = null;
  }
}
function selectFlow(name) {
  selectedCell.value = { source: focalGenre.value, target: name };
  selectedYear.value = null;
}
function clearDrill() {
  selectedCell.value = null;
  selectedYear.value = null;
}
function showEvidence() {
  scrollToSection("genre-evidence");
}
watch([() => store.yearRange, () => store.visibleFlowTypes], clearDrill, {
  deep: true,
});
</script>

<template>
  <div
    v-if="loading || error"
    class="op-state"
    :class="{ error }"
    role="status"
  >
    {{ error || "正在加载流派传播证据…" }}
  </div>
  <template v-else>
    <section id="genre" class="analysis-screen hero">
      <div class="wrap">
        <div class="analysis-head">
          <div>
            <h1>
              流派传播可视分析<span class="title-english"
                >A genre in motion</span
              >
            </h1>
            <p class="head-description">
              沿着音乐借鉴关系，观察灵感如何跨越流派、留下新的作品。
            </p>
          </div>
          <div class="data-overview">
            <div>
              <strong>{{ allGenres.length }}</strong
              ><span>音乐流派</span>
            </div>
            <div>
              <strong>{{ folkWorks }}</strong
              ><span>Oceanus Folk 作品</span>
            </div>
            <div>
              <strong>{{
                formatCount(filteredFlows.reduce((s, f) => s + f.value, 0))
              }}</strong
              ><span>筛选内影响事件</span>
            </div>
          </div>
        </div>
        <div class="genre-tools">
          <div class="segmented-control" aria-label="传播图表类型">
            <button
              class="op-chip"
              :class="{ on: visual === 'flow' }"
              :aria-pressed="visual === 'flow'"
              @click="visual = 'flow'"
            >
              传播路径</button
            ><button
              class="op-chip"
              :class="{ on: visual === 'trend' }"
              :aria-pressed="visual === 'trend'"
              @click="visual = 'trend'"
            >
              年度轨迹
            </button>
          </div>
          <div class="op-chips" v-if="visual === 'trend'">
            <button
              v-for="item in metricOptions"
              :key="item.value"
              class="op-chip"
              :class="{ on: metric === item.value }"
              :aria-pressed="metric === item.value"
              @click="metric = item.value"
            >
              {{ item.label }}
            </button>
          </div>
          <label class="genre-focus-select"
            ><span class="sr-only">选择中心流派</span
            ><select
              class="op-select"
              aria-label="选择中心流派"
              :value="focalGenre"
              @change="focusGenres = [$event.target.value]"
            >
              <option v-for="genre in allGenres" :key="genre" :value="genre">
                {{ genre }}
              </option>
            </select></label
          ><FilterPanel
            v-model="visibleFlowTypes"
            label="影响关系"
            :options="flowTypeOptions"
          />
        </div>
        <div class="app-frame genre-workspace">
          <div class="genre-main">
            <div class="flow-chart-heading">
              <span>{{
                visual === "flow"
                  ? "灵感来源"
                  : metricOptions.find((m) => m.value === metric)?.label
              }}</span
              ><strong>{{ focalGenre }}</strong
              ><span>{{ visual === "flow" ? "影响流向" : "1975—2040" }}</span>
            </div>
            <div class="genre-chart">
              <ChartPanel
                v-if="visual === 'flow'"
                :option="sankeyOption"
                label="中心流派前五大外部来源与前五大去向，带宽表示影响事件数量"
                @chart-click="onSankeyClick"
              /><ChartPanel
                v-else
                :option="trendOption"
                label="所选流派逐年影响趋势"
                @chart-click="onTrendClick"
              />
            </div>
            <div class="genre-legends" v-if="visual === 'trend'">
              <FilterPanel
                v-model="focusGenres"
                label="比较流派"
                :options="genreOptions"
              />
            </div>
            <div class="genre-timeline">
              <TimeScrubber v-model="yearRange" />
            </div>
          </div>
          <aside class="genre-aside">
            <div>
              <span class="field-label">Oceanus Folk · 扩散观察</span>
              <div class="finding-number">
                {{ (boomShare * 100).toFixed(1) }}<small>%</small>
              </div>
              <h2 class="finding-title">影响集中于 2023—2030</h2>
              <p class="finding-copy">
                全期 {{ folkTotal }} 条外向事件分布在
                {{ folkActiveYears }} 个年份，{{ peakRow.year }}
                年达到峰值。整体呈多波次扩散。
              </p>
            </div>
            <div class="flow-ranking">
              <span class="field-label">{{ focalGenre }} · 主要流向</span
              ><button
                v-for="[name, count] in outbound.slice(0, 3)"
                :key="name"
                @click="selectFlow(name)"
              >
                <span>{{ name }}</span
                ><strong>{{ count }}</strong
                ><AppIcon name="arrow" :size="14" />
              </button>
              <p v-if="!outbound.length" class="op-note">
                当前筛选内没有外向影响记录。
              </p>
            </div>
            <div
              v-if="selectedCell || selectedYear"
              class="selected-flow-proof"
              aria-live="polite"
            >
              <span class="field-label">已选证据</span>
              <p>
                {{
                  selectedCell
                    ? `${selectedCell.source} → ${selectedCell.target}`
                    : `${selectedYear} 年`
                }}
              </p>
              <span
                >{{
                  drillRows.reduce((sum, row) => sum + row.value, 0)
                }}
                条影响事件</span
              ><button class="section-link" @click="showEvidence">
                回查原始关系 <AppIcon name="arrow" :size="14" />
              </button>
            </div>
            <p class="op-note" v-else>
              点击流线或年度曲线，选择一组可回查的影响证据。
            </p>
          </aside>
        </div>
        <div class="workspace-footline">
          <span>流线宽度表示影响事件数量 · 展示前五来源与去向</span
          ><button class="section-link" @click="showEvidence">
            查看矩阵与证据
            <AppIcon name="arrow" :size="14" class="down-arrow" />
          </button>
        </div>
      </div>
    </section>
    <section id="genre-evidence" class="analysis-evidence genre-evidence">
      <div class="wrap">
        <div class="section-heading">
          <div>
            <h2>流派之间的音乐传递</h2>
            <p>从聚合矩阵，回到具体年份与五类音乐影响关系。</p>
          </div>
          <FilterPanel
            v-model="visibleFlowTypes"
            label="影响关系"
            :options="flowTypeOptions"
          />
        </div>
        <div class="genre-chart-grid">
          <article class="op-card">
            <header>
              <h3>跨流派流向矩阵</h3>
              <p>纵轴来源 · 横轴受影响者 · 点击筛选证据</p>
            </header>
            <ChartPanel
              :option="matrixOption"
              height="410px"
              label="十二个主要流派的定向影响矩阵"
              @chart-click="onMatrixClick"
            />
          </article>
          <article class="op-card">
            <header>
              <h3>音乐影响的年代构成</h3>
              <p>五类关系的年度事件数量</p>
            </header>
            <ChartPanel
              :option="flowTypeOption"
              height="410px"
              label="五类音乐影响事件的逐年堆叠面积图"
            />
          </article>
        </div>
        <article class="op-card evidence-panel">
          <header>
            <h3>原始影响证据</h3>
            <div class="evidence-filter" aria-live="polite">
              <span>{{
                selectedCell
                  ? `${selectedCell.source} → ${selectedCell.target}`
                  : selectedYear
                    ? `${selectedYear} 年`
                    : "当前筛选内的前 12 组记录"
              }}</span
              ><button v-if="selectedCell || selectedYear" @click="clearDrill">
                清除选择 <AppIcon name="close" :size="12" />
              </button>
            </div>
          </header>
          <div class="op-scroll">
            <table class="op-table">
              <thead>
                <tr>
                  <th>来源流派</th>
                  <th>受影响流派</th>
                  <th>影响关系</th>
                  <th class="num">年份</th>
                  <th class="num">事件数</th>
                  <th>原始关系 ID</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(flow, index) in drillRows.slice(0, 40)"
                  :key="`${flow.source}-${flow.target}-${flow.type}-${flow.year}-${index}`"
                >
                  <td>{{ flow.source }}</td>
                  <td>{{ flow.target }}</td>
                  <td>{{ EDGE_LABELS[flow.type] }}</td>
                  <td class="num">{{ flow.year }}</td>
                  <td class="num">{{ flow.value }}</td>
                  <td class="proof-ids">{{ evidenceFor(flow).join(" / ") }}</td>
                </tr>
              </tbody>
            </table>
            <p class="evidence-empty" v-if="!drillRows.length">
              此时间窗与关系筛选内没有匹配的证据，请扩大时间范围。
            </p>
          </div>
        </article>
        <div class="insight-row">
          <article class="insight-block">
            <h3>多波次扩散</h3>
            <p>
              峰值 {{ peakRow.year }} 年占全期外向事件的
              {{ (concentration * 100).toFixed(1) }}%。{{
                (boomShare * 100).toFixed(1)
              }}% 的事件集中在 2023—2030，不能概括为单年爆发或匀速增长。
            </p>
          </article>
          <article class="insight-block">
            <h3>影响与吸收分开观察</h3>
            <p>
              当前时段 Oceanus Folk 主要流向
              {{
                topOut.map((x) => x[0]).join("、") || "无记录"
              }}；主要灵感来源为
              {{ topIn.map((x) => x[0]).join("、") || "无记录" }}。
            </p>
          </article>
          <article class="insight-block">
            <h3>时间缺失保留未知</h3>
            <p>
              {{ issues.influence_chronology }} 条时间顺序疑点、1 条自环与 67
              条无日期引用未计入年度曲线。结构关系保留，不用缺失日期补出增长趋势。
            </p>
          </article>
        </div>
      </div>
    </section>
  </template>
</template>
