import { forceCollide, forceSimulation, forceX, forceY } from 'd3'
import { FLOW_TYPES } from './palette.js'

export function citationFrame(compact = false) {
  return compact
    ? { width: 720, height: 880, rx: 290, ry: 265 }
    : { width: 1280, height: 625, rx: 530, ry: 202 }
}

export function citationOrbit(progress, direction, offset = 0, compact = false) {
  const degrees = direction === 'out' ? 193 + 151 * progress : 156 - 143 * progress
  return citationEllipse(degrees * Math.PI / 180, offset, compact)
}

export function citationEllipse(angle, offset = 0, compact = false) {
  const frame = citationFrame(compact)
  const x = (frame.rx + offset) * Math.cos(angle)
  const y = (frame.ry + offset) * Math.sin(angle)
  const tilt = compact ? -.13 : -.105
  return {
    x: frame.width / 2 + x * Math.cos(tilt) - y * Math.sin(tilt),
    y: frame.height / 2 + x * Math.sin(tilt) + y * Math.cos(tilt),
  }
}

export function citationPosition(year, [start, end], direction, offset, compact) {
  const progress = start === end ? .5 : (year - start) / (end - start)
  return citationOrbit(progress, direction, offset, compact)
}

export function citationKey({ year, source, target, type }) {
  return JSON.stringify([year, source, target, type])
}

export function layoutCitations(samples, extent, compact = false) {
  const indexByYear = new Map()
  const radiusUnit = compact ? 3.6 : 3.05
  const points = samples.map(({ year, value, type, direction }) => {
    const voice = Math.max(0, FLOW_TYPES.indexOf(type))
    const anchor = citationPosition(year, extent, direction, (voice - 2) * 12, compact)
    const key = direction + '|' + voice + '|' + year
    const index = indexByYear.get(key) ?? 0
    indexByYear.set(key, index + 1)
    const angle = index * 2.399963
    const distance = 4.1 * Math.sqrt(index)
    return { anchor, direction, radius: radiusUnit * Math.sqrt(value),
      x: anchor.x + Math.cos(angle) * distance,
      y: anchor.y + Math.sin(angle) * distance }
  })

  // Position follows release year around each arc. Local collision offsets
  // keep the noteheads available for hit testing in dense years.
  for (const direction of ['out', 'in']) {
    const track = points.filter(point => point.direction === direction)
    forceSimulation(track).stop().alphaDecay(.042)
      .force('x', forceX(point => point.anchor.x).strength(.44))
      .force('y', forceY(point => point.anchor.y).strength(.32))
      .force('collision', forceCollide(point => point.radius + 1.1).iterations(2))
      .tick(100)
  }
  return points.map(({ x, y, radius }) => ({ x, y, radius }))
}
