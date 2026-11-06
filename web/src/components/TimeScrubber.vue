<script setup>
import { computed, onBeforeUnmount, onDeactivated, ref } from "vue";
import AppIcon from "./AppIcon.vue";
const props = defineProps({
  modelValue: { type: Array, required: true },
  min: { type: Number, default: 1975 },
  max: { type: Number, default: 2040 },
});
const emit = defineEmits(["update:modelValue"]);
const playing = ref(false);
let timer;
const progress = computed(() => ({
  "--range-start": `${((props.modelValue[0] - props.min) / (props.max - props.min)) * 100}%`,
  "--range-end": `${((props.modelValue[1] - props.min) / (props.max - props.min)) * 100}%`,
}));
function stop() {
  clearInterval(timer);
  playing.value = false;
}
function update(start, end) {
  stop();
  emit("update:modelValue", [start, end]);
}
function play() {
  if (playing.value) return stop();
  playing.value = true;
  let year = props.modelValue[1] >= props.max ? props.min : props.modelValue[1];
  const start =
    props.modelValue[1] >= props.max ? props.min : props.modelValue[0];
  emit("update:modelValue", [start, year]);
  timer = setInterval(() => {
    year += 1;
    emit("update:modelValue", [start, Math.min(year, props.max)]);
    if (year >= props.max) stop();
  }, 500);
}
onDeactivated(stop);
onBeforeUnmount(stop);
</script>
<template>
  <div class="time-control">
    <div class="time-label">
      <span class="field-label">观测时间窗</span
      ><strong>{{ modelValue[0] }} <span>—</span> {{ modelValue[1] }}</strong>
    </div>
    <div class="dual-range" :style="progress">
      <div class="range-track"><i /></div>
      <input
        type="range"
        :min="min"
        :max="max"
        :value="modelValue[0]"
        aria-label="起始年份"
        @input="
          update(
            Math.min(Number($event.target.value), modelValue[1]),
            modelValue[1],
          )
        "
      />
      <input
        type="range"
        :min="min"
        :max="max"
        :value="modelValue[1]"
        aria-label="结束年份"
        @input="
          update(
            modelValue[0],
            Math.max(Number($event.target.value), modelValue[0]),
          )
        "
      />
    </div>
    <div class="time-presets">
      <button
        v-for="start in [min, 2020, 2030]"
        :key="start"
        class="time-preset"
        :class="{ active: modelValue[0] === start && modelValue[1] === max }"
        @click="update(start, max)"
      >
        {{ start === min ? "全时段" : `${start}+` }}
      </button>
    </div>
    <button
      class="btn btn--secondary icon-button time-play"
      :aria-label="playing ? '暂停年代播放' : '播放年代变化'"
      :title="playing ? '暂停年代播放' : '播放年代变化'"
      :aria-pressed="playing"
      @click="play"
    >
      <AppIcon :name="playing ? 'pause' : 'play'" :size="14" />
    </button>
  </div>
</template>
