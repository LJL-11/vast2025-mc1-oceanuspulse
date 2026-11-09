<script setup>
const props = defineProps({
  label: { type: String, default: '筛选' },
  options: { type: Array, required: true },
  modelValue: { type: Array, required: true },
  allowEmpty: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

function toggle(value) {
  const has = props.modelValue.includes(value)
  if (!has) return emit('update:modelValue', [...props.modelValue, value])
  if (!props.allowEmpty && props.modelValue.length === 1) return
  emit('update:modelValue', props.modelValue.filter(item => item !== value))
}
function selectAll() {
  emit('update:modelValue', props.options.map(item => item.value))
}
</script>

<template>
  <div class="op-filter">
    <span v-if="label" class="op-tool-label">{{ label }}</span>
    <div class="op-chips" role="group" :aria-label="label || undefined">
      <button
        v-for="item in options"
        :key="item.value"
        type="button"
        class="op-chip"
        :class="{ on: modelValue.includes(item.value) }"
        :aria-pressed="modelValue.includes(item.value)"
        :title="item.hint || item.label"
        @click="toggle(item.value)"
      >
        <span v-if="item.color" class="dot" :style="{ background: item.color }" />
        {{ item.label }}
      </button>
    </div>
    <button type="button" class="op-btn" @click="selectAll">全选</button>
  </div>
</template>

<style scoped>
.op-filter { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; }
</style>
