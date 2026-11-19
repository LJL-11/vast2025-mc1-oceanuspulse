function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value))
}

function approach(value, target, amount) {
  const next = value + (target - value) * amount
  return Math.abs(next - target) < .015 ? target : next
}

// Each note stays in its year band. The enclosing SVG group carries the idle wave.
export function createCitationBodies() {
  let bodies = new Map()

  function updatePosition(body, x, y) {
    body.x = x
    body.y = y
    const dx = (x - body.homeX).toFixed(2)
    const dy = (y - body.homeY).toFixed(2)
    const transform = 'translate(' + dx + ',' + dy + ')'
    if (body.transform !== transform) {
      body.element.setAttribute('transform', transform)
      body.transform = transform
    }
  }

  function reset() {
    for (const body of bodies.values()) {
      body.dx = body.dy = 0
      updatePosition(body, body.homeX, body.homeY)
    }
  }

  function replace(entries) {
    const updated = new Map()
    for (const entry of entries) {
      if (!entry.element) continue
      const previous = bodies.get(entry.key)
      const stable = previous?.homeX === entry.x && previous?.homeY === entry.y
      updated.set(entry.key, {
        ...entry, homeX: entry.x, homeY: entry.y,
        x: stable ? previous.x : entry.x, y: stable ? previous.y : entry.y,
        dx: stable ? previous.dx : 0, dy: stable ? previous.dy : 0,
        transform: stable && previous.element === entry.element ? previous.transform : null,
      })
    }
    bodies = updated
  }

  function step(delta, pointer, frame, compact) {
    const reach = compact ? 121 : 108
    const reachSquared = reach * reach
    const pushAmount = 1 - Math.exp(-delta / .26)
    const returnAmount = 1 - Math.exp(-delta / .44)
    for (const body of bodies.values()) {
      if (pointer.aimed === body.key) continue
      const awayX = body.homeX + (body.waveBand?.x ?? 0) - pointer.x
      const awayY = body.homeY + (body.waveBand?.y ?? 0) - pointer.y
      const distanceSquared = awayX * awayX + awayY * awayY
      const near = pointer.inside && distanceSquared < reachSquared
      if (!near && body.dx === 0 && body.dy === 0 && body.transform != null) continue

      const normalX = (body.homeX - frame.width / 2) / (frame.rx * frame.rx)
      const normalY = (body.homeY - frame.height / 2) / (frame.ry * frame.ry)
      const length = Math.hypot(normalX, normalY) || 1
      const nx = normalX / length, ny = normalY / length
      let targetX = 0, targetY = 0
      if (near) {
        const distance = Math.sqrt(distanceSquared)
        const t = 1 - distance / reach
        const force = t * t * (3 - 2 * t) * 32
        const x = force * (distance > .5 ? awayX / distance : nx)
        const y = force * (distance > .5 ? awayY / distance : ny)
        const radial = clamp(x * nx + y * ny, -body.radialLimit, body.radialLimit)
        const tangent = clamp(y * nx - x * ny, -body.tangentLimit, body.tangentLimit)
        targetX = radial * nx - tangent * ny
        targetY = radial * ny + tangent * nx
      }
      const amount = near ? pushAmount : returnAmount
      body.dx = approach(body.dx, targetX, amount)
      body.dy = approach(body.dy, targetY, amount)
      const radial = clamp(body.dx * nx + body.dy * ny, -body.radialLimit, body.radialLimit)
      const tangent = clamp(body.dy * nx - body.dx * ny, -body.tangentLimit, body.tangentLimit)
      const margin = body.radius + 5
      updatePosition(body,
        clamp(body.homeX + radial * nx - tangent * ny, margin, frame.width - margin),
        clamp(body.homeY + radial * ny + tangent * nx, margin, frame.height - margin),
      )
    }
  }

  function nearest(x, y, radius) {
    let key = null
    let bestDistance = radius * radius
    for (const body of bodies.values()) {
      const dx = x - body.x - (body.waveBand?.x ?? 0)
      const dy = y - body.y - (body.waveBand?.y ?? 0)
      const distance = dx * dx + dy * dy
      if (distance < bestDistance) {
        bestDistance = distance
        key = body.key
      }
    }
    return key
  }

  return { replace, reset, step, nearest, position: key => bodies.get(key) }
}
