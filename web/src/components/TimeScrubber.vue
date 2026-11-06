<script setup>
const props = defineProps({
  modelValue: { type: Array, required: true },
  min: { type: Number, default: 1975 },
  max: { type: Number, default: 2040 },
})
const emit = defineEmits(['update:modelValue'])

function update(next) {
  emit('update:modelValue', next)
}
function setStart(event) {
  const value = Math.min(Number(event.target.value), props.modelValue[1])
  update([value, props.modelValue[1]])
}
function setEnd(event) {
  const value = Math.max(Number(event.target.value), props.modelValue[0])
  update([props.modelValue[0], value])
}
function preset(start, end) {
  update([start, end])
}
</script>

<template>
  <div class="op-scrubber">
    <span class="op-tool-label">时间窗</span>
    <input
      type="range" :min="min" :max="max" :value="modelValue[0]"
      aria-label="起始年份" @input="setStart"
    >
    <input
      type="range" :min="min" :max="max" :value="modelValue[1]"
      aria-label="结束年份" @input="setEnd"
    >
    <strong>{{ modelValue[0] }} – {{ modelValue[1] }}</strong>
    <button type="button" class="op-btn" @click="preset(min, max)">全部</button>
    <button type="button" class="op-btn" @click="preset(2020, max)">2020+</button>
    <button type="button" class="op-btn" @click="preset(2030, max)">2030+</button>
  </div>
</template>

<style scoped>
.op-scrubber { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; }
.op-scrubber input[type="range"] { width: 120px; accent-color: #2a9d8f; }
.op-scrubber strong { font-size: 12px; color: #17324d; font-weight: 500; font-variant-numeric: tabular-nums; min-width: 78px; }
</style>
