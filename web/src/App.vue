<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useAppStore } from './stores/useAppStore'
import { dataService } from './lib/dataService'
import InfluenceTrace from './views/InfluenceTrace.vue'
import GenreSpread from './views/GenreSpread.vue'
import RisingStar from './views/RisingStar.vue'

const store = useAppStore()
const views = { influence: InfluenceTrace, genre: GenreSpread, rising: RisingStar }
const currentView = computed(() => views[store.activeModule] || views.influence)

const modules = [
  { key: 'influence', label: '模块一 · 影响力溯源', hint: '谁造就了 Sailor Shift' },
  { key: 'genre', label: '模块二 · 流派传播', hint: 'Oceanus Folk 如何走向世界' },
  { key: 'rising', label: '模块三 · 新星预测', hint: '下一个爆红的是谁' },
]

const status = ref('loading')
const contract = ref(null)

onMounted(async () => {
  const requested = new URLSearchParams(window.location.search).get('module')
  if (requested && views[requested]) store.setModule(requested)
  try {
    const manifest = await dataService.manifest()
    contract.value = manifest.meta
    status.value = 'ok'
  } catch {
    status.value = 'missing'
  }
})

watch(() => store.activeModule, async key => {
  const url = new URL(window.location.href)
  url.searchParams.set('module', key)
  window.history.replaceState({}, '', url)
  // KeepAlive 视图重新激活后 ECharts 需要重新读取容器尺寸。
  await nextTick()
  window.dispatchEvent(new Event('resize'))
})
</script>

<template>
  <div class="op-app">
    <header class="op-header">
      <div class="op-header-top">
        <div class="op-brand">
          <h1>OceanusPulse · 潮音脉</h1>
          <p>IEEE VAST Challenge 2025 · MC1 音乐产业知识图谱可视分析系统</p>
        </div>
        <div class="op-header-meta">
          <span class="op-meta-pill" :class="{ warn: status === 'missing' }">
            <template v-if="status === 'ok'">
              数据契约 v{{ contract.schema_version }} · 观测截点 {{ contract.cutoff_year }}
            </template>
            <template v-else-if="status === 'loading'">正在校验数据契约…</template>
            <template v-else>数据管线未就绪 · 请运行 python -m pipeline.run</template>
          </span>
          <span>17,412 节点 · 37,857 关系 · 固定随机种子 42</span>
        </div>
      </div>

      <div class="op-focus-bar">
        <span>跨模块焦点</span>
        <template v-if="store.focusNode">
          <span class="op-focus-chip">
            {{ store.focusNode.name }} · {{ store.focusNode.type }}
            <button type="button" title="清除焦点" @click="store.clearFocus()">×</button>
          </span>
          <button
            v-if="store.focusNode.genre"
            type="button"
            class="op-btn"
            @click="store.focusGenre(store.focusNode.genre)"
          >在流派传播中查看「{{ store.focusNode.genre }}」→</button>
        </template>
        <span v-else>点击任意节点或实体即可在模块间联动</span>
      </div>

      <nav class="op-tabs">
        <button
          v-for="item in modules"
          :key="item.key"
          type="button"
          class="op-tab"
          :class="{ active: store.activeModule === item.key }"
          @click="store.setModule(item.key)"
        >
          {{ item.label }}<small>{{ item.hint }}</small>
        </button>
      </nav>
    </header>

    <main class="op-main">
      <KeepAlive><component :is="currentView" /></KeepAlive>
    </main>

    <footer class="op-footer">
      数据来源：IEEE VAST Challenge 2025 MC1 官方合成知识图谱；全部指标由 <code>pipeline/</code> 可复现生成（<code>python -m pipeline.run</code>、<code>python pipeline/features.py</code>）。
      口径提示：<code>notable</code> 仅表示登过热榜，不代表冠军或销量；缺失的登榜年份保持未知，不补 0；影响力边已按「来源 → 受影响者」定向，与原始引用方向相反；官方说明称 18 个连通分量，本地重算为 16。
    </footer>
  </div>
</template>
