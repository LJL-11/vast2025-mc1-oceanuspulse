<script setup>
import { onActivated, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { createChart, motionOption } from "../lib/charts";

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "320px" },
  label: { type: String, default: "交互分析图表" },
});
const emit = defineEmits(["chart-click"]);

const el = ref(null);
let chart = null;
let observer = null;

function render() {
  if (!el.value || !props.option) return;
  if (!chart) {
    chart = createChart(el.value);
    chart.on("click", (params) => emit("chart-click", params));
  }
  chart.setOption({ ...props.option, ...motionOption() }, true);
}

onMounted(() => {
  render();
  if (typeof ResizeObserver !== "undefined") {
    observer = new ResizeObserver(() => chart && chart.resize());
    observer.observe(el.value);
  }
});

watch(() => props.option, render, { deep: true });
onActivated(() => chart?.resize());

onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div
    ref="el"
    class="op-chart"
    :style="{ height }"
    role="img"
    :aria-label="label"
  />
</template>
