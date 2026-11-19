import assert from 'node:assert/strict'
import test from 'node:test'
import { createCitationBodies } from './genreCitationPhysics.js'

const frame = { width: 1280, height: 625, rx: 530, ry: 202 }
const cursor = { x: 640, y: 144, inside: true, aimed: null }

function anchoredNote() {
  const bodies = createCitationBodies()
  const element = { writes: 0, setAttribute() { this.writes++ } }
  bodies.replace([{
    key: 'note', x: 640, y: 110, radius: 4, radialLimit: 23, tangentLimit: 9,
    element,
  }])
  return { bodies, element }
}

test('pointer displacement and return use the same timing across refresh rates', () => {
  const positions = [30, 60, 120].map(hz => {
    const { bodies } = anchoredNote()
    for (let i = 0; i < hz / 2; i++) bodies.step(1 / hz, cursor, frame, false)
    const pushed = bodies.position('note').y
    for (let i = 0; i < hz; i++) bodies.step(1 / hz, { ...cursor, inside: false }, frame, false)
    const returned = bodies.position('note').y
    assert.ok(pushed >= 110 - 23 && pushed < returned && returned < 110)
    return { pushed, returned }
  })
  for (const position of positions.slice(1)) {
    assert.ok(Math.abs(position.pushed - positions[0].pushed) < .01)
    assert.ok(Math.abs(position.returned - positions[0].returned) < .01)
  }
})

test('picking uses the displaced mark and holds it through a delayed click', () => {
  const { bodies, element } = anchoredNote()
  for (let i = 0; i < 30; i++) bodies.step(1 / 60, cursor, frame, false)
  const y = bodies.position('note').y
  const writes = element.writes
  assert.equal(bodies.nearest(640, 110, 9), null)
  const aimed = bodies.nearest(640, y + 5, 9)
  assert.equal(aimed, 'note')
  for (let i = 0; i < 60; i++) bodies.step(1 / 60, { x: 640, y: y + 5, inside: true, aimed }, frame, false)
  assert.equal(bodies.position('note').y, y)
  assert.equal(element.writes, writes)
  bodies.reset()
  assert.equal(bodies.nearest(640, 110, 9), 'note')
})

test('the citation picker follows the shared idle wave without changing the year anchor', () => {
  const bodies = createCitationBodies()
  const waveBand = { x: 0, y: 0 }
  bodies.replace([{ key: 'citation', x: 620, y: 100, radius: 3, radialLimit: 23, tangentLimit: 9,
    element: { setAttribute() {} }, waveBand }])
  for (const dy of [3.8, -1.7, 0]) {
    waveBand.y = dy
    bodies.step(1 / 60, { x: 0, y: 0, inside: false }, frame, false)
    assert.equal(bodies.nearest(620, 100 + dy, .5), 'citation')
    assert.equal(bodies.position('citation').homeY, 100)
  }
})
