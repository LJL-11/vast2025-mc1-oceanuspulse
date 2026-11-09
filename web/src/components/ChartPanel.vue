<script setup>
import { nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import { BarChart, HeatmapChart, LineChart, RadarChart } from 'echarts/charts'
import { AriaComponent, GridComponent, LegendComponent, RadarComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { observeChartSize } from '../lib/atlas'

use([
  BarChart, HeatmapChart, LineChart, RadarChart,
  AriaComponent, GridComponent, LegendComponent, RadarComponent, TooltipComponent, VisualMapComponent,
  CanvasRenderer,
])

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
})
const emit = defineEmits(['chart-click'])

const el = ref(null)
let chart = null
let stopMeasuring
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

function render() {
  if (!el.value?.clientWidth || !props.option) return
  if (!chart) {
    chart = init(el.value)
    chart.on('click', params => emit('chart-click', params))
  }
  chart.setOption({
    aria: { enabled: true },
    ...props.option,
    animation: !reducedMotion.matches && (props.option.animation ?? true),
  }, true)
}

onMounted(() => {
  render()
  reducedMotion.addEventListener('change', render)
  if (typeof ResizeObserver !== 'undefined') {
    stopMeasuring = observeChartSize(el.value, () => {
      if (!el.value?.clientWidth) return
      if (chart) chart.resize()
      else render()
    })
  }
})

watch(() => props.option, render, { deep: true })
onActivated(() => nextTick(() => {
  if (chart && el.value?.clientWidth) {
    chart.resize()
    render()
  }
}))

onBeforeUnmount(() => {
  stopMeasuring?.()
  reducedMotion.removeEventListener('change', render)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="op-chart" :style="{ height }" data-visual />
</template>
