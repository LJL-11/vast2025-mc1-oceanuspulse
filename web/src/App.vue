<script setup>
import {
  computed,
  markRaw,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowReactive,
} from "vue";
import { useAppStore } from "./stores/useAppStore";
import { dataService } from "./lib/dataService";
import AppIcon from "./components/AppIcon.vue";
import { bindModuleNavigation, prefersReducedMotion } from "./lib/navigation";
const viewLoaders = {
  overview: () => import("./views/NetworkOverview.vue"),
  influence: () => import("./views/InfluenceTrace.vue"),
  genre: () => import("./views/GenreSpread.vue"),
  rising: () => import("./views/RisingStar.vue"),
};

const store = useAppStore();
const views = shallowReactive({}),
  viewPromises = new Map();
const currentView = computed(() => views[store.activeModule] || null);
const modules = [
  { key: "overview", label: "全景图谱", icon: "graph", index: "00" },
  { key: "influence", label: "影响力溯源", icon: "graph", index: "01" },
  { key: "genre", label: "流派传播", icon: "flow", index: "02" },
  { key: "rising", label: "新星预测", icon: "star", index: "03" },
];
const status = ref("loading");
const contract = ref(null);
const menuOpen = ref(false);
const presentation = ref(false);
const exported = ref(false);
const pendingModule = ref(null),
  navigationError = ref("");
let exportTimer;
let navigationSequence = 0,
  currentTransition = null;
const moduleScrollPositions = new Map();
const previousScrollRestoration = window.history.scrollRestoration;

async function ensureView(key) {
  if (views[key]) return;
  if (!viewPromises.has(key))
    viewPromises.set(
      key,
      viewLoaders[key]()
        .then((module) => {
          views[key] = markRaw(module.default);
        })
        .catch((error) => {
          viewPromises.delete(key);
          throw error;
        }),
    );
  await viewPromises.get(key);
}
async function navigateModule(key, { history = true } = {}) {
  if (!viewLoaders[key]) return;
  const sequence = ++navigationSequence;
  currentTransition?.skipTransition();
  navigationError.value = "";
  if (key === store.activeModule && views[key]) {
    pendingModule.value = null;
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion() ? "instant" : "smooth",
    });
    return;
  }
  pendingModule.value = key;
  moduleScrollPositions.set(store.activeModule, window.scrollY);
  const targetScroll = history ? 0 : moduleScrollPositions.get(key) || 0;
  try {
    await ensureView(key);
    if (sequence !== navigationSequence) return;
    const update = async () => {
      if (sequence !== navigationSequence) return;
      store.activeModule = key;
      if (history) {
        const url = new URL(window.location.href);
        url.searchParams.set("module", key);
        url.hash = "";
        window.history.pushState({ module: key }, "", url);
      }
      await nextTick();
      if (sequence !== navigationSequence) return;
      window.scrollTo({ top: 0, behavior: "instant" });
      const start = performance.now();
      while (
        document.querySelector(".op-main > .op-state:not(.error)") &&
        performance.now() - start < 650
      ) {
        await new Promise((resolve) => setTimeout(resolve, 16));
      }
      if (sequence !== navigationSequence) return;
      window.scrollTo({ top: targetScroll, behavior: "instant" });
      window.dispatchEvent(new Event("resize"));
    };
    if (
      document.startViewTransition &&
      !prefersReducedMotion() &&
      !document.hidden
    ) {
      const transition = document.startViewTransition(update);
      currentTransition = transition;
      transition.ready.catch(() => {});
      await transition.finished.catch(() => {});
      if (currentTransition === transition) currentTransition = null;
    } else {
      await update();
      if (!prefersReducedMotion())
        document
          .querySelector(".op-main")
          ?.animate(
            [{ transform: "translateY(5px)" }, { transform: "translateY(0)" }],
            { duration: 220, easing: "cubic-bezier(.16,1,.3,1)" },
          );
    }
    if (sequence === navigationSequence)
      document.querySelector(".op-main")?.focus({ preventScroll: true });
  } catch {
    if (sequence === navigationSequence)
      navigationError.value = "工作台加载失败，请重新选择模块。";
  } finally {
    if (sequence === navigationSequence) pendingModule.value = null;
  }
}
function handleHistory() {
  const key =
    new URLSearchParams(window.location.search).get("module") || "overview";
  navigateModule(viewLoaders[key] ? key : "overview", { history: false });
}

function changeModule(key) {
  store.setModule(key);
  menuOpen.value = false;
}
function exportSnapshot() {
  const snapshot = {
    title: "OceanusPulse 分析视角",
    contract: contract.value,
    module: store.activeModule,
    yearRange: store.yearRange,
    focus: store.focusNode,
    entityTypes: store.visibleTypes,
    relations: store.visibleFlowTypes,
    genres: store.focusGenres,
    metric: store.trendMetric,
  };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `OceanusPulse-${store.activeModule}-${store.yearRange.join("-")}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  exported.value = true;
  clearTimeout(exportTimer);
  exportTimer = setTimeout(() => {
    exported.value = false;
  }, 2000);
}
async function togglePresentation() {
  if (!document.fullscreenElement) {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      presentation.value = !presentation.value;
    }
  } else await document.exitFullscreen();
}
function updateFullscreen() {
  presentation.value = Boolean(document.fullscreenElement);
}
function handleKeys(event) {
  if (event.key === "Escape") menuOpen.value = false;
  if (event.altKey && ["0", "1", "2", "3"].includes(event.key)) {
    event.preventDefault();
    changeModule(
      ["overview", "influence", "genre", "rising"][Number(event.key)],
    );
  }
}
onMounted(async () => {
  const requested = new URLSearchParams(window.location.search).get("module");
  if (requested && viewLoaders[requested]) store.activeModule = requested;
  bindModuleNavigation(navigateModule);
  window.history.scrollRestoration = "manual";
  window.addEventListener("popstate", handleHistory);
  document.addEventListener("keydown", handleKeys);
  document.addEventListener("fullscreenchange", updateFullscreen);
  ensureView(store.activeModule).catch(() => {
    navigationError.value = "工作台加载失败，请重新选择模块。";
  });
  try {
    contract.value = (await dataService.manifest()).meta;
    status.value = "ok";
  } catch {
    status.value = "missing";
  }
});
onBeforeUnmount(() => {
  bindModuleNavigation(null);
  currentTransition?.skipTransition();
  window.removeEventListener("popstate", handleHistory);
  window.history.scrollRestoration = previousScrollRestoration;
  document.removeEventListener("keydown", handleKeys);
  document.removeEventListener("fullscreenchange", updateFullscreen);
  clearTimeout(exportTimer);
});
</script>

<template>
  <div
    class="op-app"
    :class="{
      'presentation-mode': presentation,
      'motion-paused': !store.motionEnabled,
    }"
  >
    <header class="nav nav--split studio-nav">
      <div class="wrap nav__bar">
        <a class="skip-link" href="#analysis">跳至分析工作台</a>
        <a
          class="studio-brand"
          href="?module=overview"
          aria-label="OceanusPulse 潮音脉首页"
          @click.prevent="changeModule('overview')"
        >
          <span class="brand-mark" aria-hidden="true"
            ><i /><i /><i /><i
          /></span>
          <span
            >Oceanus<span class="brand-light">Pulse</span
            ><small>潮音脉 · 音乐知识图谱</small></span
          >
        </a>
        <nav class="module-nav" aria-label="分析模块">
          <button
            v-for="item in modules"
            :key="item.key"
            type="button"
            class="module-link"
            :class="{ 'is-pending': pendingModule === item.key }"
            :aria-busy="pendingModule === item.key"
            :aria-current="store.activeModule === item.key ? 'page' : undefined"
            :title="`Alt + ${item.index.at(-1)}`"
            @click="changeModule(item.key)"
          >
            <AppIcon :name="item.icon" :size="17" /><span>{{ item.label }}</span
            ><small>{{ item.index }}</small>
          </button>
        </nav>
        <div class="nav-actions">
          <button
            class="btn btn--secondary icon-button presentation-button"
            :aria-label="presentation ? '退出演示模式' : '进入全屏演示'"
            :title="presentation ? '退出演示模式' : '进入全屏演示'"
            @click="togglePresentation"
          >
            <AppIcon name="expand" />
          </button>
          <button
            class="btn btn--primary export-button"
            @click="exportSnapshot"
          >
            <AppIcon
              :name="exported ? 'check' : 'download'"
              :size="16"
            /><span>{{ exported ? "已导出视角" : "导出视角" }}</span>
          </button>
          <button
            class="btn btn--secondary icon-button menu-toggle"
            :aria-expanded="menuOpen"
            aria-controls="mobile-navigation"
            aria-label="打开模块菜单"
            @click="menuOpen = !menuOpen"
          >
            <AppIcon :name="menuOpen ? 'close' : 'menu'" />
          </button>
        </div>
      </div>
      <nav
        v-if="menuOpen"
        id="mobile-navigation"
        class="mobile-navigation"
        aria-label="手机分析模块"
      >
        <button
          v-for="item in modules"
          :key="item.key"
          :aria-current="store.activeModule === item.key ? 'page' : undefined"
          @click="changeModule(item.key)"
        >
          <span>{{ item.index }}</span
          >{{ item.label }}<AppIcon name="arrow" />
        </button>
        <p>VAST Challenge 2025 · Mini-Challenge 1</p>
      </nav>
    </header>
    <main id="analysis" class="op-main" tabindex="-1">
      <p v-if="navigationError" class="route-error" role="alert">
        {{ navigationError }}
      </p>
      <KeepAlive
        ><component
          v-if="currentView"
          :is="currentView"
          :key="store.activeModule"
      /></KeepAlive>
      <div v-if="!currentView" class="op-state" role="status">
        正在准备音乐可视分析工作台…
      </div>
    </main>
    <footer class="studio-footer">
      <div class="wrap footer-line">
        <span
          >OceanusPulse
          <span class="muted">/ VAST Challenge 2025 · MC1</span></span
        >
        <span class="data-health" :class="{ warning: status === 'missing' }"
          ><i />{{
            status === "ok"
              ? `数据契约 ${contract.schema_version} · 观测截点 ${contract.cutoff_year}`
              : status === "loading"
                ? "正在校验数据"
                : "数据未就绪，请生成分析数据"
          }}</span
        >
        <span class="footer-source">数据：IEEE VAST · 图标：Lucide（ISC）</span>
      </div>
    </footer>
    <span class="sr-only" role="status" aria-live="polite">{{
      exported ? "分析视角已导出为 JSON 文件" : ""
    }}</span>
  </div>
</template>
