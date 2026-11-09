<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAppStore } from './stores/useAppStore'
import { dataService } from './lib/dataService'
import { NODE_LABELS } from './lib/palette'
import AppIcon from './components/AppIcon.vue'
import NetworkOverview from './views/NetworkOverview.vue'
import './styles/network.css'
import './styles/overview-scope.css'
import './styles/atlas.css'

const store = useAppStore()
const views = {
  overview: NetworkOverview,
  influence: defineAsyncComponent(() => import('./views/InfluenceTrace.vue')),
  genre: defineAsyncComponent(() => import('./views/GenreSpread.vue')),
  rising: defineAsyncComponent(() => import('./views/RisingStar.vue')),
}
const modules = [
  { key: 'overview', number: '00', label: '全景图谱' },
  { key: 'influence', number: '01', label: '影响力溯源' },
  { key: 'genre', number: '02', label: '流派传播' },
  { key: 'rising', number: '03', label: '新星预测' },
]
function moduleFromURL() {
  const key = new URLSearchParams(window.location.search).get('module')
  return Object.hasOwn(views, key) ? key : 'overview'
}
function readModule() { store.setModule(moduleFromURL()) }
readModule()

const currentView = computed(() => views[store.activeModule] || NetworkOverview)
const status = ref('loading')
const contract = ref(null)
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
function applyMotionPreference() {
  if (reducedMotion.matches) store.motionEnabled = false
}
applyMotionPreference()
function moduleHref(key) {
  const url = new URL(window.location.href)
  url.searchParams.set('module', key)
  return url.pathname + url.search
}
function navigate(event, key) {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  store.setModule(key)
}

onMounted(async () => {
  window.addEventListener('popstate', readModule)
  reducedMotion.addEventListener('change', applyMotionPreference)
  try {
    contract.value = (await dataService.manifest()).meta
    status.value = 'ok'
  } catch {
    status.value = 'missing'
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('popstate', readModule)
  reducedMotion.removeEventListener('change', applyMotionPreference)
})

watch(() => store.activeModule, async key => {
  if (moduleFromURL() !== key) window.history.pushState(null, '', moduleHref(key))
  window.scrollTo({ top: 0, behavior: 'auto' })
  await nextTick()
  window.dispatchEvent(new Event('resize'))
})
</script>

<template>
  <div class="op-app atlas-app">
    <a class="atlas-skip" href="#atlas-content">跳到分析内容</a>
    <header class="atlas-masthead">
      <div class="atlas-shell-width atlas-masthead-inner">
        <a class="atlas-brand" :href="moduleHref('overview')" aria-label="潮音脉全景图谱" @click="navigate($event, 'overview')">
          <svg viewBox="0 0 40 40" width="38" height="38" aria-hidden="true">
            <circle cx="20" cy="20" r="19" fill="#153e63" />
            <circle cx="20" cy="20" r="12" fill="none" stroke="#6cb0d4" stroke-width="1" />
            <path d="M8 22c4.6 0 4.8-7 9.6-7s5.2 9 9.8 9c2.5 0 3.6-2 4.6-4" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" />
            <circle cx="27.4" cy="24" r="2.3" fill="#f0bd82" />
          </svg>
          <span><strong>潮音脉</strong><small>OceanusPulse</small></span>
        </a>
        <nav class="atlas-nav" aria-label="分析模块">
          <a v-for="item in modules" :key="item.key" :href="moduleHref(item.key)"
            :aria-current="store.activeModule === item.key ? 'page' : undefined" @click="navigate($event, item.key)">
            <span>{{ item.number }}</span>{{ item.label }}
          </a>
        </nav>
        <div class="atlas-contract" :class="{ 'is-missing': status === 'missing' }" role="status">
          <i aria-hidden="true" />
          <span v-if="status === 'ok'">观测至 {{ contract.cutoff_year }}</span>
          <span v-else-if="status === 'loading'">读取数据</span>
          <span v-else>数据待生成</span>
        </div>
      </div>
    </header>

    <div v-if="store.focusNode" class="atlas-shell-width atlas-cross-focus" aria-label="跨模块焦点">
      <span>当前实体</span>
      <strong>{{ store.focusNode.name }}</strong>
      <span>{{ NODE_LABELS[store.focusNode.type] || store.focusNode.type }}</span>
      <button v-if="store.focusNode.genre && store.activeModule !== 'genre'" type="button"
        class="atlas-inline" @click="store.focusGenre(store.focusNode.genre)">
        查看 {{ store.focusNode.genre }}<AppIcon name="arrow" :size="15" />
      </button>
      <button type="button" class="atlas-inline" aria-label="清除实体焦点" @click="store.clearFocus()">
        <AppIcon name="close" :size="16" />
      </button>
    </div>

    <main id="atlas-content" class="op-main atlas-shell-width" :class="{ 'op-overview': store.activeModule === 'overview' }">
      <KeepAlive><component :is="currentView" /></KeepAlive>
    </main>

    <footer class="atlas-footer atlas-shell-width">
      <div><strong>OceanusPulse</strong><span>IEEE VAST Challenge 2025 · MC1 合成音乐知识图谱</span></div>
      <details>
        <summary>数据与方法</summary>
        <p>影响箭头由来源指向受影响作品。登榜记录指热门榜单收录，未知年份保留缺失。</p>
        <p v-if="contract">数据契约 v{{ contract.schema_version }} · 观测截点 {{ contract.cutoff_year }} · 随机种子 {{ contract.seed }}</p>
      </details>
    </footer>
  </div>
</template>
