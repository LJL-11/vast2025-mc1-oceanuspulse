"""Yearly genre flows: inspiration genre -> influenced genre, with denominators."""
from __future__ import annotations

from collections import Counter, defaultdict
from pipeline.common import Dataset, OBSERVATION_YEAR, rounded


def genre_analytics(ds: Dataset) -> tuple[dict, dict]:
    visible = [n for i, n in ds.nodes.items() if ds.visible_work(i)]
    genres = sorted({n["genre"] for n in visible})
    start = min((n["release_year"] for n in visible), default=ds.cutoff)
    releases, songs, albums, chart_entries, observed_notable = (Counter() for _ in range(5))
    for n in visible:
        key = (n["release_year"], n["genre"])
        releases[key] += 1
        (songs if n["type"] == "Song" else albums)[key] += 1
        chart = n.get("chart_year")
        if (chart is not None and n["release_year"] <= chart <= ds.cutoff and n.get("notable") is True):
            chart_entries[(chart, n["genre"])] += 1
        if n.get("notable") is True:
            observed_notable[key] += 1
    groups = defaultdict(list)
    all_events = ds.influence_events()
    valid_events = [e for e in all_events if e["eligible_dated"]
                    and e["source_genre"] and e["target_genre"]]
    inbound, outbound, internal, cross_total = (Counter() for _ in range(4))
    external_targets = defaultdict(set)
    for e in valid_events:
        year, source, target = e["year"], e["source_genre"], e["target_genre"]
        groups[(year, source, target, e["type"])].append(e)
        if source == target:
            internal[(year, source)] += 1
        else:
            outbound[(year, source)] += 1
            inbound[(year, target)] += 1
            cross_total[year] += 1
            external_targets[(year, source)].add(e["target"])
    rows = []
    total_releases = Counter()
    for (year, _), count in releases.items():
        total_releases[year] += count
    for year in range(start, ds.cutoff + 1):
        for genre in genres:
            key = (year, genre)
            foreign_count = total_releases[year] - releases[key]
            rows.append({
                "year": year, "genre": genre, "work_count": releases[key],
                "song_count": songs[key], "album_count": albums[key],
                "new_chart_entries_known_date": chart_entries[key],
                "observed_notable_releases": observed_notable[key] if ds.cutoff == OBSERVATION_YEAR else None,
                "outbound_events": outbound[key], "inbound_events": inbound[key], "internal_events": internal[key],
                "all_cross_genre_events_in_year": cross_total[year],
                "outbound_share": rounded(outbound[key] / cross_total[year]) if cross_total[year] else None,
                "external_influenced_work_count": len(external_targets[key]),
                "all_external_work_releases": foreign_count,
                "external_work_coverage": rounded(len(external_targets[key]) / foreign_count) if foreign_count else None,
                "outbound_trailing_5y_mean": rounded(sum(outbound[(y, genre)] for y in range(max(start, year - 4), year + 1))
                                                      / min(5, year - start + 1)),
            })
    flow_rows = []
    for (year, source, target, relation), events in sorted(groups.items()):
        flow_rows.append({"year": year, "source": source, "target": target, "type": relation,
                          "value": len(events), "source_work_count": len({e['source'] for e in events}),
                          "target_work_count": len({e['target'] for e in events}),
                          "event_ids": sorted(e["id"] for e in events)})
    meta = {**ds.meta, "direction": "inspiration_genre -> influenced_genre",
            "year_basis": "influenced work release year, not the unknown exact influence date",
            "relations": sorted({e["type"] for e in all_events}),
            "dated_genre_event_count": len(valid_events), "all_reference_count": len(all_events),
            "excluded_event_count": len(all_events) - len(valid_events),
            "chart_warning": "Missing chart years are not imputed. notable is top-chart appearance, not rank #1.",
            "observed_notable_scope": "2040 labels grouped by release year; NOT chart events in that year"}
    return ({"meta": meta, "genres": genres, "years": list(range(start, ds.cutoff + 1)), "rows": rows},
            {"meta": meta, "flows": flow_rows})
