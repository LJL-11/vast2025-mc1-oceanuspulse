<script setup>
import { computed, onMounted, ref } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import ForceGraph from '../components/ForceGraph.vue'
import TimeScrubber from '../components/TimeScrubber.vue'
import FilterPanel from '../components/FilterPanel.vue'
import DetailCard from '../components/DetailCard.vue'
import ChartPanel from '../components/ChartPanel.vue'
import {
  NODE_COLORS, NODE_LABELS, CREDIT_EDGE_TYPES, INFLUENCE_EDGE_TYPES,
  EDGE_COLOR_CREDIT, EDGE_COLOR_INFLUENCE,
  CHART_MUTED, CHART_GRID, formatCount,
} from '../lib/palette'

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const overview = ref(null)
const ego = ref(null)
const sailor = ref(null)
const search = ref('')
const edgeMode = ref('all')

onMounted(async () => {
  try {
    const [o, g, s] = await Promise.all([
      dataService.overview(), dataService.sailorEgo(), dataService.sailor(),
    ])
    overview.value = o
    ego.value = g
    sailor.value = s
  } catch (cause) {
    error.value = friendlyDataError(cause)
  } finally {
    loading.value = false
  }
})

const typeOptions = Object.keys(NODE_COLORS).map(type => ({
  value: type, label: NODE_LABELS[type], color: NODE_COLORS[type],
}))
const edgeModes = [
  { key: 'all', label: '全部关系' },
  { key: 'credit', label: '署名 / 录制' },
  { key: 'influence', label: '音乐影响' },
]
const visibleTypes = computed({
  get: () => store.visibleTypes,
  set: value => { store.visibleTypes = value },
})
const yearRange = computed({
  get: () => store.yearRange,
  set: value => store.setYearRange(value),
})
const visibleEdgeTypes = computed(() => {
  if (edgeMode.value === 'influence') return INFLUENCE_EDGE_TYPES
  if (edgeMode.value === 'credit') return CREDIT_EDGE_TYPES
  return [...CREDIT_EDGE_TYPES, ...INFLUENCE_EDGE_TYPES]
})

const nodeById = computed(() => new Map((ego.value?.nodes || []).map(node => [node.id, node])))
const focusId = computed(() => store.focusNode?.id ?? null)
const focusDegree = computed(() => {
  const id = focusId.value
  if (id == null || !ego.value) return 0
  return ego.value.links.filter(link => link.source === id || link.target === id).length
})
const focusLinkTypes = computed(() => {
  const id = focusId.value
  if (id == null || !ego.value) return []
  const counts = new Map()
  for (const link of ego.value.links) {
    if (link.source !== id && link.target !== id) continue
    counts.set(link.type, (counts.get(link.type) || 0) + 1)
  }
  return [...counts.entries()].map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count)
})

const works = computed(() => (sailor.value?.works || [])
  .map(work => ({ ...work, node: nodeById.value.get(work.id) }))
  .filter(work => work.node && work.node.release_year))
const careerYears = computed(() => {
  const years = works.value.map(work => work.node.release_year)
  if (!years.length) return []
  const start = Math.min(...years)
  const end = Math.max(...years)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})
const careerOption = computed(() => {
  const years = careerYears.value
  const perYear = years.map(year => works.value.filter(work => work.node.release_year === year).length)
  let cumulative = 0
  const cumulativeSeries = perYear.map(count => (cumulative += count))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['累计作品', '当年新作'], top: 0, textStyle: { fontSize: 11, color: CHART_MUTED } },
    grid: { left: 42, right: 18, top: 30, bottom: 28 },
    xAxis: {
      type: 'category', data: years, boundaryGap: false,
      axisLabel: { fontSize: 10, color: CHART_MUTED },
      axisLine: { lineStyle: { color: CHART_GRID } },
    },
    yAxis: {
      type: 'value', name: '作品数', nameTextStyle: { fontSize: 10, color: CHART_MUTED },
      axisLabel: { fontSize: 10, color: CHART_MUTED }, splitLine: { lineStyle: { color: CHART_GRID } },
    },
    series: [
      {
        name: '累计作品', type: 'line', smooth: true, showSymbol: false,
        lineStyle: { width: 2.4, color: '#2A9D8F' }, itemStyle: { color: '#2A9D8F' },
        areaStyle: { color: 'rgba(42,157,143,0.13)' }, data: cumulativeSeries,
      },
      {
        name: '当年新作', type: 'scatter', symbolSize: 9,
        itemStyle: { color: '#E8734A' }, data: perYear,
      },
    ],
  }
})
function onCareerClick(params) {
  const year = careerYears.value[params.dataIndex]
  if (year) store.setYearRange([year, year])
}

const topCollaborators = computed(() => (sailor.value?.collaborators || []).slice(0, 12))
const maxShared = computed(() => Math.max(1, ...topCollaborators.value.map(item => item.shared_work_count)))
const upstreamPaths = computed(() => (sailor.value?.upstream_paths || []).slice(0, 12))

const searchResults = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query || !ego.value) return []
  return ego.value.nodes
    .filter(node => (node.display_name || node.name || '').toLowerCase().includes(query))
    .slice(0, 8)
})

function selectNode(node) {
  if (!node) return store.clearFocus()
  store.selectNode(node)
}
function pickCollaborator(item) {
  const node = nodeById.value.get(item.id) || {
    id: item.id, name: item.name, display_name: item.name, type: 'Person',
  }
  store.selectNode(node)
}
function pickPath(path) {
  const last = (path.node_path || []).at(-1)
  const node = nodeById.value.get(last)
  if (node) store.selectNode(node)
}
function pathLabel(path) {
  const parts = (path.node_path || []).map(id => {
    const node = nodeById.value.get(id)
    return node ? (node.display_name || node.name) : String(id)
  })
  return parts.length > 3 ? `… → ${parts.slice(-3).join(' → ')}` : parts.join(' → ')
}
function pickSearchResult(node) {
  store.selectNode(node)
  search.value = ''
}

const notableTotal = computed(() => overview.value?.chart_status?.notable ?? 0)
const missingChartYear = computed(() => overview.value?.chart_status?.notable_without_year ?? 0)
const components = computed(() => overview.value?.counts?.weak_components ?? 16)
</script>

<template>
  <div>
    <div v-if="loading" class="op-state">正在加载 Sailor Shift 关系网络…</div>
    <div v-else-if="error" class="op-state error">
      {{ error }}<br><code>python -m pipeline.run</code>
    </div>

    <template v-else>
      <div class="op-page-head">
        <div>
          <h2>模块一 · 影响力溯源</h2>
          <p>Sailor Shift 的两跳网络、共同署名合作者与可回溯的音乐影响路径 · 对应赛题任务 1.1 / 1.2 / 1.3</p>
        </div>
        <span class="op-tag">预计算布局 · 无浏览器端力仿真</span>
      </div>

      <div class="op-kpis">
        <div class="op-kpi"><b>{{ formatCount(overview.counts.nodes) }}</b><span>图谱节点</span></div>
        <div class="op-kpi"><b>{{ formatCount(overview.counts.links) }}</b><span>关系边</span></div>
        <div class="op-kpi"><b>{{ works.length }}</b><span>Sailor 直接署名作品</span></div>
        <div class="op-kpi"><b>{{ (sailor.collaborators || []).length }}</b><span>共同署名合作者</span></div>
        <div class="op-kpi"><b>{{ (sailor.inspiration_sources || []).length }}</b><span>上游影响来源</span></div>
        <div class="op-kpi"><b>{{ (sailor.directly_influenced || []).length }}</b><span>下游受影响对象</span></div>
      </div>

      <section class="op-card" style="padding: 0; margin-bottom: 14px">
        <div class="op-toolbar">
          <FilterPanel v-model="visibleTypes" label="实体类型" :options="typeOptions" />
          <div class="op-chips">
            <button
              v-for="mode in edgeModes" :key="mode.key" type="button"
              class="op-chip" :class="{ on: edgeMode === mode.key }"
              @click="edgeMode = mode.key"
            >{{ mode.label }}</button>
          </div>
        </div>
        <div class="op-toolbar">
          <TimeScrubber v-model="yearRange" :min="1975" :max="2040" />
          <input v-model="search" class="op-input" type="search" placeholder="搜索实体名…" style="width: 170px">
          <div v-if="searchResults.length" class="op-chips">
            <button
              v-for="node in searchResults" :key="node.id" type="button"
              class="op-chip" @click="pickSearchResult(node)"
            >{{ node.display_name || node.name }}</button>
          </div>
        </div>
      </section>

      <div class="op-grid two">
        <section class="op-card">
          <header>
            <h3>Sailor Shift 两跳关系网络</h3>
            <p>{{ (ego.nodes || []).length }} 节点 / {{ (ego.links || []).length }} 边</p>
          </header>
          <ForceGraph
            :nodes="ego.nodes || []" :links="ego.links || []"
            :visible-types="visibleTypes" :visible-edge-types="visibleEdgeTypes"
            :year-range="yearRange" :focus-id="focusId"
            @select="selectNode"
          />
          <div class="op-legend" style="margin-top: 12px">
            <span v-for="(label, type) in NODE_LABELS" :key="type">
              <i :style="{ background: NODE_COLORS[type] }" />{{ label }}
            </span>
            <span><i class="line" :style="{ background: EDGE_COLOR_INFLUENCE }" />音乐影响（带箭头）</span>
            <span><i class="line" :style="{ background: EDGE_COLOR_CREDIT }" />署名 / 录制 / 成员</span>
          </div>
          <p class="op-note">橙色箭头方向为「来源 → 受影响者」，与原图引用方向相反；灰蓝线只表示共同参与作品。时间窗外的作品节点会淡化但不会被删除，以保留网络结构。</p>
        </section>

        <div class="op-grid" style="gap: 14px; align-content: start">
          <DetailCard
            :node="store.focusNode" :degree="focusDegree" :link-types="focusLinkTypes"
            @close="store.clearFocus()" @jump="store.focusGenre"
          />
          <section class="op-card">
            <header><h3>共同署名合作者 Top 12</h3><p>按共同作品数 · 点击聚焦</p></header>
            <div
              v-for="item in topCollaborators" :key="item.id"
              class="op-bar-row" @click="pickCollaborator(item)"
            >
              <span class="op-bar-name" :title="item.name">{{ item.name }}</span>
              <div class="op-bar-track">
                <div class="op-bar-fill" :style="{ width: `${(item.shared_work_count / maxShared) * 100}%` }" />
              </div>
              <span class="op-bar-value">{{ item.shared_work_count }}</span>
            </div>
            <p class="op-note">共同署名只说明参与同一作品，不代表私人关系；同一作品上的多个署名角色只计一次合作。</p>
          </section>
        </div>
      </div>

      <div class="op-grid even" style="margin-top: 14px">
        <section class="op-card">
          <header><h3>作品累积轨迹</h3><p>点击年份可锁定全局时间窗</p></header>
          <ChartPanel :option="careerOption" height="250px" @chart-click="onCareerClick" />
          <p class="op-note">面积线为累计直接署名作品，橙点为当年新作。数据中的 Sailor 2028 爆红单曲没有 notoriety 记录，因此本图依据作品发行年而非登榜年构建。</p>
        </section>
        <section class="op-card">
          <header><h3>可回溯的上游影响路径</h3><p>最多三跳 · 保留原始边 ID</p></header>
          <div class="op-scroll">
            <table class="op-table">
              <thead><tr><th>来源实体链路</th><th class="num">跳数</th><th class="num">年份</th><th>日期完整</th></tr></thead>
              <tbody>
                <tr v-for="path in upstreamPaths" :key="path.id" @click="pickPath(path)">
                  <td>{{ pathLabel(path) }}</td>
                  <td class="num">{{ path.hops }}</td>
                  <td class="num">{{ (path.event_years || []).filter(Boolean).join(', ') || '—' }}</td>
                  <td><span class="op-tag">{{ path.fully_dated ? '是' : '否' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="op-note">路径只沿五类音乐影响边追溯，不经过录制、发行或普通合作边；点击一行可把末端实体设为焦点。</p>
        </section>
      </div>

      <h3 style="font-size: 14px; font-weight: 500; color: #17324d; margin: 20px 0 10px">数据洞见</h3>
      <div class="op-insights">
        <article class="op-insight">
          <span class="tag">洞见 01 · 慢热型崛起</span>
          <h4>合作网络比单曲更能解释她的地位</h4>
          <p>Sailor Shift 共有 {{ works.length }} 部直接署名作品、{{ (sailor.collaborators || []).length }} 位共同署名合作者，轨迹横跨 {{ careerYears[0] }}–{{ careerYears.at(-1) }} 年，是持续输出而非单年爆发；前乐队成员 Maya Jensen 与她共同署名 {{ topCollaborators[0]?.shared_work_count ?? '—' }} 部作品。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 02 · 影响不对称</span>
          <h4>她吸收的多，向外辐射的证据少且无日期</h4>
          <p>上游影响来源 {{ (sailor.inspiration_sources || []).length }} 个，下游受影响对象仅 {{ (sailor.directly_influenced || []).length }} 个；数据工程核验发现这 7 条下游引用全部没有日期，因此不能据此绘制「影响力逐年增长」曲线。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 03 · 数据陷阱</span>
          <h4>登榜字段不能当成绩单</h4>
          <p>全图 {{ formatCount(notableTotal) }} 部 notable 作品中有 {{ formatCount(missingChartYear) }} 部缺失登榜年份（{{ ((missingChartYear / notableTotal) * 100).toFixed(1) }}%）；<code>notable</code> 仅表示上过热榜，不代表冠军或销量，缺失值一律保持未知而非补 0。</p>
        </article>
        <article class="op-insight">
          <span class="tag">洞见 04 · 口径校正</span>
          <h4>官方说明与实测不一致</h4>
          <p>官方数据说明称 18 个连通分量，本组按弱连通重算为 {{ components }} 个，最大分量含 17,277 个节点。报告与答辩一律以本地复现结果为准，并保留原始记录不改。</p>
        </article>
      </div>
    </template>
  </div>
</template>
