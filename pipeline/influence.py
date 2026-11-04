"""Explain artist influence with raw reference edges and explicit work-credit provenance."""
from __future__ import annotations

from collections import Counter, defaultdict

from pipeline.common import ACTOR_TYPES, CREDIT_TYPES, OBSERVATION_YEAR, Dataset, rounded


def build_evidence(ds: Dataset, focus_id: int = 17255, attribution: str = "performers") -> dict:
    if attribution not in {"performers", "creative_credits"}:
        raise ValueError("Unknown attribution scope")
    allowed = {"PerformerOf"} if attribution == "performers" else CREDIT_TYPES
    credits = defaultdict(lambda: defaultdict(list))
    for edge in ds.links:
        if (edge["type"] in allowed and ds.nodes[edge["source"]]["type"] in ACTOR_TYPES
                and ds.visible_work(edge["target"])):
            credits[edge["target"]][edge["source"]].append(edge)

    def attribution_rows(entity):
        if ds.nodes[entity]["type"] in ACTOR_TYPES:
            return [{"artist_id": entity, "work_id": None, "roles": [], "edge_ids": []}]
        return [{"artist_id": actor, "work_id": entity,
                 "roles": sorted({e["type"] for e in edges}),
                 "edge_ids": sorted(e["id"] for e in edges)}
                for actor, edges in sorted(credits.get(entity, {}).items())]

    events = []
    for event in ds.influence_events():
        sources, targets = attribution_rows(event["source"]), attribution_rows(event["target"])
        source_actor = ds.nodes[event["source"]]["type"] in ACTOR_TYPES
        target_actor = ds.nodes[event["target"]]["type"] in ACTOR_TYPES
        kind = ("explicit_artist_reference" if source_actor and target_actor else
                "work_attribution" if not source_actor and not target_actor else "mixed_attribution")
        events.append({**event, "evidence_kind": kind, "source_credits": sources, "target_credits": targets,
                       "observable_at_cutoff": all(ds.nodes[i]["type"] in ACTOR_TYPES or ds.visible_work(i)
                                                   for i in (event["source"], event["target"]))})
    result = {
        "meta": {**ds.meta, "attribution_scope": attribution,
                 "direction": "inspiration artist -> influenced artist",
                 "weight": "one event split over source x target credited artists; self-pairs removed without redistribution",
                 "inference": "work attribution infers artist association from explicit credits; not proof of a personal or causal relationship",
                 "undated_policy": "retained as structural evidence at 2040 only; never assigned a year",
                 "path_policy": "at most 3 deterministic examples per peer; all event IDs retained"},
        "events": events,
        "summary": {"event_count": len(events),
                    "evidence_kinds": dict(sorted(Counter(e["evidence_kind"] for e in events).items())),
                    "dated_attributable_event_count": sum(e["eligible_dated"] and bool(e["source_credits"])
                                                          and bool(e["target_credits"]) for e in events),
                    "dated_unattributable_event_count": sum(e["eligible_dated"] and not (e["source_credits"] and e["target_credits"]) for e in events)},
    }
    result["focus"] = focus_evidence(ds, result, focus_id)
    return result


def artist_pairs(event: dict):
    sources, targets = event["source_credits"], event["target_credits"]
    if not sources or not targets:
        return
    fraction = 1 / (len(sources) * len(targets))
    for source in sources:
        for target in targets:
            if source["artist_id"] != target["artist_id"]:
                yield source["artist_id"], target["artist_id"], fraction


def dated_events(evidence: dict, include_chronology: bool = False, weights: dict | None = None):
    """An alternative chronology policy still cannot use invisible/future endpoints."""
    cutoff = evidence["meta"]["cutoff_year"]
    for event in evidence["events"]:
        if weights is not None and weights.get(event["type"], 0) <= 0:
            continue
        eligible = event["eligible_dated"]
        if include_chronology:
            eligible = (event["observable_at_cutoff"] and event["year"] is not None
                        and event["year"] <= cutoff
                        and not set(event["quality_flags"]) & {"self_loop", "duplicate_relation"})
        if eligible:
            yield event


def evidence_path(event: dict, source_artist: int, target_artist: int) -> dict:
    source = next(c for c in event["source_credits"] if c["artist_id"] == source_artist)
    target = next(c for c in event["target_credits"] if c["artist_id"] == target_artist)
    steps = []
    if source["work_id"] is not None:
        steps.append({"from": source_artist, "to": source["work_id"],
                      "edge_id": source["edge_ids"][0], "traversal": "forward"})
    steps.append({"from": event["source"], "to": event["target"],
                  "edge_id": event["id"], "traversal": "reverse"})
    if target["work_id"] is not None:
        steps.append({"from": target["work_id"], "to": target_artist,
                      "edge_id": target["edge_ids"][0], "traversal": "reverse"})
    return {"event_id": event["id"], "evidence_kind": event["evidence_kind"], "year": event["year"],
            "node_path": [steps[0]["from"]] + [s["to"] for s in steps], "steps": steps}


def focus_evidence(ds: Dataset, evidence: dict, focus_id: int) -> dict:
    if focus_id not in ds.nodes:
        raise ValueError(f"Unknown focus node: {focus_id}")
    incoming, outgoing = {}, {}
    for event in evidence["events"]:
        if not event["eligible_structural"]:
            continue
        if ds.cutoff < OBSERVATION_YEAR and not event["eligible_dated"]:
            continue
        for source, target, fraction in artist_pairs(event):
            if focus_id not in (source, target):
                continue
            peer = target if source == focus_id else source
            groups = outgoing if source == focus_id else incoming
            if peer not in groups:
                groups[peer] = {"id": peer, "name": ds.nodes[peer]["display_name"], "event_ids": [],
                                "explicit_reference_count": 0, "attributed_reference_count": 0,
                                "dated_count": 0, "undated_count": 0, "fractional_attributed_weight": 0.0,
                                "by_type": Counter(), "example_paths": []}
            row = groups[peer]
            row["event_ids"].append(event["id"])
            explicit = event["evidence_kind"] == "explicit_artist_reference"
            row["explicit_reference_count" if explicit else "attributed_reference_count"] += 1
            row["dated_count" if event["year"] is not None else "undated_count"] += 1
            if not explicit:
                row["fractional_attributed_weight"] += fraction
            row["by_type"][event["type"]] += 1
            if len(row["example_paths"]) < 3:
                row["example_paths"].append(evidence_path(event, source, target))

    def finish(rows):
        for row in rows.values():
            row["event_ids"].sort()
            row["fractional_attributed_weight"] = rounded(row["fractional_attributed_weight"])
            row["by_type"] = dict(sorted(row["by_type"].items()))
            row["omitted_example_count"] = len(row["event_ids"]) - len(row["example_paths"])
        return sorted(rows.values(), key=lambda r: (-len(r["event_ids"]), r["id"]))

    return {"id": focus_id, "incoming": finish(incoming), "outgoing": finish(outgoing)}


def influence_scores(evidence: dict, weights: dict, include_chronology: bool = False) -> dict:
    artists, genres, relation_mass = Counter(), Counter(), Counter()
    count, attributed_mass, self_mass = 0, 0.0, 0.0
    for event in dated_events(evidence, include_chronology, weights):
        count += 1
        weight = weights[event["type"]]
        relation_mass[event["type"]] += weight
        if event["source_genre"] and event["target_genre"] and event["source_genre"] != event["target_genre"]:
            genres[event["source_genre"]] += weight
        sources, targets = event["source_credits"], event["target_credits"]
        if sources and targets:
            surviving = 0.0
            for source, _, fraction in artist_pairs(event):
                artists[source] += weight * fraction
                surviving += fraction
            attributed_mass += weight * surviving
            self_mass += weight * (1 - surviving)
    return {"artists": {i: rounded(v) for i, v in artists.items()},
            "genres": {g: rounded(v) for g, v in genres.items()},
            "event_count": count, "weighted_event_mass": rounded(sum(relation_mass.values())),
            "relation_mass": {k: rounded(v) for k, v in sorted(relation_mass.items())},
            "attributed_artist_mass": rounded(attributed_mass), "removed_self_mass": rounded(self_mass)}
