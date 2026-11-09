<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/useAppStore'
import AppIcon from './AppIcon.vue'

const props = defineProps({ module: { type: String, required: true } })
const store = useAppStore()
const chapters = [
  { key: 'overview', number: '00', title: '全景图谱' },
  { key: 'influence', number: '01', title: '影响力溯源' },
  { key: 'genre', number: '02', title: '流派传播' },
  { key: 'rising', number: '03', title: '新星预测' },
]
const index = computed(() => chapters.findIndex(chapter => chapter.key === props.module))
const previous = computed(() => chapters[index.value - 1])
const next = computed(() => chapters[index.value + 1])
function href(key) {
  const url = new URL(window.location.href)
  url.searchParams.set('module', key)
  url.hash = ''
  return url.pathname + url.search
}
function turn(event, key) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  store.setModule(key)
}
</script>

<template>
  <nav class="journal-pager" aria-label="图志翻页">
    <a v-if="previous" class="journal-previous" :href="href(previous.key)" @click="turn($event, previous.key)">
      <AppIcon name="arrow" :size="18" />
      <span><small>上一章 · {{ previous.number }}</small><strong>{{ previous.title }}</strong></span>
    </a>
    <a v-if="next" class="journal-next" :href="href(next.key)" @click="turn($event, next.key)">
      <span><small>下一章 · {{ next.number }}</small><strong>{{ next.title }}</strong></span>
      <AppIcon name="arrow" :size="18" />
    </a>
    <a v-else class="journal-next" :href="href('overview')" @click="turn($event, 'overview')">
      <span><small>Oceanus 音乐图志</small><strong>回到封面</strong></span>
      <AppIcon name="arrow" :size="18" />
    </a>
  </nav>
</template>
