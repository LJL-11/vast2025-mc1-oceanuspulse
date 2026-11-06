<script setup>
import { computed } from 'vue'
import { NODE_COLORS, NODE_LABELS, EDGE_LABELS, formatCount } from '../lib/palette'

const props = defineProps({
  node: { type: Object, default: null },
  degree: { type: Number, default: 0 },
  linkTypes: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'jump'])

const color = computed(() => NODE_COLORS[props.node?.type] || '#718396')
const rows = computed(() => {
  if (!props.node) return []
  return [
    ['实体 ID', props.node.id],
    ['类型', NODE_LABELS[props.node.type] || props.node.type],
    ['流派', props.node.genre || '—'],
    ['发行 / 写作年份', props.node.release_year ?? '—'],
    ['已知登榜年份', props.node.chart_year ?? '未知（不补 0）'],
    ['登过热榜', props.node.notable == null ? '—' : (props.node.notable ? '是' : '否')],
    ['图中连接数', formatCount(props.degree)],
  ]
})
</script>

<template>
  <article class="op-card op-detail">
    <template v-if="node">
      <div class="op-detail-head">
        <h3 :style="{ color }">{{ node.name }}</h3>
        <button type="button" class="op-btn" @click="emit('close')">清除</button>
      </div>
      <p class="op-note">点击其他节点可切换焦点；焦点会同步到顶部跨模块状态条。</p>
      <dl class="op-detail-grid">
        <template v-for="[key, value] in rows" :key="key">
          <dt>{{ key }}</dt><dd>{{ value }}</dd>
        </template>
      </dl>
      <div v-if="linkTypes.length" class="op-pill-list">
        <span v-for="item in linkTypes" :key="item.type" class="op-pill">
          {{ EDGE_LABELS[item.type] || item.type }} × {{ item.count }}
        </span>
      </div>
      <button
        v-if="node.genre"
        type="button"
        class="op-btn primary"
        style="margin-top: 12px"
        @click="emit('jump', node.genre)"
      >在流派传播中查看「{{ node.genre }}」→</button>
    </template>
    <template v-else>
      <h3>实体详情</h3>
      <p class="op-note">在左侧关系图中点击任意节点，这里会显示它的类型、流派、年份、关系构成和可回溯的边 ID。再次点击空白处或按「清除」取消选择。</p>
    </template>
  </article>
</template>
