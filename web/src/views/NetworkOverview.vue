<script setup>
import { computed, nextTick, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { dataService } from '../lib/dataService'
import { useAppStore } from '../stores/useAppStore'
import { EDGE_LABELS, FLOW_TYPES, GENRE_PALETTE, NODE_COLORS, NODE_LABELS, formatCount } from '../lib/palette'
import { FLOW_TONES, HOME_GENRE, summarizeNeighbors } from '../lib/atlas'
import AppIcon from '../components/AppIcon.vue'
import CitationPoster from '../components/CitationPoster.vue'
import JournalPager from '../components/JournalPager.vue'
import GenreOrbit from '../components/GenreOrbit.vue'
import NetworkCanvas from '../components/NetworkCanvas.vue'

const store = useAppStore()
const overview = shallowRef(null)
const entityGraph = shallowRef(null)
const flows = shallowRef([])
const citationSummary = computed(() => {
  const byYear = new Map()
  let total = 0
  for (const row of flows.value) {
    byYear.set(row.year, (byYear.get(row.year) ?? 0) + row.value)
    total += row.value
  }
  const peak = [...byYear].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0]
  return { total, peak }
})
const loading = ref(true)
const error = ref('')
const mode = ref('genres')
const projection = ref('orbit')
const genreId = ref(HOME_GENRE)
const peerId = ref('')
const entityId = ref(17255)
const direction = ref('all')
const relation = ref('all')
const entityTypes = ref(Object.keys(NODE_COLORS))
const search = ref('')
const searchOpen = ref(false)
const searchBox = ref(null)
const workbench = ref(null)
const fullscreen = ref(false)
const fullscreenError = ref('')
const documentFullscreenEnabled = document.fullscreenEnabled
const playing = ref(false)
const evidenceOpen = ref(false)
const evidenceLoading = ref(false)
const evidenceError = ref('')
const evidenceIndex = shallowRef(null)
const reducedQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
const compactQuery = window.matchMedia('(max-width: 620px)')
const reduced = ref(reducedQuery.matches)
const compact = ref(compactQuery.matches)
let playTimer = 0

function updatePreferences() {
  reduced.value = reducedQuery.matches
  compact.value = compactQuery.matches
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [summary, network, genreFlows] = await Promise.all([
      dataService.overview(), dataService.network(), dataService.genreFlows(),
    ])
    overview.value = summary
    entityGraph.value = network
    flows.value = genreFlows.flows.filter(row => row.year != null && row.source !== row.target)
    if (!genres.value.some(node => node.id === genreId.value)) genreId.value = genres.value[0]?.id ?? ''
    if (!network.nodes.some(node => node.id === entityId.value)) entityId.value = network.nodes[0]?.id ?? null
    if (!genres.value.length) mode.value = 'entities'
  } catch (cause) {
    error.value = cause.message
  } finally {
    loading.value = false
    await nextTick()
    document.documentElement.dataset.ready = '1'
  }
}

onMounted(() => {
  reducedQuery.addEventListener('change', updatePreferences)
  compactQuery.addEventListener('change', updatePreferences)
  document.addEventListener('fullscreenchange', syncFullscreen)
  load()
})
onDeactivated(pause)
onBeforeUnmount(() => {
  pause()
  reducedQuery.removeEventListener('change', updatePreferences)
  compactQuery.removeEventListener('change', updatePreferences)
  document.removeEventListener('fullscreenchange', syncFullscreen)
})

function syncFullscreen() {
  fullscreen.value = !!workbench.value && document.fullscreenElement === workbench.value
}
async function toggleFullscreen() {
  fullscreenError.value = ''
  try {
    if (fullscreen.value) await document.exitFullscreen()
    else await workbench.value.requestFullscreen()
  } catch {
    fullscreenError.value = '浏览器未允许全屏显示。'
  }
}

const genres = computed(() => Object.entries(overview.value?.genre_work_counts ?? {}).map(([id, value], index) => ({
  id, name: id, value, type: 'Genre', color: GENRE_PALETTE[index % GENRE_PALETTE.length],
  radius: 7 + Math.sqrt(value) * .32,
})))
const genresById = computed(() => new Map(genres.value.map(node => [node.id, node])))
const activeGenre = computed(() => genresById.value.get(genreId.value))
const entity = computed(() => entityGraph.value?.nodes.find(node => node.id === entityId.value))
const entityEdges = computed(() => (entityGraph.value?.links ?? []).filter(
  link => link.source === entityId.value || link.target === entityId.value,
))
const observedRange = computed(() => [
  overview.value?.year_fields.release_year.min ?? 1975,
  overview.value?.meta.cutoff_year ?? 2040,
])
const years = computed(() => Array.from(
  { length: observedRange.value[1] - observedRange.value[0] + 1 },
  (_, index) => observedRange.value[0] + index,
))
const yearRange = computed(() => {
  const [min, max] = observedRange.value
  const start = Math.min(max, Math.max(min, store.yearRange[0]))
  return [start, Math.min(max, Math.max(start, store.yearRange[1]))]
})
const motion = computed(() => store.motionEnabled && !reduced.value)
watch(motion, enabled => { if (!enabled) pause() })
const relationFlows = computed(() => flows.value.filter(row => relation.value === 'all' || row.type === relation.value))
const windowFlows = computed(() => relationFlows.value.filter(row => row.year >= yearRange.value[0]
  && row.year <= yearRange.value[1]))
const neighbors = computed(() => summarizeNeighbors(windowFlows.value, genreId.value))
const timeHover = ref(null)
const previewNeighbors = computed(() => {
  const period = timeHover.value
  if (!period) return null
  return summarizeNeighbors(relationFlows.value.filter(row => row.year >= period.start && row.year <= period.end), genreId.value)
})
const pair = computed(() => peerId.value ? neighbors.value.get(peerId.value) : null)
const totals = computed(() => [...neighbors.value.values()].reduce(
  (sum, row) => ({ in: sum.in + row.in, out: sum.out + row.out }), { in: 0, out: 0 },
))
const ranked = computed(() => {
  const score = row => direction.value === 'all' ? row.in + row.out : row[direction.value]
  return [...neighbors.value.values()].filter(score)
    .sort((a, b) => score(b) - score(a) || a.id.localeCompare(b.id)).slice(0, 4)
})
const availableDirections = [
  { id: 'all', label: '双向' }, { id: 'in', label: '灵感流入' }, { id: 'out', label: '影响流出' },
]

const spatialNodes = computed(() => {
  const home = genres.value.find(node => node.id === HOME_GENRE) ?? genres.value[0]
  const around = genres.value.filter(node => node !== home)
  const placed = around.map((node, index) => {
    const phi = Math.acos(1 - 2 * (index + .5) / around.length)
    const theta = index * Math.PI * (3 - Math.sqrt(5))
    return { ...node, x: 300 * Math.sin(phi) * Math.cos(theta), y: 300 * Math.cos(phi), z: 300 * Math.sin(phi) * Math.sin(theta) }
  })
  return home ? [{ ...home, x: 0, y: 0, z: 0, color: '#8fd7f8' }, ...placed] : placed
})
const spatialGraph = computed(() => {
  if (mode.value === 'entities') return entityGraph.value
  const links = new Map()
  for (const row of windowFlows.value) {
    const id = row.source + '|' + row.target
    if (!links.has(id)) links.set(id, { id, source: row.source, target: row.target, type: 'genre-flow', value: 0 })
    links.get(id).value += row.value
  }
  return { nodes: spatialNodes.value, links: [...links.values()] }
})

const searchResults = computed(() => {
  const q = search.value.trim().toLocaleLowerCase()
  if (!q) return []
  return [...genres.value, ...(entityGraph.value?.nodes ?? [])].filter(node =>
    (node.display_name || node.name).toLocaleLowerCase().includes(q) || String(node.id) === q,
  ).slice(0, 8)
})
function handleSearchKey(event) {
  if (event.isComposing) return
  if (event.key === 'Escape') searchOpen.value = false
  if (event.key === 'Enter' && searchResults.value.length) {
    event.preventDefault()
    pickSearch(searchResults.value[0])
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    searchBox.value?.querySelector('.atlas-search-results button')?.focus()
  }
}
function closeSearch(event) {
  if (!searchBox.value?.contains(event.relatedTarget)) searchOpen.value = false
}
function pickSearch(node) {
  mode.value = node.type === 'Genre' ? 'genres' : 'entities'
  if (node.type === 'Genre') focusGenre(node.id)
  else {
    selectEntity(node)
    if (!entityTypes.value.includes(node.type)) entityTypes.value = [...entityTypes.value, node.type]
  }
  search.value = ''
  searchOpen.value = false
}
function switchMode(value) {
  pause()
  mode.value = value
  searchOpen.value = false
  timeHover.value = null
}
function setProjection(value) {
  pause()
  projection.value = value
  peerId.value = ''
  timeHover.value = null
}
function focusGenre(id) {
  if (!genresById.value.has(id)) return
  pause()
  genreId.value = id
  peerId.value = ''
  timeHover.value = null
}
function selectPeer(id) {
  peerId.value = peerId.value === id ? '' : id
}
function selectEntity(node) {
  entityId.value = node?.id ?? null
}
function toggleType(type) {
  const types = entityTypes.value
  entityTypes.value = types.includes(type) ? types.filter(key => key !== type) : [...types, type]
  if (entity.value && !entityTypes.value.includes(entity.value.type)) entityId.value = null
}
function openAnalysis(node = activeGenre.value) {
  if (!node) return
  pause()
  if (node.type === 'Genre') {
    store.focusGenres = [...new Set([node.id, ...(peerId.value ? [peerId.value] : [])])]
    store.visibleFlowTypes = relation.value === 'all' ? [...FLOW_TYPES] : [relation.value]
    store.setModule('genre')
  } else {
    store.selectNode(node.id === 17255 ? { ...node, genre: HOME_GENRE } : node)
    store.setModule('influence')
  }
}
function spatialSelect(node) {
  if (mode.value === 'entities') selectEntity(node)
  else if (node) focusGenre(node.id)
}

const yearSignals = computed(() => {
  const byYear = new Map(years.value.map(year => [year, { year, in: 0, out: 0, types: {} }]))
  for (const row of relationFlows.value) {
    const signal = byYear.get(row.year)
    if (!signal) continue
    const side = row.target === genreId.value ? 'in' : row.source === genreId.value ? 'out' : ''
    if (!side) continue
    signal[side] += row.value
    signal.types[row.type] ??= { in: 0, out: 0 }
    signal.types[row.type][side] += row.value
  }
  return [...byYear.values()]
})
const timeBins = computed(() => {
  const step = compact.value ? 3 : 1
  const bins = []
  for (let i = 0; i < yearSignals.value.length; i += step) {
    const group = yearSignals.value.slice(i, i + step)
    bins.push({
      start: group[0].year, end: group.at(-1).year,
      in: group.reduce((total, row) => total + row.in, 0),
      out: group.reduce((total, row) => total + row.out, 0),
    })
  }
  return bins
})
const maxSignal = computed(() => Math.max(1, ...timeBins.value.flatMap(row => [row.in, row.out])))
const firstSignal = computed(() => yearSignals.value.find(row => row.in || row.out)?.year)
function formatPeriod(start, end) { return start === end ? String(start) : start + '—' + end }
function setWindow(start, end) {
  pause()
  timeHover.value = null
  store.setYearRange([start, end])
}
function browseAtlas() {
  workbench.value?.focus({ preventScroll: true })
  workbench.value?.scrollIntoView({ block: 'start', behavior: motion.value ? 'smooth' : 'instant' })
}
function exploreYear(year) {
  switchMode('genres')
  setProjection('orbit')
  setWindow(year, year)
  const rows = relationFlows.value.filter(row => row.year === year)
  if (rows.length) {
    const focus = rows.some(row => row.source === genreId.value || row.target === genreId.value)
      ? genreId.value
      : rows.reduce((best, row) => row.value > best.value ? row : best).source
    focusGenre(focus)
    direction.value = 'all'
    const peers = [...summarizeNeighbors(rows, focus).values()]
    peerId.value = peers.sort((a, b) => b.in + b.out - a.in - a.out || a.id.localeCompare(b.id))[0]?.id ?? ''
  }
  browseAtlas()
}
function setBound(side, value) {
  const year = Number(value)
  const [start, end] = yearRange.value
  if (side === 0) setWindow(year, Math.max(end, year))
  else setWindow(Math.min(start, year), year)
}
function pause() {
  clearInterval(playTimer)
  playTimer = 0
  playing.value = false
}
function togglePlay() {
  if (playing.value) return pause()
  if (!motion.value || firstSignal.value == null) return
  const [min, max] = observedRange.value
  const lastStart = Math.max(min, max - 4)
  const [start, end] = yearRange.value
  let cursor = end - start === 4 && start >= firstSignal.value && start < lastStart
    ? start : Math.min(firstSignal.value, lastStart)
  store.setYearRange([cursor, Math.min(cursor + 4, max)])
  if (cursor === lastStart) return
  playing.value = true
  playTimer = window.setInterval(() => {
    cursor += 1
    store.setYearRange([cursor, Math.min(cursor + 4, max)])
    if (cursor === lastStart) pause()
  }, 800)
}
function binTitle(bin) {
  return formatPeriod(bin.start, bin.end) + ' 年 · 流入 ' + bin.in + ' · 流出 ' + bin.out
}

watch([peerId, genreId], () => { evidenceOpen.value = false })
const evidenceFlows = computed(() => (pair.value?.rows ?? []).filter(row => direction.value === 'all'
  || (direction.value === 'in' ? row.target === genreId.value : row.source === genreId.value)))
const evidenceCount = computed(() => evidenceFlows.value.reduce((sum, row) => sum + row.value, 0))
const evidenceRows = computed(() => {
  if (!evidenceIndex.value || !evidenceOpen.value) return []
  const { events, nodes } = evidenceIndex.value
  return [...evidenceFlows.value].sort((a, b) => b.year - a.year)
    .flatMap(row => row.event_ids).slice(0, 6).flatMap(id => {
      const event = events.get(id)
      if (!event) return []
      const name = entityId => nodes.get(entityId)?.display_name || nodes.get(entityId)?.name || '#' + entityId
      return [{ ...event, sourceName: name(event.source), targetName: name(event.target) }]
    })
})
async function toggleEvidence() {
  if (evidenceOpen.value && !evidenceError.value) {
    evidenceOpen.value = false
    return
  }
  evidenceOpen.value = true
  if (evidenceIndex.value || evidenceLoading.value) return
  evidenceError.value = ''
  evidenceLoading.value = true
  try {
    const [events, nodes] = await Promise.all([dataService.influenceEvents(), dataService.nodeIndex()])
    evidenceIndex.value = {
      events: new Map(events.events.map(row => [row.id, row])),
      nodes: new Map(nodes.nodes.map(node => [node.id, node])),
    }
  } catch (cause) {
    evidenceError.value = cause.message
  } finally {
    evidenceLoading.value = false
  }
}
</script>

<template>
  <div v-if="loading || error" class="op-state" :class="{ error }" role="status">
    <template v-if="error">
      <p>全景图谱加载失败。{{ error }}</p>
      <button type="button" class="atlas-button" @click="load">重新加载</button>
    </template>
    <template v-else>正在加载音乐图谱…</template>
  </div>
  <section v-else id="overview" class="atlas-overview" aria-labelledby="atlas-heading">
    <div class="wrap">
      <div class="atlas-cover hero">
        <header class="atlas-cover-title">
          <h1 id="atlas-heading"><span lang="en">Oceanus</span>音乐图志</h1>
          <p v-if="citationSummary.peak">
            <strong class="atlas-cover-finding">{{ citationSummary.peak[0] }} 年</strong>留下 {{ formatCount(citationSummary.peak[1]) }} 条跨流派引用，是观测期最密集的一年。
          </p>
          <p class="atlas-cover-guide">沿外圈读年份，五道刻纹区分引用类型。{{ formatCount(citationSummary.total) }} 个点各对应一条引用，大小按同年同类流派对的频次分级。细线随年度引用量起伏。</p>
          <button type="button" class="atlas-button atlas-cover-action" @click="browseAtlas">
            浏览引用图谱<AppIcon name="arrow" :size="17" />
          </button>
        </header>
        <CitationPoster :flows="flows" :years="years" :relation="relation" @year="exploreYear" @relation="relation = $event" />
      </div>

      <header class="atlas-page-heading atlas-explorer-heading">
        <div>
          <h2>流派与作品</h2>
          <p>在关系图中追查灵感来源、影响去向和原始作品。</p>
        </div>
        <dl class="atlas-head-facts" aria-label="数据规模">
          <div><dt>音乐实体</dt><dd>{{ formatCount(overview.counts.nodes) }}</dd></div>
          <div><dt>原始关系</dt><dd>{{ formatCount(overview.counts.links) }}</dd></div>
          <div><dt>流派</dt><dd>{{ genres.length }}</dd></div>
        </dl>
      </header>

      <div ref="workbench" class="app-frame atlas-workspace" tabindex="-1" aria-label="引用关系工作台">
        <div class="atlas-toolbar">
          <div class="atlas-segments" role="group" aria-label="图谱内容">
            <button type="button" :aria-pressed="mode === 'genres'" :disabled="!genres.length" @click="switchMode('genres')">
              <AppIcon name="flow" :size="16" />流派关系
            </button>
            <button type="button" :aria-pressed="mode === 'entities'" @click="switchMode('entities')">
              <AppIcon name="graph" :size="16" />音乐实体
            </button>
          </div>
          <div ref="searchBox" class="atlas-search" @focusout="closeSearch" @keydown.esc="searchOpen = false">
            <AppIcon name="search" :size="17" />
            <input v-model="search" type="search" placeholder="搜索流派、音乐人或作品"
              aria-label="搜索图谱" autocomplete="off" @focus="searchOpen = true" @input="searchOpen = true"
              @keydown="handleSearchKey" />
            <div v-if="searchOpen && search.trim()" class="atlas-search-results">
              <button v-for="node in searchResults" :key="node.id" type="button" @click="pickSearch(node)">
                <span>{{ node.display_name || node.name }}</span>
                <small>{{ node.type === 'Genre' ? '流派' : NODE_LABELS[node.type] }}</small>
              </button>
              <p v-if="!searchResults.length" role="status">当前图谱没有匹配的名称。</p>
            </div>
          </div>
          <div v-if="mode === 'genres'" class="atlas-segments" role="group" aria-label="图谱视角">
            <button type="button" :aria-pressed="projection === 'orbit'" @click="setProjection('orbit')">环形图</button>
            <button type="button" :aria-pressed="projection === 'spatial'" @click="setProjection('spatial')">空间图</button>
          </div>
        </div>

        <div class="atlas-map-grid" :class="{ 'is-orbit': mode === 'genres' && projection === 'orbit' }">
          <div class="atlas-plot">
            <div v-if="mode === 'genres'" class="atlas-plot-controls">
              <div class="atlas-direction" role="group" aria-label="影响方向">
                <button v-for="item in availableDirections" :key="item.id" type="button"
                  :aria-pressed="direction === item.id" @click="direction = item.id">
                  <i v-if="item.id !== 'all'" :style="{ background: FLOW_TONES[item.id] }" aria-hidden="true" />
                  {{ item.label }}
                </button>
              </div>
              <select v-model="relation" aria-label="引用类型" @change="pause">
                <option value="all">全部引用类型</option>
                <option v-for="type in FLOW_TYPES" :key="type" :value="type">{{ EDGE_LABELS[type] }}</option>
              </select>
              <button v-if="genreId !== HOME_GENRE && genresById.has(HOME_GENRE)" type="button"
                class="atlas-inline" @click="focusGenre(HOME_GENRE)">
                <AppIcon name="reset" :size="15" />回到 Oceanus Folk
              </button>
              <div class="atlas-plot-tools">
                <details class="atlas-plot-key">
                  <summary><AppIcon name="info" :size="15" />读图</summary>
                  <div>内圈弧段长度随收录作品数变化，弦带显示引用方向与数量。外圈按年排列，蓝色向外为流出，暖色向内为流入。宽屏彩点标出引用类型。指向流派可追查年份，指向年份可预览关系，点击年份锁定时间窗。</div>
                </details>
                <button v-if="(projection === 'orbit' && documentFullscreenEnabled) || fullscreen" type="button" class="atlas-inline"
                  :aria-pressed="fullscreen" @click="toggleFullscreen">
                  <AppIcon name="expand" :size="15" />{{ fullscreen ? '退出全屏' : '全屏' }}
                </button>
              </div>
            </div>
            <div v-else class="atlas-plot-controls atlas-type-controls" role="group" aria-label="实体类型">
              <button v-for="(color, type) in NODE_COLORS" :key="type" type="button"
                :aria-pressed="entityTypes.includes(type)" @click="toggleType(type)">
                <i :style="{ background: color }" aria-hidden="true" />{{ NODE_LABELS[type] }}
              </button>
              <button v-if="fullscreen" type="button" class="atlas-inline" @click="toggleFullscreen">
                <AppIcon name="expand" :size="15" />退出全屏
              </button>
            </div>
            <p v-if="fullscreenError" class="atlas-fullscreen-error" role="status">{{ fullscreenError }}</p>
            <div class="atlas-stage">
              <GenreOrbit v-if="mode === 'genres' && projection === 'orbit'" :genres="genres"
                :focus="genreId" :neighbors="neighbors" :selected="peerId" :direction="direction"
                :motion="motion" :years="yearSignals" :year-range="yearRange"
                :preview="timeHover" :preview-neighbors="previewNeighbors"
                @select="selectPeer" @focus="focusGenre" @year="year => setWindow(year, year)" @preview-year="timeHover = $event" />
              <div v-else class="network-stage atlas-spatial" data-visual>
                <NetworkCanvas :nodes="spatialGraph.nodes" :links="spatialGraph.links"
                  :visible-types="mode === 'entities' ? entityTypes : null"
                  :focus-id="mode === 'genres' ? genreId : entityId"
                  :flow-direction="mode === 'genres' ? direction : 'all'"
                  :label="mode === 'genres' ? '流派空间图' : '音乐实体网络'"
                  @select="spatialSelect" @open="openAnalysis" />
              </div>
            </div>
          </div>

          <aside class="atlas-inspector" aria-label="图谱档案">
            <template v-if="mode === 'genres'">
              <div class="atlas-inspector-top">
                <span>{{ peerId ? '双向引用' : '流派档案' }}</span>
                <button v-if="peerId" type="button" class="atlas-inline" @click="peerId = ''">
                  <AppIcon name="close" :size="15" />关闭
                </button>
                <span v-else>{{ formatCount(activeGenre?.value) }} 部收录作品</span>
              </div>
              <h2>{{ peerId || genreId }}</h2>
              <p class="atlas-inspector-period">{{ formatPeriod(...yearRange) }} · {{ peerId ? '以 ' + genreId + ' 为焦点' : '跨流派引用' }}</p>
              <dl class="atlas-balance">
                <div><dt><i :style="{ background: FLOW_TONES.in }" />流入</dt><dd>{{ formatCount(peerId ? pair?.in ?? 0 : totals.in) }}</dd></div>
                <div><dt><i :style="{ background: FLOW_TONES.out }" />流出</dt><dd>{{ formatCount(peerId ? pair?.out ?? 0 : totals.out) }}</dd></div>
              </dl>
              <template v-if="peerId">
                <p v-if="!pair" class="atlas-subtle">当前时段和引用类型下没有记录。可以切换时段，或继续探索这个流派。</p>
                <div class="atlas-actions">
                  <button v-if="evidenceCount" type="button" class="atlas-button" :aria-expanded="evidenceOpen" @click="toggleEvidence">
                    {{ evidenceError ? '重试证据' : evidenceOpen ? '收起证据' : '查看引用证据' }}
                  </button>
                  <button type="button" class="atlas-inline" @click="focusGenre(peerId)">设为焦点<AppIcon name="arrow" :size="15" /></button>
                </div>
                <div v-if="evidenceOpen" class="atlas-evidence" aria-live="polite">
                  <p v-if="evidenceLoading">正在读取原始引用…</p>
                  <p v-else-if="evidenceError">{{ evidenceError }}</p>
                  <template v-else>
                    <span class="atlas-subtle">最近 {{ evidenceRows.length }} 条 · 共 {{ evidenceCount }} 条</span>
                    <article v-for="row in evidenceRows" :key="row.id">
                      <span>{{ row.year }} · {{ EDGE_LABELS[row.type] }}</span>
                      <strong>{{ row.sourceName }} → {{ row.targetName }}</strong>
                      <code>{{ row.id }}</code>
                    </article>
                  </template>
                </div>
              </template>
              <template v-else>
                <h3>关系最多的流派</h3>
                <div class="atlas-peer-list">
                  <button v-for="row in ranked" :key="row.id" type="button" @click="selectPeer(row.id)">
                    <span>{{ row.id }}</span>
                    <span class="atlas-pair-count">
                      <b>{{ row.in }}</b><b :style="{ color: FLOW_TONES.out }">{{ row.out }}</b>
                    </span>
                    <AppIcon name="arrow" :size="14" />
                  </button>
                  <p v-if="!ranked.length" class="atlas-subtle">当前筛选下没有跨流派引用。</p>
                </div>
              </template>
              <button type="button" class="atlas-button atlas-primary atlas-continue" @click="openAnalysis()">
                {{ peerId ? '比较两个流派' : '进入流派传播' }}<AppIcon name="arrow" :size="17" />
              </button>
            </template>
            <template v-else>
              <div class="atlas-inspector-top"><span>实体档案</span><span>{{ formatCount(entityGraph.nodes.length) }} 个概览节点</span></div>
              <template v-if="entity">
                <h2>{{ entity.display_name || entity.name }}</h2>
                <p class="atlas-inspector-period">{{ NODE_LABELS[entity.type] }} · #{{ entity.id }}</p>
                <dl class="atlas-entity-facts">
                  <div><dt>概览内关系</dt><dd>{{ entityEdges.length }}</dd></div>
                  <div v-if="entity.genre"><dt>流派</dt><dd>{{ entity.genre }}</dd></div>
                  <div><dt>发行年</dt><dd>{{ entity.release_year ?? '未知' }}</dd></div>
                </dl>
                <button type="button" class="atlas-button atlas-primary atlas-continue" @click="openAnalysis(entity)">
                  进入关系分析<AppIcon name="arrow" :size="17" />
                </button>
              </template>
              <p v-else class="atlas-subtle">选中实体后，可查看它的关系及作品资料。</p>
              <p class="atlas-subtle">概览优先包含 Sailor Shift 邻域与高连接实体。</p>
            </template>
          </aside>
        </div>

        <section v-if="mode === 'genres'" class="atlas-time" aria-labelledby="atlas-time-title">
          <div class="atlas-time-head">
            <div>
              <h2 id="atlas-time-title">引用时间谱</h2>
              <span aria-live="off">{{ timeHover ? binTitle(timeHover) : '按受影响作品发行年 · ' + formatPeriod(...yearRange) }}</span>
            </div>
            <div class="atlas-time-actions">
              <div class="atlas-time-window" role="group" aria-label="观测起止年">
                <select :value="yearRange[0]" aria-label="起始年" @change="setBound(0, $event.target.value)">
                  <option v-for="year in years" :key="year">{{ year }}</option>
                </select>
                <span>至</span>
                <select :value="yearRange[1]" aria-label="截止年" @change="setBound(1, $event.target.value)">
                  <option v-for="year in years" :key="year">{{ year }}</option>
                </select>
              </div>
              <button type="button" class="atlas-button" @click="setWindow(...observedRange)">全期</button>
              <button type="button" class="atlas-button" :disabled="!motion || firstSignal == null"
                :aria-pressed="playing" @click="togglePlay">
                <AppIcon :name="playing ? 'pause' : 'play'" :size="15" />{{ playing ? '暂停' : '播放五年窗' }}
              </button>
            </div>
          </div>
          <div class="atlas-signal" :style="{ '--bins': timeBins.length }" aria-label="逐年引用，点击选择时段">
            <button v-for="bin in timeBins" :key="bin.start" type="button" :title="binTitle(bin)"
              :aria-label="binTitle(bin)" :aria-pressed="bin.start <= yearRange[1] && bin.end >= yearRange[0]"
              :tabindex="bin.end >= yearRange[1] && bin.start <= yearRange[1] ? 0 : -1"
              @pointerenter="timeHover = bin" @pointerleave="timeHover = null"
              @focus="timeHover = bin" @blur="timeHover = null" @click="setWindow(bin.start, bin.end)"
              @keydown.left.prevent="$event.currentTarget.previousElementSibling?.focus()"
              @keydown.right.prevent="$event.currentTarget.nextElementSibling?.focus()">
              <i class="atlas-signal-out" :style="{ height: 46 * bin.out / maxSignal + '%' }" />
              <i class="atlas-signal-in" :style="{ height: 46 * bin.in / maxSignal + '%' }" />
            </button>
          </div>
          <div class="atlas-time-axis" aria-hidden="true">
            <span>{{ observedRange[0] }}</span>
            <span v-for="year in [1990, 2005, 2020].filter(y => y > observedRange[0] && y < observedRange[1])" :key="year"
              :style="{ left: (year - observedRange[0]) / (observedRange[1] - observedRange[0]) * 100 + '%' }">{{ year }}</span>
            <span>{{ observedRange[1] }}</span>
          </div>
        </section>
      </div>
      <JournalPager module="overview" />
    </div>
  </section>
</template>
