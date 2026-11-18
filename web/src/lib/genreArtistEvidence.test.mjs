import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { genreArtistEvidence } from './genreArtistEvidence.js'

const nodes = [{ id: 1, name: 'One', type: 'Person' }, { id: 2, name: 'Band', type: 'MusicalGroup' },
  { id: 10, name: 'Origin', type: 'Song', genre: 'Oceanus Folk' },
  { id: 20, name: 'Receiving song', type: 'Song', genre: 'Indie Folk', notable: true, chart_year: null }]
const credit = id => ({ artist_id: id, work_id: 20, roles: ['PerformerOf'], edge_ids: [id + ':20:0'] })
const event = (id, extra = {}) => ({ id, source: 10, target: 20, source_genre: 'Oceanus Folk', target_genre: 'Indie Folk',
  year: 2025, type: 'CoverOf', eligible_dated: true, observable_at_cutoff: true, target_credits: [credit(1), credit(2)], ...extra })
const flow = ids => [{ source: 'Oceanus Folk', target: 'Indie Folk', event_ids: ids }]

test('credits deduplicate within each performer, while co-performers remain separate', () => {
  const e = event('a', { target_credits: [credit(1), credit(1), credit(2)] })
  const rows = genreArtistEvidence([e, e, event('b')], nodes, flow(['a', 'b', 'b']), 'Oceanus Folk')
  assert.equal(rows.length, 2)
  for (const row of rows) {
    assert.equal(row.count, 2)
    assert.equal(row.workCount, 1)
    assert.equal(row.notableCount, 1)
    assert.equal(row.works[0].chartYear, null)
    assert.equal(row.works[0].creditIds.length, 1)
    assert.deepEqual(row.eventIds, ['a', 'b'])
  }
})
test('only eligible outgoing events and explicit matching performer credits are attributed', () => {
  const events = [event('valid'), event('date', { eligible_dated: false }), event('future', { observable_at_cutoff: false }),
    event('reverse', { source_genre: 'Indie Folk', target_genre: 'Oceanus Folk' }),
    event('same', { target_genre: 'Oceanus Folk' }), event('wrong-work', { target_credits: [{ ...credit(1), work_id: 21 }] }),
    event('wrong-role', { target_credits: [{ ...credit(1), roles: ['ProducerOf'] }] }), event('outside-filter')]
  const rows = genreArtistEvidence(events, nodes, flow(events.slice(0, -1).map(e => e.id)), 'Oceanus Folk')
  assert.deepEqual(rows.map(row => row.count), [1, 1])
  assert.deepEqual(rows[0].eventIds, ['valid'])
})
test('missing names and notable metadata do not invent chart status', () => {
  const row = genreArtistEvidence([event('a')], nodes.filter(node => node.id !== 20), flow(['a']), 'Oceanus Folk')[0]
  assert.equal(row.notableCount, 0)
  assert.equal(row.works[0].name, '#20')
  assert.equal(row.works[0].references[0].sourceName, 'Origin')
})
test('real bundle preserves every reference and credit ID for the most-referenced performer', async () => {
  const read = async name => JSON.parse(await readFile(new URL('../../../data/processed/' + name + '.json', import.meta.url), 'utf8'))
  const [evidence, index, flows] = await Promise.all(['influence_evidence', 'node_index', 'genre_flows'].map(read))
  const rows = genreArtistEvidence(evidence.events, index.nodes, flows.flows, 'Oceanus Folk')
  assert.equal(rows.length, 511)
  const top = rows[0]
  assert.equal(top.name, 'Min He')
  assert.equal(top.count, 8)
  assert.equal(top.workCount, 1)
  const source = evidence.events.filter(event => event.eligible_dated && event.source_genre === 'Oceanus Folk'
    && event.target_genre !== 'Oceanus Folk' && event.target_credits.some(credit => credit.artist_id === top.id))
  assert.deepEqual([...top.eventIds].sort(), source.map(e => e.id).sort())
  const ids = new Set(source.flatMap(e => e.target_credits.filter(c => c.artist_id === top.id).flatMap(c => c.edge_ids)))
  assert.deepEqual(new Set(top.works.flatMap(work => work.creditIds)), ids)
})
