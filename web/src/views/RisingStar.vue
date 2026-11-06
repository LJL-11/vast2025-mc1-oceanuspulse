<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { loadRisingStar, dataService } from "../lib/dataService";
import { useAppStore } from "../stores/useAppStore";
import ChartPanel from "../components/ChartPanel.vue";
import AppIcon from "../components/AppIcon.vue";
import { scrollToSection } from "../lib/navigation";
import { CHART_MUTED, CHART_GRID } from "../lib/palette";
const store = useAppStore();
const data = ref(null),
  loading = ref(true),
  error = ref(""),
  selectedId = ref(null),
  trajectoryMetric = ref("cumulative_works");
const COLORS = ["#8fd7f8", "#e7b58a", "#dfc180"];
const strengthLabels = {
  mentor: "导师",
  momentum: "产出动量",
  quality: "作品质量",
  collaboration: "合作网络",
  influence: "音乐影响",
  prestige: "厂牌资源",
};
const predictions = computed(() => data.value?.predictions || []);
const selected = computed(
  () =>
    predictions.value.find((p) => p.act_id === selectedId.value) ||
    predictions.value[0],
);
const comparison = computed(() => data.value?.comparison || []);
const validation = computed(() => data.value?.validation || {});
const cv = computed(() => validation.value.cross_validation || {});
const meta = computed(() => data.value?.meta || {});
const leaderboard = computed(() =>
  (data.value?.leaderboard || []).slice(0, 12),
);
const featureLabels = computed(() =>
  Object.fromEntries((data.value?.features || []).map((f) => [f.key, f.label])),
);
const univariate = computed(() =>
  (validation.value.univariate?.tests || []).slice(0, 6),
);
const coefficients = computed(() =>
  (validation.value.coefficients || []).slice(0, 6),
);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await loadRisingStar();
    selectedId.value = data.value.predictions[0]?.act_id;
  } catch {
    error.value = "新星分析数据尚未就绪，请先生成 rising_star.json。";
  } finally {
    loading.value = false;
    await nextTick();
    document.documentElement.dataset.ready = "1";
  }
}
onMounted(load);
const radarOption = computed(() => ({
  tooltip: {},
  legend: { show: false },
  radar: {
    radius: "66%",
    center: ["50%", "50%"],
    indicator: Object.values(strengthLabels).map((name) => ({
      name,
      max: 100,
    })),
    axisName: { color: CHART_MUTED, fontSize: 12 },
    splitNumber: 4,
    splitArea: { areaStyle: { color: ["#132237", "#142336"] } },
    axisLine: { lineStyle: { color: CHART_GRID } },
    splitLine: { lineStyle: { color: "#334c67" } },
  },
  series: [
    {
      type: "radar",
      symbolSize: 4,
      data: predictions.value.map((item, index) => ({
        name: item.name,
        value: Object.keys(strengthLabels).map(
          (key) => item.strength_percentiles?.[key] ?? 0,
        ),
        lineStyle: {
          color: COLORS[index],
          width: item.act_id === selectedId.value ? 2 : 1,
          opacity: item.act_id === selectedId.value ? 1 : 0.18,
        },
        itemStyle: {
          color: COLORS[index],
          opacity: item.act_id === selectedId.value ? 1 : 0.18,
        },
        areaStyle: {
          color: COLORS[index],
          opacity: item.act_id === selectedId.value ? 0.09 : 0,
        },
      })),
    },
  ],
}));
const trajectoryOption = computed(() => {
  const years = [
    ...new Set(
      comparison.value.flatMap((a) => (a.timeline || []).map((r) => r.year)),
    ),
  ].sort((a, b) => a - b);
  return {
    tooltip: { trigger: "axis" },
    legend: {
      bottom: 0,
      type: "scroll",
      textStyle: { color: CHART_MUTED, fontSize: 12 },
    },
    grid: { left: 40, right: 12, top: 20, bottom: 64 },
    xAxis: {
      type: "category",
      data: years,
      boundaryGap: false,
      axisLabel: { color: CHART_MUTED, fontSize: 12 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: CHART_MUTED, fontSize: 12 },
      splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } },
    },
    series: comparison.value.map((artist, index) => {
      const rows = new Map((artist.timeline || []).map((r) => [r.year, r]));
      let previous = 0;
      return {
        name: artist.name,
        type: "line",
        smooth: 0.2,
        showSymbol: false,
        connectNulls: true,
        lineStyle: { width: 2, color: COLORS[index % 3] },
        itemStyle: { color: COLORS[index % 3] },
        data: years.map((year) => {
          const row = rows.get(year);
          if (row) previous = row[trajectoryMetric.value] ?? previous;
          return previous;
        }),
      };
    }),
  };
});
const leaderboardOption = computed(() => {
  const rows = [...leaderboard.value].reverse();
  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const item = rows[params[0].dataIndex];
        return `${item.name}<br>综合分 ${item.score}<br>模型概率 ${item.model_probability.toFixed(3)}<br>${item.had_hit ? "已有登榜记录" : "未有登榜记录"}`;
      },
    },
    grid: { left: 126, right: 36, top: 8, bottom: 20 },
    xAxis: {
      type: "value",
      max: 100,
      axisLabel: { color: CHART_MUTED, fontSize: 12 },
      splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } },
    },
    yAxis: {
      type: "category",
      data: rows.map((r) => r.name),
      axisLabel: {
        color: CHART_MUTED,
        fontSize: 12,
        width: 112,
        overflow: "truncate",
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        barWidth: 8,
        data: rows.map((row) => ({
          value: row.score,
          itemStyle: {
            borderRadius: [0, 3, 3, 0],
            color: row.had_hit ? "#4b5f78" : "#8fd7f8",
          },
        })),
        label: {
          show: true,
          position: "right",
          color: CHART_MUTED,
          fontSize: 12,
        },
      },
    ],
  };
});
async function inspectCandidate() {
  const graph = await dataService.sailorEgo();
  const node =
    graph.nodes.find((n) => n.id === selected.value.group_id) ||
    graph.nodes.find((n) => n.id === selected.value.representative);
  if (node) store.selectNode({ ...node, genre: "Oceanus Folk" });
  else
    store.selectNode({
      id: selected.value.group_id,
      name: selected.value.name,
      type: "MusicalGroup",
      genre: "Oceanus Folk",
    });
  store.setModule("influence");
}
function selectLeaderboard(params) {
  const name = [...leaderboard.value].reverse()[params.dataIndex]?.name;
  const item = predictions.value.find((p) => p.name === name);
  if (item) {
    selectedId.value = item.act_id;
    scrollToSection("rising");
  }
}
</script>

<template>
  <div
    v-if="loading || error"
    class="op-state"
    :class="{ error }"
    role="status"
  >
    {{ error || "正在加载新星画像…"
    }}<button v-if="error" class="btn btn--secondary" @click="load">
      重新加载数据
    </button>
  </div>
  <template v-else>
    <section id="rising" class="analysis-screen rising-screen hero">
      <div class="wrap">
        <div class="analysis-head">
          <div>
            <h1>
              新星画像与预测<span class="title-english">The next wave</span>
            </h1>
            <p class="head-description">
              比较创作、合作与影响证据，寻找下一代 Oceanus Folk 音乐人。
            </p>
          </div>
          <div class="data-overview">
            <div>
              <strong>{{ meta.reference_acts }}</strong
              ><span>参照音乐团体</span>
            </div>
            <div>
              <strong>{{ cv.auc.toFixed(3) }}</strong
              ><span>历史回溯 AUC</span>
            </div>
          </div>
        </div>
        <div class="rising-topline">
          <span class="window-label"
            ><AppIcon name="star" :size="15" />预测窗口
            {{ meta.prediction_window.join("—") }}</span
          ><span>选择候选，联动能力雷达与证据</span>
        </div>
        <div class="rising-grid">
          <div class="candidate-list" aria-label="新星候选排名">
            <button
              v-for="(item, index) in predictions"
              :key="item.act_id"
              class="candidate-card"
              :class="{ selected: item.act_id === selectedId }"
              :style="{ '--candidate-color': COLORS[index] }"
              :aria-pressed="item.act_id === selectedId"
              @click="selectedId = item.act_id"
            >
              <span class="candidate-rank"
                >候选 <strong>0{{ item.rank }}</strong></span
              >
              <h2>{{ item.name }}</h2>
              <span class="candidate-meta"
                >{{ item.debut }}—{{ item.last_active }} · Oceanus Folk</span
              ><span class="candidate-score"
                ><strong>{{ item.score }}</strong
                ><span>综合评分 / 100</span></span
              >
              <span class="candidate-mini-bars" aria-hidden="true"
                ><i
                  v-for="(value, key) in item.strength_percentiles"
                  :key="key"
                  :style="{ height: `${Math.max(4, value)}%` }" /></span
              ><span class="candidate-support"
                >与 Sailor Shift 共同署名
                {{ item.raw.n_sailor_works }} 部作品<br />{{
                  item.member_names.length
                }}
                位成员 · {{ item.raw.n_works }} 部作品</span
              ><span class="candidate-status"
                >{{
                  selectedId === item.act_id ? "正在查看证据" : "查看候选证据"
                }}<AppIcon
                  :name="selectedId === item.act_id ? 'check' : 'arrow'"
                  :size="16"
              /></span>
            </button>
          </div>
          <article class="candidate-inspector" aria-label="候选能力与证据">
            <header>
              <h3>六维能力对比</h3>
              <span>参照群体百分位</span>
            </header>
            <div class="candidate-radar">
              <ChartPanel
                :option="radarOption"
                label="三位候选的六维能力雷达，选中候选高亮"
              />
            </div>
            <div class="candidate-evidence" aria-live="polite">
              <h3>{{ selected.name }} 的预测依据</h3>
              <p>
                共同署名 {{ selected.raw.n_sailor_works }} 部作品 · 模型概率
                {{ selected.model_probability.toFixed(3) }}<br />Bootstrap
                第一名占比
                {{ (selected.bootstrap_rank1_share * 100).toFixed(0) }}%
              </p>
              <p class="evidence-name">
                {{ selected.member_names.join(" / ") }}
              </p>
              <button class="section-link" @click="inspectCandidate">
                查看图谱关系 <AppIcon name="arrow" :size="16" />
              </button>
            </div>
          </article>
        </div>
        <div class="workspace-footline">
          <span>综合分为六维百分位加权，模型概率不等同于成名概率。</span
          ><a
            class="section-link"
            href="#rising-validation"
            @click.prevent="scrollToSection('rising-validation')"
            >查看模型检验 <AppIcon name="arrow" :size="14" class="down-arrow"
          /></a>
        </div>
      </div>
    </section>
    <section id="rising-validation" class="analysis-evidence rising-validation">
      <div class="wrap">
        <div class="section-heading">
          <div>
            <h2>职业轨迹与历史验证</h2>
            <p>预测的依据和边界，与候选排名一起呈现。</p>
          </div>
          <div class="segmented-control">
            <button
              v-for="item in [
                { key: 'cumulative_works', label: '累计作品' },
                { key: 'cumulative_hits', label: '已知登榜' },
              ]"
              :key="item.key"
              class="op-chip"
              :class="{ on: trajectoryMetric === item.key }"
              :aria-pressed="trajectoryMetric === item.key"
              @click="trajectoryMetric = item.key"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div class="validation-grid">
          <article class="op-card">
            <header>
              <h3>三位艺人的职业轨迹</h3>
              <p>逐年累计 · 连续年度</p>
            </header>
            <ChartPanel
              :option="trajectoryOption"
              height="300px"
              label="任务指定三位艺人职业轨迹比较"
            />
          </article>
          <article class="op-card">
            <header>
              <h3>Oceanus Folk 综合分排行</h3>
              <p>浅绿为未登榜候选 · 点击候选查看画像</p>
            </header>
            <ChartPanel
              :option="leaderboardOption"
              height="300px"
              label="Oceanus Folk 综合分前十二名"
              @chart-click="selectLeaderboard"
            />
          </article>
        </div>
        <div class="validation-hero">
          <article class="op-card">
            <header>
              <h3>历史五年回溯</h3>
              <p>5 折交叉验证</p>
            </header>
            <div class="validation-score">
              {{ cv.auc.toFixed(3) }}<span>AUC</span>
            </div>
            <p class="validation-copy">
              Logistic 模型使用
              {{ meta.snapshot_year }}
              年以前的历史五年窗口进行回溯，独立于六维综合评分。预测窗口内没有真实结果，因此这里展示历史区分能力，不能解释为未来成名概率。
            </p>
            <div class="validation-table">
              <table class="op-table">
                <thead>
                  <tr>
                    <th>模型特征</th>
                    <th class="num">系数</th>
                    <th class="num">OR</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in coefficients" :key="row.feature">
                    <td>{{ featureLabels[row.feature] || row.feature }}</td>
                    <td class="num">{{ row.coefficient.toFixed(3) }}</td>
                    <td class="num">{{ row.odds_ratio.toFixed(3) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
          <article class="op-card">
            <header>
              <h3>特征统计检验</h3>
              <p>Mann–Whitney U · BH-FDR</p>
            </header>
            <div class="validation-table">
              <table class="op-table">
                <thead>
                  <tr>
                    <th>特征</th>
                    <th class="num">正 / 负均值</th>
                    <th class="num">p</th>
                    <th class="num">q</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in univariate" :key="row.feature">
                    <td>{{ featureLabels[row.feature] || row.feature }}</td>
                    <td class="num">
                      {{ row.mean_positive.toFixed(2) }} /
                      {{ row.mean_negative.toFixed(2) }}
                    </td>
                    <td class="num">{{ row.p_value.toExponential(1) }}</td>
                    <td class="num">{{ row.p_fdr.toFixed(3) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="validation-copy">
              同时报告原始 p 值和多重比较校正后的 q
              值。候选仅在给定数据、时间窗口和评分规则内比较，不将缺失登榜记录视为已证实的失败。
            </p>
          </article>
        </div>
      </div>
    </section>
  </template>
</template>
