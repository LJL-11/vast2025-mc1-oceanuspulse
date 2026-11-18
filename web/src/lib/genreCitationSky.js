import { citationOrbit } from './genreCitationLayout'
import { createCitationBodies } from './genreCitationPhysics'

const TRAIL_LIGHT = { out: '117,180,254', in: '255,188,108' }
const ARC_STEPS = 256
const PARTICLE_SHADES = 12
const WAVE_BANDS = [[-10, .24], [8, .14], [21, .09]]
export const STAR_BEAT_PERIOD = 3.6
export const STAR_BEAT_TRAVEL = 2.75
export const starBeatOffset = direction => direction === 'in' ? .28 : 0

function seededRandom(seed = 985173) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
    return seed / 4294967296
  }
}

function glowSprite(rgb) {
  const sprite = document.createElement('canvas')
  sprite.width = sprite.height = 80
  const context = sprite.getContext('2d')
  const light = context.createRadialGradient(40, 40, 0, 40, 40, 40)
  light.addColorStop(0, 'rgba(' + rgb + ',.9)')
  light.addColorStop(.14, 'rgba(' + rgb + ',.42)')
  light.addColorStop(.36, 'rgba(' + rgb + ',.16)')
  light.addColorStop(.64, 'rgba(' + rgb + ',.045)')
  light.addColorStop(1, 'rgba(' + rgb + ',0)')
  context.fillStyle = light
  context.fillRect(0, 0, 80, 80)
  return sprite
}

function sizeCanvas(canvas, frame, displayWidth, maxPixelRatio) {
  const scale = Math.min(window.devicePixelRatio || 1, maxPixelRatio) * displayWidth / frame.width
  canvas.width = Math.max(1, Math.round(frame.width * scale))
  canvas.height = Math.max(1, Math.round(frame.height * scale))
  const context = canvas.getContext('2d')
  context?.setTransform(canvas.width / frame.width, 0, 0, canvas.height / frame.height, 0, 0)
  return context
}

export function drawCitationSky(canvas, frame, displayWidth, points, beacons, compact, orbitAt = citationOrbit) {
  const context = sizeCanvas(canvas, frame, displayWidth, 2)
  if (!context) return

  const random = seededRandom()
  function dot(x, y, radius, opacity, rgb) {
    context.beginPath()
    context.arc(x, y, radius, 0, Math.PI * 2)
    context.fillStyle = 'rgba(' + rgb + ',' + opacity + ')'
    context.fill()
  }

  // The dust is a decorative field. It sits behind the interactive noteheads.
  for (let i = 0; i < 650; i++) {
    const x = random() * frame.width
    const y = random() * frame.height
    const light = random() ** 3
    dot(x, y, .33 + light * .67, .08 + light * .37, i % 5 === 0 ? '227,187,142' : '183,211,242')
  }

  const sprites = Object.fromEntries(Object.entries(TRAIL_LIGHT).map(([direction, rgb]) => [direction, glowSprite(rgb)]))
  context.globalCompositeOperation = 'lighter'
  for (const [direction, rgb] of Object.entries(TRAIL_LIGHT)) {
    for (let i = 0; i < 480; i++) {
      const progress = random()
      const offset = (random() + random() - 1) * 54
      const { x, y } = orbitAt(progress, direction, offset, compact)
      const light = random() ** 3
      dot(x, y, .19 + light * .7, (.04 + light * .38) * Math.sin(Math.PI * progress) ** .45, rgb)
    }
  }
  for (const [i, point] of points.entries()) {
    const sprite = sprites[point.direction]
    const rgb = TRAIL_LIGHT[point.direction]
    if (i % 5 === 0) {
      const size = 97 + random() * 50
      context.globalAlpha = .06 + .04 * random()
      context.drawImage(sprite, point.x - size / 2, point.y - size / 2, size, size)
    }
    const halo = 13 + point.radius * 5
    context.globalAlpha = Math.min(.46, .14 + point.weight * .043)
    context.drawImage(sprite, point.x - halo / 2, point.y - halo / 2, halo, halo)

    context.globalAlpha = 1
    for (let j = 0; j < 10; j++) {
      const dx = (random() + random() - 1) * 56
      const dy = (random() + random() - 1) * 42
      const light = random() ** 2
      dot(point.x + dx, point.y + dy, .23 + light * .84, .09 + light * .57, rgb)
    }
  }
  for (const point of beacons) {
    const sprite = sprites[point.direction]
    const size = compact ? 120 : 142
    context.globalAlpha = .84
    context.drawImage(sprite, point.x - size / 2, point.y - size / 2, size, size)
  }
}

function arcSamples(direction, compact, orbitAt) {
  return Array.from({ length: ARC_STEPS + 1 }, (_, i) => {
    const progress = i / ARC_STEPS
    const center = orbitAt(progress, direction, 0, compact)
    const outer = orbitAt(progress, direction, 1, compact)
    return { ...center, progress, nx: outer.x - center.x, ny: outer.y - center.y }
  })
}

function pointOnTrail(trail, progress, offset) {
  const position = progress * ARC_STEPS
  const index = Math.min(Math.floor(position), ARC_STEPS - 1)
  const fraction = position - index
  const a = trail.samples[index]
  const b = trail.samples[index + 1]
  const x = a.x + offset * a.nx
  const y = a.y + offset * a.ny
  trail.point.x = x + fraction * (b.x + offset * b.nx - x)
  trail.point.y = y + fraction * (b.y + offset * b.ny - y)
  return trail.point
}

function orbitParticles(compact, orbitAt) {
  const random = seededRandom(11921)
  const count = compact ? 164 : 290
  return Object.keys(TRAIL_LIGHT).map(direction => {
    const samples = arcSamples(direction, compact, orbitAt)
    const wave = samples.filter((_, index) => index % 2 === 0).map(sample => ({
      ...sample,
      delay: (sample.progress * STAR_BEAT_TRAVEL + starBeatOffset(direction)) / STAR_BEAT_PERIOD,
      envelope: Math.sin(Math.PI * sample.progress) * 17,
      amplitude: 0,
    }))
    return {
      samples, wave, point: { x: 0, y: 0 },
      glow: glowSprite(TRAIL_LIGHT[direction]),
      core: direction === 'out' ? '#dcedff' : '#fff0d2',
      particles: Array.from({ length: count }, () => ({
        start: random(),
        speed: .018 + random() * .045,
        offset: (random() + random() - 1) * 66,
        radius: .38 + random() ** 3 * 1.6,
        phase: random() * Math.PI * 2,
        opacity: .26 + random() * .62,
      })),
    }
  })
}

function paintWave(context, trail, seconds) {
  for (const sample of trail.wave) {
    const beat = seconds / STAR_BEAT_PERIOD - sample.delay
    const phase = beat - Math.floor(beat)
    const swell = Math.exp(-Math.pow((phase - .23) / .118, 2))
    const echo = .46 * Math.exp(-Math.pow((phase - .48) / .095, 2))
    sample.amplitude = sample.envelope * (swell + echo)
  }
  context.strokeStyle = trail.core
  for (const [offset, strength] of WAVE_BANDS) {
    context.beginPath()
    for (const sample of trail.wave) {
      const ripple = Math.sin(sample.progress * 67 - seconds * 5.8 + offset * .13)
      const distance = offset + ripple * sample.amplitude
      const x = sample.x + distance * sample.nx
      const y = sample.y + distance * sample.ny
      if (sample.progress === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    }
    context.lineWidth = offset === -10 ? 1.15 : .72
    context.globalAlpha = strength
    context.stroke()
  }
}

function paintParticles(context, trails, seconds, pointer) {
  context.globalCompositeOperation = 'lighter'
  for (const [index, trail] of trails.entries()) {
    paintWave(context, trail, seconds)
    context.fillStyle = trail.core
    const dots = Array.from({ length: PARTICLE_SHADES }, () => new Path2D())
    for (const particle of trail.particles) {
      const progress = (particle.start + seconds * particle.speed) % 1
      const drift = Math.sin(seconds * .95 + particle.phase) * 7
      const position = pointOnTrail(trail, progress, particle.offset + drift)
      const fade = Math.min(1, progress * 8, (1 - progress) * 8)
      const twinkle = .72 + .28 * Math.sin(seconds * 2 + particle.phase)
      const alpha = particle.opacity * fade * twinkle
      const x = position.x + pointer.dx * (particle.radius + .4)
      const y = position.y + pointer.dy * (particle.radius + .4)
      const radius = particle.radius

      if (radius > .95) {
        const spread = radius * 10
        context.globalAlpha = alpha * .78
        context.drawImage(trail.glow, x - spread / 2, y - spread / 2, spread, spread)
      }
      const shade = Math.round(alpha * PARTICLE_SHADES)
      if (shade) {
        const path = dots[shade - 1]
        path.moveTo(x + radius, y)
        path.arc(x, y, radius, 0, Math.PI * 2)
      }
    }
    for (let shade = 0; shade < dots.length; shade++) {
      context.globalAlpha = (shade + 1) / PARTICLE_SHADES
      context.fill(dots[shade])
    }

    // A pair of traveling accents makes the groove's motion legible at a glance.
    const head = (seconds * .095 + .2 + index * .48) % 1
    const intensity = Math.sin(Math.PI * head)
    for (let step = 16; step >= 0; step--) {
      const progress = head - step * .0029
      if (progress < 0) continue
      const point = pointOnTrail(trail, progress, 2)
      const size = step === 0 ? 54 : 19 - step * .65
      context.globalAlpha = intensity * (step === 0 ? .9 : .5 * (1 - step / 17))
      context.drawImage(trail.glow, point.x - size / 2, point.y - size / 2, size, size)
    }
    const point = pointOnTrail(trail, head, 2)
    context.globalAlpha = intensity * .8
    context.beginPath()
    context.arc(point.x, point.y, 2.35, 0, Math.PI * 2)
    context.fill()
  }
}

export function mountCitationMotion(canvas, plate, orbitAt = citationOrbit) {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
  const pointer = {
    clientX: 0, clientY: 0, x: 0, y: 0, glowX: 0, glowY: 0,
    dx: 0, dy: 0, strength: 0, aimed: null, inside: false,
  }
  const bodies = createCitationBodies()
  const pointerGlow = glowSprite('146,198,255')
  let frame
  let compact
  let context
  let trails = []
  let waveBands = []
  let visible = true
  let request = 0
  let startedAt = null
  let lastFrame = null
  let nextSkyPaint = 0
  let meanFrameMs = 1000 / 60
  let skyInterval = 1000 / 60
  let plateRect = null

  function invalidateBounds() {
    plateRect = null
  }

  function toPlot(clientX, clientY) {
    plateRect ??= plate.getBoundingClientRect()
    if (!frame || !plateRect.width || !plateRect.height) return null
    const scale = frame.width / plateRect.width
    return {
      x: (clientX - plateRect.left) * scale,
      y: (clientY - plateRect.top) * frame.height / plateRect.height,
      scale,
    }
  }

  function canPlay() {
    return context && visible && !reduce.matches && !document.hidden
  }

  function clear() {
    if (context && frame) context.clearRect(0, 0, frame.width, frame.height)
  }

  function moveWaveBands(seconds, strength, delta) {
    const held = bodies.position(pointer.aimed)?.waveBand
    const follow = 1 - Math.exp(-delta * 11)
    for (const band of waveBands) {
      if (band === held) continue
      const phase = seconds / STAR_BEAT_PERIOD - (band.progress * STAR_BEAT_TRAVEL + starBeatOffset(band.direction)) / STAR_BEAT_PERIOD
      const cycle = phase - Math.floor(phase)
      const crest = Math.exp(-(((cycle - .23) / .15) ** 2))
      const echo = Math.exp(-(((cycle - .5) / .16) ** 2))
      const distance = strength * (compact ? 5.2 : 3.8) * (crest - .46 * echo)
      const x = band.x + (distance * band.nx - band.x) * follow
      const y = band.y + (distance * band.ny - band.y) * follow
      if (Math.abs(x - band.x) + Math.abs(y - band.y) < .008) continue
      band.x = x
      band.y = y
      band.element.setAttribute('transform', 'translate(' + x.toFixed(2) + ',' + y.toFixed(2) + ')')
    }
  }
  function resetWaveBands() {
    for (const band of waveBands) {
      band.x = band.y = 0
      band.element.removeAttribute('transform')
    }
  }

  function sync() {
    if (canPlay()) {
      if (!request) request = requestAnimationFrame(paint)
    } else {
      cancelAnimationFrame(request)
      request = 0
      lastFrame = null
      nextSkyPaint = 0
      if (reduce.matches) {
        clear()
        bodies.reset()
        resetWaveBands()
      }
    }
  }

  function paint(now) {
    request = 0
    if (!canPlay()) return
    startedAt ??= now
    const elapsed = lastFrame === null ? 1000 / 60 : Math.min(50, now - lastFrame)
    const delta = elapsed / 1000
    lastFrame = now
    if (pointer.inside) {
      const point = toPlot(pointer.clientX, pointer.clientY)
      if (point) {
        pointer.x = point.x
        pointer.y = point.y
        if (pointer.strength < .02) {
          pointer.glowX = point.x
          pointer.glowY = point.y
        }
        const follow = 1 - Math.exp(-delta * 7.84)
        pointer.glowX += (point.x - pointer.glowX) * follow
        pointer.glowY += (point.y - pointer.glowY) * follow
      }
    }
    pointer.strength += (Number(pointer.inside) - pointer.strength) * (1 - Math.exp(-delta * 5.95))
    if (waveBands.length) moveWaveBands((now - startedAt) / 1000, 1 - pointer.strength, delta)
    bodies.step(delta, pointer, frame, compact)

    // Input and data marks follow every refresh. Only the dust and waves
    // give up a paint when the browser sustains longer frames.
    meanFrameMs += (elapsed - meanFrameMs) * .08
    if (meanFrameMs > 22) skyInterval = 1000 / 30
    else if (meanFrameMs < 18) skyInterval = 1000 / 60
    if (now + .5 >= nextSkyPaint) {
      nextSkyPaint = Math.max(nextSkyPaint + skyInterval, now + skyInterval / 2)
      pointer.dx = (pointer.glowX / frame.width - .5) * 12 * pointer.strength
      pointer.dy = (pointer.glowY / frame.height - .5) * 10 * pointer.strength
      clear()
      paintParticles(context, trails, (now - startedAt) / 1000, pointer)
      if (pointer.strength > .01) {
        context.globalAlpha = pointer.strength * .25
        context.drawImage(pointerGlow, pointer.glowX - 51, pointer.glowY - 51, 102, 102)
        context.globalAlpha = pointer.strength * .4
        context.drawImage(pointerGlow, pointer.glowX - 14, pointer.glowY - 14, 28, 28)
      }
      context.globalAlpha = 1
    }
    sync()
  }

  const visibility = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting
    invalidateBounds()
    plate.toggleAttribute('data-out-of-view', !visible)
    if (!visible) pointer.inside = false
    sync()
  })
  visibility.observe(plate)
  reduce.addEventListener('change', sync)
  document.addEventListener('visibilitychange', sync)
  window.addEventListener('scroll', invalidateBounds, { capture: true, passive: true })
  window.addEventListener('resize', invalidateBounds)

  return {
    resize(bounds, displayWidth, useCompact) {
      invalidateBounds()
      frame = bounds
      if (compact !== useCompact) trails = orbitParticles(useCompact, orbitAt)
      compact = useCompact
      context = sizeCanvas(canvas, frame, displayWidth, 1.5)
      sync()
    },
    move(event) {
      if (event.pointerType === 'touch' || reduce.matches) return
      pointer.clientX = event.clientX
      pointer.clientY = event.clientY
      pointer.inside = true
    },
    leave() {
      pointer.inside = false
      invalidateBounds()
    },
    aim(key) {
      pointer.aimed = key ?? null
    },
    setBodies(entries, bands = []) {
      waveBands = bands
      resetWaveBands()
      bodies.replace(entries)
      if (reduce.matches) bodies.reset()
    },
    nearest(event, pixels) {
      const point = toPlot(event.clientX, event.clientY)
      return point ? bodies.nearest(point.x, point.y, pixels * point.scale) : null
    },
    dispose() {
      cancelAnimationFrame(request)
      visibility.disconnect()
      reduce.removeEventListener('change', sync)
      document.removeEventListener('visibilitychange', sync)
      window.removeEventListener('scroll', invalidateBounds, true)
      window.removeEventListener('resize', invalidateBounds)
    },
  }
}
