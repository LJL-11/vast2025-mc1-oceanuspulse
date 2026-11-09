import { computed, onBeforeUnmount, onMounted, shallowRef } from 'vue'

const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
const pageVisible = shallowRef(!document.hidden)
const motionReduced = shallowRef(preference.matches)
const updatePreference = event => { motionReduced.value = event.matches }
const updateVisibility = () => { pageVisible.value = !document.hidden }
preference.addEventListener('change', updatePreference)
document.addEventListener('visibilitychange', updateVisibility)

const listeners = new WeakMap()
const observer = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => {
  for (const entry of entries) listeners.get(entry.target)?.(entry.isIntersecting)
}) : null

export function useVisibleMotion(getElement) {
  const visible = shallowRef(false)
  let element
  onMounted(() => {
    element = getElement()
    if (element && observer) {
      listeners.set(element, state => { visible.value = state })
      observer.observe(element)
    } else visible.value = true
  })
  onBeforeUnmount(() => {
    if (!element) return
    observer?.unobserve(element)
    listeners.delete(element)
  })
  return computed(() => visible.value && pageVisible.value && !motionReduced.value)
}

export function useReadingPause() {
  const pointer = shallowRef(false)
  const focused = shallowRef(false)
  return {
    paused: computed(() => pointer.value || focused.value || motionReduced.value),
    events: {
      pointerenter(event) { pointer.value = event.pointerType !== 'touch' },
      pointerleave() { pointer.value = false },
      focusin(event) { focused.value = event.target.matches(':focus-visible') },
      focusout() { focused.value = false },
    },
  }
}

const fullTurn = Math.PI * 2

export function wavePhase(angle) {
  const phase = ((angle / fullTurn) % 1 + 1) % 1
  return phase ? (phase - 1).toFixed(4) : 0
}

export function revolvingWave(cx, cy, radius, { amplitude = 11, seconds = 5.6, delay = 0 } = {}) {
  const steps = 220
  const point = (angle, distance) => (cx + Math.cos(angle) * distance).toFixed(1)
    + ' ' + (cy + Math.sin(angle) * distance).toFixed(1)
  let wave = ''
  let echo = ''
  let ribs = ''
  for (let index = 0; index < steps; index += 1) {
    const angle = fullTurn * index / steps
    // The two unequal crests make the direction of a full revolution easy to see.
    const crest = ((1 + Math.cos(angle)) / 2) ** 5
    const response = ((1 + Math.cos(angle - 2.08)) / 2) ** 7
    const energy = .18 + .82 * crest + .48 * response
    const vibration = .55 * Math.sin(angle * 17) + .30 * Math.sin(angle * 29) + .15 * Math.sin(angle * 43)
    const command = index ? 'L' : 'M'
    wave += command + point(angle, radius + amplitude * energy * vibration)
    echo += command + point(angle, radius - amplitude * .91
      + amplitude * energy * .58 * Math.sin(angle * 17 - .82))
    if (index % 5 === 0) {
      const base = radius + amplitude * .22
      ribs += 'M' + point(angle, base) + 'L' + point(angle, base + amplitude * (.12 + .59 * energy))
    }
  }
  return {
    wave: wave + 'Z', echo: echo + 'Z', ribs,
    style: {
      '--atlas-wave-x': cx + 'px',
      '--atlas-wave-y': cy + 'px',
      '--atlas-orbit-period': seconds + 's',
      '--atlas-orbit-delay': delay + 's',
    },
  }
}

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    preference.removeEventListener('change', updatePreference)
    document.removeEventListener('visibilitychange', updateVisibility)
    observer?.disconnect()
  })
}
