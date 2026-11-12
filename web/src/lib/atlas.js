import { arc, ribbonArrow } from 'd3'

export const HOME_GENRE = 'Oceanus Folk'
export const FLOW_TONES = { in: '#b36935', out: '#26799f' }

export function observeChartSize(element, resize) {
  let frame
  const observer = new ResizeObserver(([entry]) => {
    const { width, height } = entry.contentRect
    if (!width || !height) return
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => resize(Math.round(width), Math.round(height)))
  })
  observer.observe(element)
  return () => {
    observer.disconnect()
    cancelAnimationFrame(frame)
  }
}

export function summarizeNeighbors(rows, focus) {
  const neighbors = new Map()
  for (const row of rows) {
    if (row.source === row.target) continue
    const incoming = row.target === focus
    if (!incoming && row.source !== focus) continue
    const id = incoming ? row.source : row.target
    if (!neighbors.has(id)) neighbors.set(id, { id, in: 0, out: 0, rows: [] })
    const peer = neighbors.get(id)
    peer[incoming ? 'in' : 'out'] += row.value
    peer.rows.push(row)
  }
  return neighbors
}

export function orbitLayout(genres, width, height) {
  const compact = width < 650
  const cx = width / 2
  const cy = height / 2
  const ringGap = compact ? 35 : 58
  const radius = Math.max(56, Math.min(cy - ringGap - (compact ? 37 : 47), cx - ringGap - (compact ? 19 : 163)))
  const slice = 2 * Math.PI / Math.max(1, genres.length)
  const maxWorks = Math.max(1, ...genres.map(node => node.value))
  const band = arc().innerRadius(radius - 4).outerRadius(radius + (compact ? 5 : 8)).cornerRadius(2.5)
  const points = genres.map((node, index) => {
    const offset = index * slice
    const angle = offset - Math.PI / 2
    const x = cx + (radius + 8) * Math.cos(angle)
    const y = cy + (radius + 8) * Math.sin(angle)
    const span = slice * (.18 + .24 * Math.sqrt(node.value / maxWorks))
    return {
      ...node, x, y, angle, offset, span,
      band: band({ startAngle: offset - span, endAngle: offset + span }),
      left: x < cx, labelY: y,
    }
  })
  if (!compact) {
    for (const left of [true, false]) {
      const side = points.filter(node => node.left === left).sort((a, b) => a.y - b.y)
      let y = 11
      for (const point of side) {
        point.labelY = Math.max(point.y, y)
        y = point.labelY + 18
      }
      y = height - 11
      for (const point of side.reverse()) {
        point.labelY = Math.min(point.labelY, y)
        const labelEdge = Math.max(142, cx - radius - ringGap - 43)
        point.labelX = left ? labelEdge : width - labelEdge
        y = point.labelY - 18
      }
    }
  }
  return { compact, cx, cy, radius, ringGap, points }
}

/** Allocate ports along the focus arc and use D3's directed ribbons for each citation flow. */
export function orbitRibbons(layout, focusId, neighbors, direction) {
  const focus = layout.points.find(node => node.id === focusId)
  if (!focus) return []
  const routes = layout.points.flatMap(node => ['in', 'out']
    .filter(side => neighbors.get(node.id)?.[side] && (direction === 'all' || direction === side))
    .map(side => ({ node, direction: side, value: neighbors.get(node.id)[side] })))
  const weight = routes.reduce((sum, route) => sum + Math.sqrt(route.value), 0)
  const largest = Math.max(1, ...routes.map(route => route.value))
  const ribbon = ribbonArrow().headRadius(layout.compact ? 4 : 7)
  let cursor = focus.offset - focus.span
  return routes.map(({ node, direction, value }) => {
    const share = 2 * focus.span * Math.sqrt(value) / weight
    const focusPort = { startAngle: cursor, endAngle: cursor + share, radius: layout.radius - 5 }
    cursor += share
    const peerHalf = node.span * (.12 + .32 * Math.sqrt(value / largest))
    const peerCenter = node.offset + (direction === 'in' ? -.47 : .47) * node.span
    const peerPort = { startAngle: peerCenter - peerHalf, endAngle: peerCenter + peerHalf, radius: layout.radius - 5 }
    const [source, target] = direction === 'out' ? [focusPort, peerPort] : [peerPort, focusPort]
    const mid = port => {
      const angle = (port.startAngle + port.endAngle) / 2
      return [port.radius * Math.sin(angle), -port.radius * Math.cos(angle)].join(',')
    }
    return {
      id: node.id + ':' + direction, peer: node.id, direction, value,
      path: ribbon({ source, target }),
      trace: 'M' + mid(source) + ' Q0,0 ' + mid(target),
    }
  })
}
