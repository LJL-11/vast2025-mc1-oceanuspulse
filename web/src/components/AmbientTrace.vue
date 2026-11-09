<script setup>
import { ref } from 'vue'
import { useVisibleMotion } from '../lib/ambientMotion'

defineProps({ orbit: { type: Object, required: true } })
const layer = ref(null)
const running = useVisibleMotion(() => layer.value?.ownerSVGElement)
</script>

<template>
  <g ref="layer" class="atlas-idle-wave" :data-running="running" aria-hidden="true">
    <g class="atlas-wave-rotor" :style="orbit.style">
      <g class="atlas-wave-kick">
        <path class="atlas-rotor-wash" :d="orbit.wave" pathLength="100" />
        <path class="atlas-rotor-ribs" :d="orbit.ribs" />
        <path class="atlas-rotor-echo" :d="orbit.echo" />
        <path class="atlas-rotor-wave" :d="orbit.wave" />
        <path class="atlas-rotor-crest" :d="orbit.wave" pathLength="100" />
      </g>
    </g>
  </g>
</template>

<style>
.atlas-idle-wave {
  fill: none;
  pointer-events: none;
  opacity: 0;
  transition: opacity 140ms ease;
}
.atlas-idle-wave[data-running="true"] { opacity: 1; }
.atlas-wave-rotor, .atlas-wave-kick, .atlas-wave-body, .atlas-orbit-swell {
  transform-box: view-box;
  transform-origin: var(--atlas-wave-x, 50%) var(--atlas-wave-y, 50%);
}
.atlas-wave-rotor path {
  vector-effect: non-scaling-stroke;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.atlas-rotor-wave { stroke: var(--atlas-rotor-ink, #28759c); stroke-width: 1.85; opacity: .92; }
.atlas-rotor-echo { stroke: #75a9bc; stroke-width: 1.25; opacity: .83; }
.atlas-rotor-ribs { stroke: var(--atlas-rotor-ink, #3c819f); stroke-width: 1.12; opacity: .62; }
.atlas-rotor-wash { stroke: #5ea0ba; stroke-width: 7.2; stroke-dasharray: 27 73; stroke-dashoffset: 13; opacity: .23; }
.atlas-rotor-crest { stroke: var(--atlas-rotor-ink, #205e83); stroke-width: 2.9; stroke-dasharray: 19 81; stroke-dashoffset: 10; }
:where(.atlas-idle-wave[data-running="true"]) .atlas-wave-rotor {
  animation: atlas-wave-spin var(--atlas-orbit-period, 5.6s) linear var(--atlas-orbit-delay, 0s) infinite;
}
:where(.atlas-idle-wave[data-running="true"]) .atlas-wave-kick {
  animation: atlas-wave-kick 2.42s cubic-bezier(.18,.74,.24,1) var(--atlas-orbit-delay, 0s) infinite;
}
:where(svg:has(.atlas-idle-wave[data-running="true"])) .atlas-wave-body {
  animation: atlas-wave-body 2.42s cubic-bezier(.18,.74,.24,1)
    calc(var(--atlas-body-delay, 0s) + var(--atlas-orbit-delay, 0s)) infinite;
}
:where(svg:has(.atlas-idle-wave[data-running="true"])) .atlas-orbit-swell {
  animation: atlas-orbit-swell var(--atlas-orbit-period, 5.6s) ease-in-out
    calc(var(--atlas-orbit-period, 5.6s) * var(--atlas-wave-phase, 0) + var(--atlas-orbit-delay, 0s)) infinite;
}
[data-wave-surface]:is(:focus-visible, :has(:focus-visible), :active) .atlas-idle-wave { opacity: 0; }
[data-wave-surface]:is(:focus-visible, :has(:focus-visible), :active)
  :is(.atlas-wave-rotor, .atlas-wave-kick, .atlas-wave-body, .atlas-orbit-swell) { animation: none; }
@media (hover: hover) {
  [data-wave-surface]:hover .atlas-idle-wave { opacity: 0; }
  [data-wave-surface]:hover :is(.atlas-wave-rotor, .atlas-wave-kick, .atlas-wave-body, .atlas-orbit-swell) {
    animation: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .atlas-idle-wave { display: none; }
  :is(.atlas-wave-rotor, .atlas-wave-kick, .atlas-wave-body, .atlas-orbit-swell) { animation: none; }
}
@keyframes atlas-wave-spin { to { transform: rotate(1turn); } }
@keyframes atlas-wave-kick {
  0%, 100% { transform: scale(.992); opacity: .77; }
  11% { transform: scale(1.029); opacity: 1; }
  22% { transform: scale(1.002); opacity: .83; }
  36% { transform: scale(1.021); opacity: .98; }
  63% { transform: scale(.997); opacity: .84; }
}
@keyframes atlas-wave-body {
  0%, 100% { transform: scale(1); }
  12% { transform: scale(var(--atlas-wave-stretch-x, 1.021), var(--atlas-wave-stretch-y, 1.035)); }
  23% { transform: scale(1.004); }
  36% { transform: scale(var(--atlas-wave-echo-x, 1.012), var(--atlas-wave-echo-y, 1.022)); }
  66% { transform: scale(1); }
}
@keyframes atlas-orbit-swell {
  0%, 100% { transform: scale(var(--atlas-wave-reach, 1.047)); }
  8% { transform: scale(1.012); }
  15% { transform: scale(1.026); }
  28%, 78% { transform: scale(1); }
  92% { transform: scale(1.016); }
}
</style>
