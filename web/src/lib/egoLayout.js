import { arc } from 'd3'

const turn = Math.PI * 2
const typeOrder = ['Person', 'Song', 'Album', 'RecordLabel', 'MusicalGroup']
const ringSlice = arc()
export const EGO_CENTER_RADIUS = 55

function adjacency(links) {
  const neighbors = new Map()
  for (const { id, source, target } of links) {
    if (!neighbors.has(source)) neighbors.set(source, [])
    if (!neighbors.has(target)) neighbors.set(target, [])
    neighbors.get(source).push({ id, to: target })
    neighbors.get(target).push({ id, to: source })
  }
  return neighbors
}

function visitTwoHops(neighbors, anchor) {
  const visited = new Map([[anchor, { depth: 0 }]])
  let ring = [anchor]
  for (let depth = 1; depth <= 2; depth += 1) {
    const next = []
    for (const from of ring) {
      for (const edge of neighbors.get(from) ?? []) {
        if (visited.has(edge.to)) continue
        visited.set(edge.to, { depth, from, edgeId: edge.id })
        next.push(edge.to)
      }
    }
    ring = next
  }
  return visited
}

export function egoTrail(links, anchor, target) {
  if (anchor === target || target == null) return null
  const visited = visitTwoHops(adjacency(links), anchor)
  if (!visited.has(target)) return null
  const nodeIds = [target]
  const edgeIds = []
  for (let node = target; node !== anchor;) {
    const { from, edgeId } = visited.get(node)
    edgeIds.unshift(edgeId)
    nodeIds.unshift(from)
    node = from
  }
  return { nodeIds, edgeIds }
}

function polar(angle, radius) {
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }
}

function slice(start, end, innerRadius, outerRadius) {
  return ringSlice({ startAngle: start + Math.PI / 2, endAngle: end + Math.PI / 2, innerRadius, outerRadius })
}

function angleBetween(from, to) {
  return Math.atan2(Math.sin(to - from), Math.cos(to - from))
}

function byDateAndName(a, b) {
  return (a.release_year ?? 2100) - (b.release_year ?? 2100)
    || (a.display_name || a.name || '').localeCompare(b.display_name || b.name || '')
}

export function layOutEgo(nodes, links, anchor) {
  const root = nodes.find(node => node.id === anchor)
  const marks = new Map()
  if (!root) return { marks, sectors: [], counts: [0, 0] }
  const ids = new Set(nodes.map(node => node.id))
  const neighbors = adjacency(links.filter(link => ids.has(link.source) && ids.has(link.target)))
  const distances = visitTwoHops(neighbors, anchor)
  const groups = new Map([...new Set([...typeOrder, ...nodes.map(node => node.type)])]
    .map(type => [type, { type, near: [], far: [] }]))
  for (const node of nodes) {
    const depth = distances.get(node.id)?.depth
    if (depth === 1) groups.get(node.type).near.push(node)
    if (depth === 2) groups.get(node.type).far.push(node)
  }
  const populated = [...groups.values()].filter(group => group.near.length || group.far.length)
  const weight = group => Math.max(group.near.length, group.far.length / 2.6, 1)
  const totalWeight = populated.reduce((sum, group) => sum + weight(group), 0)
  const gap = .067
  const minimum = Math.min(.36, turn / Math.max(1, populated.length) * .52)
  let cursor = -Math.PI + .12
  const sectors = populated.map(group => {
    const span = minimum + (turn - populated.length * (minimum + gap)) * weight(group) / totalWeight
    const start = cursor
    const end = start + span
    const middle = (start + end) / 2
    cursor = end + gap
    return {
      ...group, start, end, middle, span,
      inner: slice(start, end, 117, 160),
      outer: slice(start, end, 177, 267),
      trim: slice(start, end, 269, 271),
      label: polar(middle, 293),
    }
  })
  marks.set(anchor, { node: root, id: anchor, depth: 0, angle: 0, radial: 0, x: 0, y: 0, size: EGO_CENTER_RADIUS })

  function place(group, sector, depth, radii) {
    const capacity = Math.ceil(group.length / radii.length)
    group.forEach((node, index) => {
      const row = Math.floor(index / capacity)
      const rowCount = Math.min(capacity, group.length - row * capacity)
      const slot = (index % capacity + .5 + (row % 2 ? .15 : -.13)) / rowCount
      const angle = sector.start + .095 + slot * (sector.span - .19)
      const radial = radii[row]
      const degree = (neighbors.get(node.id) ?? []).length
      const size = depth === 1 ? Math.min(6.4, 3.1 + Math.sqrt(degree) * .41)
        : Math.min(4.4, 2.25 + Math.sqrt(degree) * .32)
      marks.set(node.id, { node, id: node.id, depth, angle, radial, size, degree, ...polar(angle, radial) })
    })
  }
  for (const sector of sectors) {
    const radii = sector.near.length > 17 ? [132, 148] : [140]
    place(sector.near.sort(byDateAndName), sector, 1, radii)
  }
  for (const sector of sectors) {
    const arranged = sector.far.map(node => {
      const near = (neighbors.get(node.id) ?? []).map(edge => marks.get(edge.to))
        .filter(mark => mark?.depth === 1).sort((a, b) => b.degree - a.degree)[0]
      return { node, bearing: angleBetween(sector.middle, near?.angle ?? sector.middle) }
    }).sort((a, b) => a.bearing - b.bearing || byDateAndName(a.node, b.node))
    const slots = Math.max(1, Math.floor(sector.span * 223 / 11))
    const rings = Math.min(4, Math.max(1, Math.ceil(arranged.length / slots)))
    const radii = Array.from({ length: rings }, (_, index) => rings === 1 ? 225 : 194 + 60 * index / (rings - 1))
    place(arranged.map(entry => entry.node), sector, 2, radii)
  }
  const counts = sectors.reduce(([near, far], sector) => [near + sector.near.length, far + sector.far.length], [0, 0])
  return { marks, sectors, counts }
}

function inset(mark, control, margin) {
  const distance = Math.hypot(control.x - mark.x, control.y - mark.y)
  if (!distance) return mark
  const fraction = Math.min(.48, (mark.size + margin) / distance)
  return { x: mark.x + (control.x - mark.x) * fraction, y: mark.y + (control.y - mark.y) * fraction }
}

export function egoCurve(source, target, influence, lane = 0) {
  const offset = lane * .05
  let a, b
  if (!source.depth || !target.depth) {
    const spoke = source.depth ? source : target
    const inner = polar(spoke.angle + offset, 84)
    const outer = polar(spoke.angle - offset * .4, spoke.radial * .82)
    a = source.depth ? outer : inner
    b = source.depth ? inner : outer
  } else {
    const delta = angleBetween(source.angle, target.angle)
    const shallow = Math.min(source.radial, target.radial)
    const bend = Math.max(116, shallow * (.96 - .19 * Math.min(1, Math.abs(delta))))
    a = polar(source.angle + delta * .25 + offset, bend)
    b = polar(source.angle + delta * .75 + offset, bend)
  }
  const from = inset(source, a, 1)
  const to = inset(target, b, influence ? 2.5 : 1)
  const xy = point => point.x.toFixed(1) + ' ' + point.y.toFixed(1)
  return `M${xy(from)}C${xy(a)} ${xy(b)} ${xy(to)}`
}
