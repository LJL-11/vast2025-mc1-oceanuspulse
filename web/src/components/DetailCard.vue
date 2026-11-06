<script setup>
import { computed } from "vue";
import {
  NODE_COLORS,
  NODE_LABELS,
  EDGE_LABELS,
  formatCount,
} from "../lib/palette";
import AppIcon from "./AppIcon.vue";
const props = defineProps({
  node: { type: Object, default: null },
  degree: { type: Number, default: 0 },
  linkTypes: { type: Array, default: () => [] },
});
const emit = defineEmits(["close", "jump"]);
const color = computed(() => NODE_COLORS[props.node?.type] || "#95a4b9");
const initials = computed(() =>
  (props.node?.name || "")
    .split(" ")
    .slice(0, 2)
    .map((x) => x[0])
    .join(""),
);
</script>
<template>
  <aside class="entity-dossier" aria-label="当前实体档案" aria-live="polite">
    <div class="dossier-heading">
      <span class="field-label">实体档案</span
      ><button
        v-if="node"
        class="btn btn--secondary icon-button"
        aria-label="清除当前焦点"
        @click="emit('close')"
      >
        <AppIcon name="close" :size="15" />
      </button>
    </div>
    <template v-if="node">
      <div class="entity-avatar" :style="{ '--entity-color': color }">
        {{ initials }}
      </div>
      <span class="entity-kind"
        ><i :style="{ background: color }" />{{
          NODE_LABELS[node.type] || node.type
        }}</span
      >
      <h2 class="entity-name">{{ node.name }}</h2>
      <div class="dossier-stats">
        <div>
          <strong>{{ formatCount(degree) }}</strong
          ><span>图中连接</span>
        </div>
        <div>
          <strong>{{ node.release_year ?? "—" }}</strong
          ><span>发行年份</span>
        </div>
      </div>
      <dl class="entity-facts">
        <div>
          <dt>实体编号</dt>
          <dd>#{{ node.id }}</dd>
        </div>
        <div>
          <dt>所属流派</dt>
          <dd>{{ node.genre || "未标注" }}</dd>
        </div>
        <div>
          <dt>登榜年份</dt>
          <dd>{{ node.chart_year ?? "未知" }}</dd>
        </div>
      </dl>
      <div class="relation-breakdown">
        <span class="field-label">关系构成</span>
        <div v-for="item in linkTypes.slice(0, 4)" :key="item.type">
          <span>{{ EDGE_LABELS[item.type] || item.type }}</span
          ><i
            ><b
              :style="{
                width: `${Math.max(5, (item.count / Math.max(1, degree)) * 100)}%`,
              }" /></i
          ><strong>{{ item.count }}</strong>
        </div>
      </div>
      <button
        v-if="node.genre"
        class="btn btn--secondary dossier-action"
        @click="emit('jump', node.genre)"
      >
        查看流派传播<AppIcon name="arrow" :size="16" />
      </button>
      <span class="dossier-boundary"
        >连接表示图谱关系，不代表私人关系或因果影响。</span
      >
    </template>
    <template v-else
      ><div class="entity-avatar"><AppIcon name="graph" :size="32" /></div>
      <h2 class="entity-name">选择一个实体</h2>
      <p>点击图谱节点或搜索名称，查看关系与证据。</p></template
    >
  </aside>
</template>
