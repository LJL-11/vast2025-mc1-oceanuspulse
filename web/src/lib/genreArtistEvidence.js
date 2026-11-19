// Count references to a performer's credited works, not a personal influence score.
export function genreArtistEvidence(events, nodes, flows, focus) {
  const ids = new Set(flows.filter(flow => flow.source === focus && flow.target !== focus).flatMap(flow => flow.event_ids))
  const people = new Map()
  const nodeMap = new Map(nodes.map(node => [node.id, node]))
  for (const event of events) {
    if (!ids.has(event.id) || !event.eligible_dated || event.observable_at_cutoff === false
      || event.source_genre !== focus || event.target_genre === focus) continue
    for (const credit of event.target_credits ?? []) {
      const person = nodeMap.get(credit.artist_id)
      if (!person || !['Person', 'MusicalGroup'].includes(person.type)
        || credit.work_id !== event.target || !credit.roles.includes('PerformerOf')) continue
      let row = people.get(person.id)
      if (!row) {
        row = { id: person.id, name: person.display_name || person.name, type: person.type, events: new Map(), works: new Map() }
        people.set(person.id, row)
      }
      row.events.set(event.id, event)
      let work = row.works.get(event.target)
      if (!work) {
        const node = nodeMap.get(event.target)
        work = { id: event.target, name: node?.display_name || node?.name || '#' + event.target,
          genre: event.target_genre, year: node?.release_year ?? event.year,
          notable: node?.notable === true, chartYear: node?.chart_year ?? null,
          creditIds: new Set(), references: new Map() }
        row.works.set(event.target, work)
      }
      credit.edge_ids.forEach(id => work.creditIds.add(id))
      work.references.set(event.id, { ...event,
        sourceName: nodeMap.get(event.source)?.display_name || nodeMap.get(event.source)?.name || '#' + event.source })
    }
  }
  return [...people.values()].map(row => {
    const years = new Map()
    row.events.forEach(event => years.set(event.year, (years.get(event.year) ?? 0) + 1))
    return { ...row, eventIds: [...row.events.keys()], count: row.events.size, workCount: row.works.size,
      notableCount: [...row.works.values()].filter(work => work.notable).length,
      years: [...years].sort((a, b) => a[0] - b[0]),
      works: [...row.works.values()].map(work => ({ ...work, creditIds: [...work.creditIds], references: [...work.references.values()] })) }
  }).sort((a, b) => b.count - a.count || b.workCount - a.workCount || b.notableCount - a.notableCount || a.name.localeCompare(b.name))
}
