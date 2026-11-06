<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

// 表头流光：把指针位置写成 CSS 变量，交给 .op-header-fx 的径向光斑渲染。
// 只作用于表头本身，不触碰任何视图逻辑。
const headerEl = ref(null)
let glowFrame = 0
function onHeaderMove(event) {
  if (glowFrame) return
  const { clientX, clientY } = event
  glowFrame = requestAnimationFrame(() => {
    glowFrame = 0
    const el = headerEl.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    el.style.setProperty('--mx', `${clientX - rect.left}px`)
    el.style.setProperty('--my', `${clientY - rect.top}px`)
  })
}
function onHeaderLeave() {
  const el = headerEl.value
  if (!el) return
  el.style.setProperty('--mx', '24%')
  el.style.setProperty('--my', '30%')
}
onBeforeUnmount(() => { if (glowFrame) cancelAnimationFrame(glowFrame) })
</script>

<template>
  <div class="op-app">
    <header
      ref="headerEl"
      class="op-header"
      @pointermove="onHeaderMove"
      @pointerleave="onHeaderLeave"
    >
      <div class="op-header-fx" aria-hidden="true"></div>
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

<style scoped>
/* 表头专属视觉：深蓝渐变 + 三层缓慢流动的极光 + 指针跟随的流光。
   使用 scoped，只覆盖 .op-header 及其内部元素，页面其余部分完全不受影响。 */
.op-header {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: 18px 32px 0; /* 与原布局保持一致 */
  color: #fff;
  --mx: 24%;
  --my: 30%;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, .10), transparent 46%),
    linear-gradient(112deg, #102f4f 0%, #174674 28%, #2569a8 64%, #1a4d82 100%);
  box-shadow: 0 10px 28px rgba(13, 40, 70, .16), inset 0 -1px 0 rgba(255, 255, 255, .18);
}
.op-header > *:not(.op-header-fx) { position: relative; z-index: 1; }

/* 第一层：缓慢漂移的三色极光 */
.op-header::before {
  content: '';
  position: absolute;
  inset: -12%;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(46% 82% at 12% 8%, rgba(105, 190, 255, .62), transparent 72%),
    radial-gradient(38% 88% at 72% 0%, rgba(72, 224, 218, .34), transparent 72%),
    radial-gradient(52% 86% at 94% 100%, rgba(142, 130, 255, .36), transparent 72%);
  filter: blur(10px);
  /* 负 delay：页面一打开光晕就处在流动中途，而不是从静止起点开始 */
  animation: op-aurora 16s ease-in-out -6s infinite alternate;
}

/* 第二层：斜向扫过的流光带 */
.op-header::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: .72;
  background: linear-gradient(108deg,
      transparent 34%,
      rgba(255, 255, 255, .08) 45%,
      rgba(255, 255, 255, .28) 50%,
      rgba(255, 255, 255, .08) 55%,
      transparent 66%);
  background-size: 240% 100%;
  animation: op-sweep 7s linear -3.2s infinite;
}

/* 第三层：跟随鼠标的柔光 + 极淡斜纹 */
.op-header-fx {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: .6;
  transition: opacity .45s ease;
  background:
    radial-gradient(440px circle at var(--mx) var(--my),
        rgba(255, 255, 255, .34), rgba(126, 198, 255, .16) 42%, transparent 70%),
    repeating-linear-gradient(112deg, rgba(255, 255, 255, .045) 0 1px, transparent 1px 26px);
}
.op-header:hover .op-header-fx { opacity: 1; }
.op-header:hover::after { opacity: .95; animation-duration: 3.6s; }
.op-header:hover::before { animation-duration: 8s; }

@keyframes op-aurora {
  0%   { transform: translate3d(-3%, -2%, 0) scale(1); }
  50%  { transform: translate3d(3%, 2%, 0) scale(1.08); }
  100% { transform: translate3d(-1%, 3%, 0) scale(1.02); }
}
@keyframes op-sweep {
  from { background-position: 160% 0; }
  to   { background-position: -60% 0; }
}

/* 文字与控件：提亮对比度，加一点玻璃质感；原有的橙色选中态保持不变 */
.op-brand h1 { text-shadow: 0 2px 18px rgba(6, 26, 46, .38); }
.op-brand p, .op-header-meta, .op-focus-bar { color: rgba(255, 255, 255, .86); }
.op-meta-pill {
  background: rgba(255, 255, 255, .09);
  border-color: rgba(255, 255, 255, .30);
  color: #eaf4ff;
  backdrop-filter: blur(8px);
}
.op-meta-pill.warn { border-color: #ffb98c; color: #ffdcc0; }
.op-focus-chip {
  background: rgba(255, 255, 255, .16);
  border-color: rgba(255, 255, 255, .28);
  backdrop-filter: blur(8px);
}
.op-header .op-btn {
  background: rgba(255, 255, 255, .12);
  border-color: rgba(255, 255, 255, .30);
  color: #fff;
  backdrop-filter: blur(8px);
}
.op-header .op-btn:hover { background: rgba(255, 255, 255, .22); border-color: rgba(255, 255, 255, .5); }
.op-tab {
  border-radius: 9px 9px 0 0;
  transition: color .2s ease, background .25s ease, transform .25s ease, border-color .2s ease;
}
.op-tab:hover {
  color: #fff;
  background: rgba(255, 255, 255, .12);
  transform: translateY(-2px);
}
.op-tab.active { background: rgba(255, 255, 255, .07); }
.op-tab.active:hover { transform: none; }

@media (max-width: 1100px) {
  .op-header { padding: 16px 18px 0; }
}
@media (prefers-reduced-motion: reduce) {
  .op-header::before, .op-header::after { animation: none; }
  .op-header-fx { transition: none; }
  .op-tab:hover { transform: none; }
}
</style>
