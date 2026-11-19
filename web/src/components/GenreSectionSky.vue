<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({ variation: { type: Number, required: true } })
const sky = ref(null)
let visibility
// These small lights belong to the chapter margin, outside the plotted data.
const lights = Array.from({ length: 31 }, (_, index) => {
  const i = index + 1
  return { x: 18 + ((i * 127 + props.variation * 47) % 706), y: 7 + ((i * i * 23 + props.variation * 19) % 136),
    radius: i % 8 === 0 ? 1.8 : .65 + (i % 3) * .23, bright: i % 8 === 0 }
})
onMounted(() => {
  visibility = new IntersectionObserver(([entry]) => sky.value?.toggleAttribute('data-visible', entry.isIntersecting))
  visibility.observe(sky.value)
})
onBeforeUnmount(() => visibility?.disconnect())
</script>

<template>
  <svg ref="sky" class="score-margin-sky" :class="{ 'is-warm': variation % 2 }" viewBox="0 0 740 152"
    preserveAspectRatio="xMaxYMid slice" aria-hidden="true" focusable="false">
    <g class="margin-lights">
      <g v-for="(star, i) in lights" :key="i" :transform="'translate(' + star.x + ',' + star.y + ')'">
        <circle :r="star.radius" />
        <path v-if="star.bright" class="margin-glint" :style="{ animationDelay: '-' + i * .61 + 's' }" d="M-4.2 0H4.2M0 -4.2V4.2" />
      </g>
    </g>
    <g class="margin-staff" :transform="'translate(0 ' + (variation % 3) * 5 + ')'">
      <path v-for="lane in [0,1,2,3,4]" :key="lane" :transform="'translate(0 ' + lane * 4 + ')'"
        d="M-10 101C113 102 157 48 271 52S462 128 568 86S708 23 760 38" />
      <path class="margin-travel" pathLength="100" :style="{ animationDelay: '-' + variation * 2.7 + 's' }"
        d="M-10 109C113 110 157 56 271 60S462 136 568 94S708 31 760 46" />
    </g>
  </svg>
</template>

<style scoped>
.score-margin-sky {
  position: absolute;
  z-index: -1;
  top: 0;
  right: 0;
  width: min(64%, 840px);
  height: clamp(112px, 14vw, 184px);
  pointer-events: none;
  color: #9fcbf1;
  mask-image: linear-gradient(90deg, transparent, #000 29%, #000 94%, #000c);
}
.score-margin-sky.is-warm { color: #dfbd91; }
.margin-lights { fill: currentColor; opacity: .66; }
.margin-glint { fill: none; stroke: currentColor; stroke-width: .65; }
.margin-staff { fill: none; stroke: currentColor; stroke-width: .8; stroke-opacity: .23; }
.margin-travel { stroke-width: 1.45; stroke-opacity: .75; stroke-linecap: round; stroke-dasharray: 5 95; }
@media (prefers-reduced-motion: no-preference) {
  .margin-travel { animation: score-margin-travel 13s linear infinite paused; }
  .margin-glint { animation: score-margin-light 5.6s ease-in-out infinite alternate paused; }
  [data-visible] :is(.margin-travel,.margin-glint) { animation-play-state: running; }
}
@keyframes score-margin-travel { from { stroke-dashoffset: 8; } to { stroke-dashoffset: -92; } }
@keyframes score-margin-light { from { opacity: .24; } to { opacity: 1; } }
@media (max-width: 600px) {
  .score-margin-sky { width: 56%; height: 95px; opacity: .74; }
}
</style>
