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
    <div class="op-scrubber-bounds">
      <input
        type="range" :min="min" :max="max" :value="modelValue[0]"
        aria-label="起始年份" @input="setStart"
      >
      <input
        type="range" :min="min" :max="max" :value="modelValue[1]"
        aria-label="结束年份" @input="setEnd"
      >
    </div>
    <strong>{{ modelValue[0] === modelValue[1] ? modelValue[0] + ' 年' : modelValue.join(' – ') }}</strong>
    <button type="button" class="op-btn" :aria-pressed="modelValue[0] === min && modelValue[1] === max" @click="preset(min, max)">全部</button>
    <button v-for="year in [2020, 2030].filter(year => year > min && year <= max)" :key="year" type="button" class="op-btn"
      :aria-pressed="modelValue[0] === year && modelValue[1] === max" @click="preset(year, max)">{{ year }}+</button>
  </div>
</template>

<style scoped>
.op-scrubber { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; }
.op-scrubber-bounds { display: inline-flex; align-items: center; gap: 8px; }
.op-scrubber input[type="range"] { appearance: none; width: clamp(65px, 8vw, 112px); height: 22px; margin: 0; background: transparent; cursor: pointer; }
.op-scrubber input::-webkit-slider-runnable-track { height: 4px; background: #d3e3ee; border-radius: 4px; }
.op-scrubber input::-webkit-slider-thumb { appearance: none; width: 13px; height: 13px; margin-top: -4.5px; border: 2px solid #fff; border-radius: 50%; background: #28729c; box-shadow: 0 0 0 1px #4384a9; }
.op-scrubber input::-moz-range-track { height: 4px; background: #d3e3ee; border-radius: 4px; }
.op-scrubber input::-moz-range-thumb { width: 10px; height: 10px; border: 2px solid #fff; border-radius: 50%; background: #28729c; box-shadow: 0 0 0 1px #4384a9; }
.op-scrubber button[aria-pressed="true"] { background: #e9f2f9; border-color: #bbd4e7; color: #194f72; }
.op-scrubber strong { font-size: 12px; color: #17324d; font-weight: 500; font-variant-numeric: tabular-nums; min-width: 78px; }
</style>
