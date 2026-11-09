<script setup>
import { computed, onMounted, ref } from 'vue'
import { dataService, friendlyDataError } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import CreditScore from '../components/CreditScore.vue'
import ForceGraph from '../components/ForceGraph.vue'
import TimeScrubber from '../components/TimeScrubber.vue'
import FilterPanel from '../components/FilterPanel.vue'
import DetailCard from '../components/DetailCard.vue'
import ChartPanel from '../components/ChartPanel.vue'
import AppIcon from '../components/AppIcon.vue'
import JournalPager from '../components/JournalPager.vue'
import {
  NODE_COLORS, NODE_LABELS, CREDIT_EDGE_TYPES, INFLUENCE_EDGE_TYPES,
  EDGE_COLOR_CREDIT, EDGE_COLOR_INFLUENCE,
  CHART_MUTED, CHART_GRID, formatCount, genreColor,
} from '../lib/palette'

const store = useAppStore()
const loading = ref(true)
const error = ref('')
const overview = ref(null)
const ego = ref(null)
const sailor = ref(null)
const search = ref('')
const graphMode = ref('credits')
const edgeMode = ref('all')
const pathMode = ref('upstream')
const selectedPath = ref(null)
const graphCard = ref(null)
const pathCard = ref(null)
const creditScope = ref(null)
const careerMode = ref('works')
const careerRows = ref([])
const careerLoading = ref(false)
const careerError = ref('')

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
  const collaboration = careerMode.value === 'collaboration' && careerRows.value.length
  const years = collaboration ? careerRows.value.map(row => row.year) : careerYears.value
  const perYear = collaboration
    ? careerRows.value.map(row => row.rolling.collaborator_count)
    : years.map(year => works.value.filter(work => work.node.release_year === year).length)
  let count = 0
  const cumulative = collaboration
    ? careerRows.value.map(row => row.cumulative.collaborator_count)
    : perYear.map(value => (count += value))
  const labels = collaboration ? ['累计合作者', '近五年活跃合作者'] : ['累计作品', '当年新作']
  return {
    animationDuration: 240,
    tooltip: { trigger: 'axis' },
    legend: { data: labels, top: 0, textStyle: { fontSize: 12, color: CHART_MUTED } },
    grid: { left: 41, right: 24, top: 42, bottom: 31 },
    xAxis: {
      type: 'category', data: years, boundaryGap: false,
      axisLabel: { fontSize: 10, color: CHART_MUTED },
      axisLine: { lineStyle: { color: CHART_GRID } },
    },
    yAxis: {
      type: 'value', name: collaboration ? '合作者' : '作品', nameTextStyle: { fontSize: 11, color: CHART_MUTED },
      axisLabel: { fontSize: 10, color: CHART_MUTED }, splitLine: { lineStyle: { color: CHART_GRID } },
    },
    series: [
      {
        name: labels[0], type: 'line', step: 'end', showSymbol: false,
        lineStyle: { width: 2.5, color: '#256c99' }, itemStyle: { color: '#256c99' },
        areaStyle: { color: 'rgba(37,108,153,0.11)' }, data: cumulative,
      },
      {
        name: labels[1], type: collaboration ? 'line' : 'bar', barMaxWidth: 12, symbolSize: 6,
        lineStyle: { width: 2, color: '#b36935' },
        itemStyle: { color: '#b36935', borderRadius: [3, 3, 0, 0] }, data: perYear,
      },
    ],
  }
})
function onCareerClick(params) {
  const year = careerOption.value.xAxis.data[params.dataIndex]
  if (year) store.setYearRange([year, year])
}
async function switchCareer(mode) {
  if (mode === 'works' || careerRows.value.length) {
    careerMode.value = mode
    return
  }
  if (careerLoading.value) return
  careerLoading.value = true
  careerError.value = ''
  try {
    const history = await dataService.networkDynamics()
    const rows = history.artists.find(artist => artist.id === sailor.value.focus_id)?.rows
    if (!rows?.length) throw new Error('当前截面没有可用的合作轨迹。')
    careerRows.value = rows
    careerMode.value = mode
  } catch (cause) {
    careerError.value = friendlyDataError(cause)
  } finally {
    careerLoading.value = false
  }
}

const topCollaborators = computed(() => (sailor.value?.collaborators || []).slice(0, 12))
const scoreCollaborators = computed(() => topCollaborators.value.map((item, index) => ({
  ...item, color: genreColor(index), type: nodeById.value.get(item.id)?.type ?? 'Person',
})))
const maxShared = computed(() => Math.max(1, ...topCollaborators.value.map(item => item.shared_work_count)))
const scopeWorks = computed(() => (creditScope.value?.ids ?? []).map(id => nodeById.value.get(id)).filter(Boolean)
  .sort((a, b) => (a.release_year ?? Infinity) - (b.release_year ?? Infinity) || a.id - b.id))
const scopePaths = computed(() => {
  const ids = creditScope.value?.ids ? new Set(creditScope.value.ids) : null
  return Object.fromEntries(['upstream', 'downstream'].map(side => {
    const rows = sailor.value?.[side + '_paths'] ?? []
    return [side, ids ? rows.filter(path => path.node_path?.some(id => ids.has(id))) : rows]
  }))
})
const paths = computed(() => scopePaths.value[pathMode.value])
const pathIds = computed(() => inInfluenceDirection(selectedPath.value?.event_ids))
const directedPathNodes = computed(() => inInfluenceDirection(selectedPath.value?.node_path))
const pathOnGraph = computed(() => (ego.value?.links || []).filter(link =>
  pathIds.value.includes(link.id)
  && visibleEdgeTypes.value.includes(link.type)
  && visibleTypes.value.includes(nodeById.value.get(link.source)?.type)
  && visibleTypes.value.includes(nodeById.value.get(link.target)?.type),
).length)

const searchResults = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query || !ego.value) return []
  return ego.value.nodes
    .filter(node => (node.display_name || node.name || '').toLowerCase().includes(query))
    .slice(0, 8)
})

function selectNode(node) {
  selectedPath.value = null
  creditScope.value = null
  if (!node) return store.clearFocus()
  store.selectNode(node)
}
function pickCollaborator(item) {
  const node = nodeById.value.get(item.id) || {
    id: item.id, name: item.name, display_name: item.name, type: 'Person',
  }
  if (!visibleTypes.value.includes(node.type)) visibleTypes.value = [...visibleTypes.value, node.type]
  selectNode(node)
  creditScope.value = { name: item.name, ids: item.work_ids, isCollaborator: true }
}
function pickCreditWork(node) {
  selectNode(node)
  creditScope.value = { name: node.display_name || node.name, ids: [node.id], isCollaborator: false }
}
function switchGraph(mode) {
  graphMode.value = mode
  if (mode === 'credits') selectedPath.value = null
}
function pickPath(path) {
  switchGraph('network')
  selectedPath.value = path
  edgeMode.value = 'influence'
  visibleTypes.value = Object.keys(NODE_COLORS)
  const last = (path.node_path || []).at(-1)
  const node = nodeById.value.get(last)
  if (node) store.selectNode(node)
}
function switchPathMode(mode) {
  pathMode.value = mode
  selectedPath.value = null
}
function inInfluenceDirection(items = []) {
  return pathMode.value === 'upstream' ? [...items].reverse() : items
}
function pathLabel(path) {
  return inInfluenceDirection(path.node_path).map(id => {
    const node = nodeById.value.get(id)
    return node ? (node.display_name || node.name) : String(id)
  }).join(' → ')
}
function pickSearchResult(node) {
  const collaborator = scoreCollaborators.value.find(item => item.id === node.id)
  if (collaborator) pickCollaborator(collaborator)
  else if (works.value.some(work => work.id === node.id)) pickCreditWork(node)
  else {
    switchGraph('network')
    selectNode(node)
  }
  if (!visibleTypes.value.includes(node.type)) visibleTypes.value = [...visibleTypes.value, node.type]
  search.value = ''
}

const notableTotal = computed(() => overview.value?.chart_status?.notable ?? 0)
const missingChartYear = computed(() => overview.value?.chart_status?.notable_without_year ?? 0)
const components = computed(() => overview.value?.counts?.weak_components ?? 16)
</script>

<template>
  <div class="atlas-analysis atlas-sailor">
    <div v-if="loading" class="op-state">正在加载 Sailor Shift 关系网络…</div>
    <div v-else-if="error" class="op-state error">
      {{ error }}<br><code>python -m pipeline.run</code>
    </div>

    <template v-else>
      <header class="journal-opening">
        <span class="journal-folio" aria-label="第 01 章">01</span>
        <div class="journal-lede">
          <h1>Sailor Shift 的合作者</h1>
          <p v-if="topCollaborators.length"><strong>{{ topCollaborators[0].name }}</strong> 与 Sailor Shift 共同署名 {{ topCollaborators[0].shared_work_count }} 部作品，是这张谱上共同署名最多的合作者。</p>
          <p v-else>从有发行年份的署名作品追查她的合作关系。</p>
        </div>
        <aside class="journal-margin" aria-label="人物特写口径">
          <p><strong>{{ works.length }} 部</strong>有发行年份的直接署名作品</p>
          <p><strong>{{ sailor.collaborators.length }} 位</strong>共同署名合作者</p>
        </aside>
      </header>

      <details class="op-card atlas-filter-card atlas-genre-filters">
        <summary><span>筛选实体与年份</span><small>{{ yearRange[0] === yearRange[1] ? yearRange[0] + ' 年' : yearRange.join('—') }}</small></summary>
        <div class="op-toolbar">
          <FilterPanel v-model="visibleTypes" label="实体类型" :options="typeOptions" />
          <div v-if="graphMode === 'network'" class="op-chips" role="group" aria-label="关系类型">
            <button
              v-for="mode in edgeModes" :key="mode.key" type="button"
              class="op-chip" :class="{ on: edgeMode === mode.key }"
              :aria-pressed="edgeMode === mode.key"
              @click="edgeMode = mode.key"
            >{{ mode.label }}</button>
          </div>
        </div>
        <div class="op-toolbar">
          <TimeScrubber v-model="yearRange" :min="overview.year_fields.release_year.min" :max="overview.meta.cutoff_year" />
          <input v-model="search" class="op-input" type="search" aria-label="搜索两跳网络"
            placeholder="搜索网络中的实体" @keydown.enter.prevent="searchResults[0] && pickSearchResult(searchResults[0])">
          <div v-if="searchResults.length" class="op-chips">
            <button
              v-for="node in searchResults" :key="node.id" type="button"
              class="op-chip" @click="pickSearchResult(node)"
            >{{ node.display_name || node.name }}</button>
          </div>
        </div>
      </details>

      <div class="op-grid two atlas-graph-grid" :class="{ 'journal-credit-layout': graphMode === 'credits' }">
        <section ref="graphCard" class="op-card atlas-ego-card">
          <header>
            <div>
              <h3>{{ graphMode === 'credits' ? '共同署名谱' : '两跳关系网络' }}</h3>
              <p>{{ graphMode === 'credits' ? '按发行年份从上往下读，沿弧线追踪同一位合作者' : ego.nodes.length + ' 节点 · ' + ego.links.length + ' 条边' }}</p>
            </div>
            <div class="atlas-segments" role="group" aria-label="Sailor Shift 主图">
              <button type="button" :aria-pressed="graphMode === 'credits'" @click="switchGraph('credits')">署名谱</button>
              <button type="button" :aria-pressed="graphMode === 'network'" @click="switchGraph('network')">两跳网络</button>
            </div>
          </header>
          <div v-if="graphMode === 'credits'" class="op-legend atlas-graph-key">
            <span><i style="background: #235c78" />歌曲</span>
            <span><i style="background: #aa5639" />专辑</span>
            <span><i class="line" style="background: #537e85" />颜色与右侧合作者名录对应</span>
          </div>
          <div v-else class="op-legend atlas-graph-key">
            <span><i class="line" :style="{ background: EDGE_COLOR_INFLUENCE }" />音乐影响 · 来源 → 受影响者</span>
            <span><i class="line" :style="{ background: EDGE_COLOR_CREDIT }" />署名、录制与成员</span>
            <span>跳数按完整网络计算 · 年份筛选淡出区间外作品</span>
          </div>
          <div v-if="selectedPath" class="atlas-path-status">
            <span>图中显示 {{ pathOnGraph }} / {{ pathIds.length }} 条路径边</span>
            <button type="button" class="atlas-inline" @click="selectedPath = null">清除路径</button>
          </div>
          <CreditScore v-if="graphMode === 'credits'"
            :works="works" :collaborators="scoreCollaborators" :year-range="yearRange"
            :focus-id="focusId" :visible-types="visibleTypes"
            @work="pickCreditWork" @collaborator="pickCollaborator" @year="year => store.setYearRange([year, year])"
          />
          <ForceGraph v-else
            :nodes="ego.nodes || []" :links="ego.links || []"
            :visible-types="visibleTypes" :visible-edge-types="visibleEdgeTypes"
            :year-range="yearRange" :anchor-id="sailor.focus_id" :focus-id="focusId"
            :path-ids="pathIds" :path-nodes="directedPathNodes"
            @select="selectNode"
          />
        </section>

        <div class="op-grid journal-credit-index">
          <section v-if="creditScope" class="op-card journal-credit-evidence" aria-label="署名与影响证据">
            <header><h3>{{ creditScope.name }}</h3><p>{{ creditScope.isCollaborator ? '共同署名记录' : '作品影响记录' }}</p></header>
            <ul v-if="creditScope.isCollaborator">
              <li v-for="work in scopeWorks" :key="work.id">
                <button type="button" class="atlas-path-link" @click="pickCreditWork(work)">{{ work.display_name || work.name }}</button>
                <span>{{ work.release_year ?? '年份未知' }}</span>
              </li>
            </ul>
            <button type="button" class="atlas-inline" @click="pathCard?.scrollIntoView({ block: 'start' })">
              涉及这些作品的路径 · 上游 {{ scopePaths.upstream.length }} / 下游 {{ scopePaths.downstream.length }}
              <AppIcon name="arrow" :size="15" />
            </button>
          </section>
          <DetailCard
            :node="store.focusNode" :degree="focusDegree" :link-types="focusLinkTypes"
            @close="selectNode(null)" @jump="store.focusGenre"
          />
          <section class="op-card">
            <header><h3>共同署名合作者 Top 12</h3><p>按共同作品数 · 点击聚焦</p></header>
            <button
              v-for="item in scoreCollaborators" :key="item.id"
              type="button" class="op-bar-row atlas-collab-row"
              :aria-pressed="focusId === item.id" @click="pickCollaborator(item)"
            >
              <span class="op-bar-name" :title="item.name">{{ item.name }}</span>
              <div class="op-bar-track">
                <div class="op-bar-fill" :style="{ width: `${(item.shared_work_count / maxShared) * 100}%`, background: item.color }" />
              </div>
              <span class="op-bar-value">{{ item.shared_work_count }}</span>
            </button>
            <p class="op-note">共同署名只说明参与同一作品，不代表私人关系；同一作品上的多个署名角色只计一次合作。</p>
          </section>
        </div>
      </div>

      <div class="journal-interlude">
        <h2>从共同署名追到引用</h2>
        <p>署名谱记录谁一起做过作品。影响路径则沿引用边追查作品的来源和去向，点击路径可查看原始边 ID。</p>
      </div>
      <div class="op-grid even">
        <section class="op-card">
          <header>
            <h3>职业时间谱</h3>
            <div class="atlas-segments" role="group" aria-label="职业时间谱指标">
              <button type="button" :aria-pressed="careerMode === 'works'" @click="switchCareer('works')">作品</button>
              <button type="button" :aria-pressed="careerMode === 'collaboration'" :disabled="careerLoading"
                @click="switchCareer('collaboration')">{{ careerLoading ? '读取中' : '合作' }}</button>
            </div>
          </header>
          <p v-if="careerError" class="atlas-subtle" role="status">{{ careerError }}</p>
          <ChartPanel :option="careerOption" height="282px" @chart-click="onCareerClick" />
        </section>
        <section ref="pathCard" class="op-card journal-path-card">
          <header>
            <h3>影响路径</h3>
            <div class="atlas-segments" role="group" aria-label="路径方向">
              <button type="button" :aria-pressed="pathMode === 'upstream'" @click="switchPathMode('upstream')">上游</button>
              <button type="button" :aria-pressed="pathMode === 'downstream'" @click="switchPathMode('downstream')">下游</button>
            </div>
          </header>
          <div v-if="creditScope" class="atlas-path-status">
            <span>涉及 {{ creditScope.name }} 的{{ creditScope.isCollaborator ? '共同署名作品' : '作品' }} · {{ paths.length }} 条</span>
            <button type="button" class="atlas-inline" @click="creditScope = null; selectedPath = null">查看全部路径</button>
          </div>
          <div v-if="selectedPath" class="atlas-path-evidence">
            <span>{{ pathLabel(selectedPath) }}</span>
            <div><code v-for="id in pathIds" :key="id">{{ id }}</code></div>
            <button v-if="pathOnGraph" type="button" class="atlas-inline" @click="graphCard?.scrollIntoView({ block: 'start' })">
              定位到关系图<AppIcon name="arrow" :size="15" />
            </button>
          </div>
          <div class="op-scroll">
            <table class="op-table">
              <thead><tr><th>来源 → 受影响者</th><th class="num">跳数</th><th class="num">事件年份</th></tr></thead>
              <tbody>
                <tr v-for="path in paths" :key="path.id" :class="{ 'atlas-picked': selectedPath?.id === path.id }">
                  <td><button type="button" class="atlas-path-link" :aria-pressed="selectedPath?.id === path.id"
                    @click="pickPath(path)">{{ pathLabel(path) }}</button></td>
                  <td class="num">{{ path.hops }}</td>
                  <td class="num">{{ inInfluenceDirection(path.event_years).map(year => year ?? '未知').join(' / ') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!paths.length" class="atlas-subtle">{{ creditScope ? '这些作品没有记录到该方向的影响路径。' : '当前数据截面没有该方向的影响路径。' }}</p>
        </section>
      </div>

      <div class="journal-interlude"><h2>读图笔记</h2></div>
      <div class="op-insights journal-notes">
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
      <JournalPager module="influence" />
    </template>
  </div>
</template>
