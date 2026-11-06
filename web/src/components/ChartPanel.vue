<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
})
const emit = defineEmits(['chart-click'])

const el = ref(null)
let chart = null
let observer = null

function render() {
  if (!el.value || !props.option) return
  if (!chart) {
    chart = echarts.init(el.value)
    chart.on('click', params => emit('chart-click', params))
  }
  chart.setOption(props.option, true)
}

onMounted(() => {
  render()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart && chart.resize())
    observer.observe(el.value)
  }
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="op-chart" :style="{ height }" />
</template>
