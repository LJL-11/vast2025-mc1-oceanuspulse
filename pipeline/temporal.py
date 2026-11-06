"""Yearly as-of networks for a bounded comparison cohort and rolling genre evidence."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from itertools import combinations
import networkx as nx

from pipeline.common import ACTOR_TYPES, Dataset, rounded
from pipeline.artist_features import chart_year_as_of
from pipeline.influence import artist_pairs, dated_events
from pipeline.metrics import pagerank
from pipeline.rankings import rank_details


def select_cohort(ds: Dataset, baseline: dict, focus_id: int, compare_ids=(), candidate_limit: int = 10) -> dict:
    if candidate_limit < 0:
        raise ValueError("candidate_limit cannot be negative")
    group_ids = {e["target"] for e in ds.links if e["type"] == "MemberOf" and e["source"] == focus_id}
    members = {e["source"] for e in ds.links if e["type"] == "MemberOf" and e["target"] in group_ids}
    candidates = [r["id"] for r in baseline["candidates"][:candidate_limit]]
    selected = sorted({focus_id, *members, *candidates, *compare_ids})
    if any(i not in ds.nodes or ds.nodes[i]["type"] not in ACTOR_TYPES for i in selected):
        raise ValueError("Comparison cohort must contain known Person/MusicalGroup IDs")
    return {"ids": selected, "focus_id": focus_id, "explicit_compare_ids": sorted(set(compare_ids)),
            "group_context_ids": sorted(members), "candidate_ids": candidates,
            "candidate_display_limit": candidate_limit,
            "omitted_candidate_count": max(0, baseline["candidate_count"] - candidate_limit),
            "selection_note": "final-cutoff focal cohort; candidate order only selects a bounded display cohort, not a prediction or unbiased backtest sample",
            "membership_note": "undated MemberOf is used only to select context, never to assign work credits or date membership"}


def _collaboration(ds: Dataset, by_work: dict, start: int | None = None) -> nx.Graph:
    graph = nx.Graph()
    for work, actors in sorted(by_work.items()):
        if start is not None and ds.nodes[work]["release_year"] < start:
            continue
        graph.add_nodes_from(sorted(actors))
        for source, target in combinations(sorted(actors), 2):
            if not graph.has_edge(source, target):
                graph.add_edge(source, target, weight=0, first_year=ds.nodes[work]["release_year"])
            edge = graph[source][target]
            edge["weight"] += 1
            edge["first_year"] = min(edge["first_year"], ds.nodes[work]["release_year"])
    return graph


def genre_windows(ds: Dataset, evidence: dict, window: int = 5) -> list[dict]:
    if window < 1:
        raise ValueError("Rolling window must be positive")
    visible = [n for i, n in ds.nodes.items() if ds.visible_work(i)]
    genres = sorted({n["genre"] for n in visible})
    start = min((n["release_year"] for n in visible), default=ds.cutoff)
    events = [e for e in dated_events(evidence) if e["source_genre"] and e["target_genre"]]
    rows = []
    for year in range(start, ds.cutoff + 1):
        low = year - window + 1
        outgoing, incoming, internal, previous = (Counter() for _ in range(4))
        works, targets = defaultdict(set), defaultdict(set)
        denominator = 0
        for event in events:
            source, target, date = event["source_genre"], event["target_genre"], event["year"]
            if low <= date <= year:
                if source == target:
                    internal[source] += 1
                else:
                    denominator += 1
                    outgoing[source] += 1
                    incoming[target] += 1
                    works[source].add(event["target"])
                    targets[source].add(target)
            if low - window <= date < low and source != target:
                previous[source] += 1
        observed = min(window, year - start + 1)
        previous_observed = max(0, min(window, year - window - start + 1))
        for genre in genres:
            rows.append({"year": year, "genre": genre, "window_start": max(start, low),
                         "observed_years": observed, "previous_observed_years": previous_observed,
                         "outbound_events": outgoing[genre], "inbound_events": incoming[genre],
                         "internal_events": internal[genre], "all_cross_genre_events": denominator,
                         "outbound_share": rounded(outgoing[genre] / denominator) if denominator else None,
                         "external_influenced_work_count": len(works[genre]),
                         "external_target_genre_count": len(targets[genre]),
                         "previous_window_outbound_events": previous[genre],
                         "outbound_change_vs_previous_window": outgoing[genre] - previous[genre]
                         if observed == window and previous_observed == window else None})
    return rows


def network_dynamics(ds: Dataset, evidence: dict, cohort: dict, window: int = 5) -> dict:
    if window < 1:
        raise ValueError("Rolling window must be positive")
    _, final_credits = ds.credits()
    first_year = min((ds.nodes[w]["release_year"] for actor in cohort["ids"]
                      for w in final_credits.get(actor, {})), default=ds.cutoff)
    dataset_start = min((n["release_year"] for i, n in ds.nodes.items() if ds.visible_work(i)), default=ds.cutoff)
    series = {i: {"id": i, "name": ds.nodes[i]["display_name"], "rows": []} for i in cohort["ids"]}
    events = list(dated_events(evidence))
    network_sizes = []
    for year in range(first_year, ds.cutoff + 1):
        snapshot = replace(ds, cutoff=year)
        by_work, by_actor = snapshot.credits()
        graph = _collaboration(snapshot, by_work)
        rolling_start = year - window + 1
        rolling_graph = _collaboration(snapshot, by_work, rolling_start)
        pr = pagerank(graph)
        pr_ranks = rank_details(pr)
        influence = nx.DiGraph()
        influence.add_nodes_from(sorted(graph))
        recent_credit, annual_credit, cross_credit = Counter(), Counter(), Counter()
        cross_targets = defaultdict(set)
        event_count = 0
        for event in events:
            if event["year"] > year:
                continue
            event_count += 1
            for source, target, fraction in artist_pairs(event):
                if not influence.has_edge(source, target):
                    influence.add_edge(source, target, weight=0.0)
                influence[source][target]["weight"] += fraction
                if event["year"] >= rolling_start:
                    recent_credit[source] += fraction
                if event["year"] == year:
                    annual_credit[source] += fraction
                if event["source_genre"] and event["target_genre"] and event["source_genre"] != event["target_genre"]:
                    cross_credit[source] += fraction
                    cross_targets[source].add(event["target_genre"])
        source_pr = pagerank(influence.reverse(copy=False))
        source_ranks = rank_details({i: source_pr[i] for i in influence if influence.out_degree(i) > 0})
        artist_genres = {i: {ds.nodes[w]["genre"] for w in works} for i, works in by_actor.items()}
        network_sizes.append({"year": year, "credited_work_count": len(by_work),
                              "collaboration_nodes": len(graph), "collaboration_edges": graph.number_of_edges(),
                              "rolling_collaboration_nodes": len(rolling_graph),
                              "rolling_collaboration_edges": rolling_graph.number_of_edges(),
                              "dated_reference_events": event_count, "artist_influence_edges": influence.number_of_edges()})
        for actor in cohort["ids"]:
            works = by_actor.get(actor)
            if not works:
                continue
            neighbors = sorted(graph.neighbors(actor))
            peer_genres = set().union(*(artist_genres.get(i, set()) for i in neighbors)) if neighbors else set()
            own_genres = artist_genres[actor]
            previous = series[actor]["rows"][-1] if series[actor]["rows"] else None
            degree = graph.degree(actor)
            cumulative = {"work_count": len(works), "collaborator_count": degree,
                          "collaboration_pagerank": rounded(pr[actor]),
                          "collaboration_pagerank_percentile": pr_ranks[actor]["percentile"],
                          "known_charted_work_count": sum(chart_year_as_of(ds.nodes[w], year) is not None for w in works),
                          "collaborator_genre_count": len(peer_genres),
                          "outside_own_genre_collaborator_count": sum(bool(artist_genres[i] - own_genres) for i in neighbors),
                          "dated_influence_credit": rounded(influence.out_degree(actor, weight="weight")),
                          "dated_influenced_artist_count": influence.out_degree(actor),
                          "influence_source_pagerank": rounded(source_pr[actor]),
                          "influence_source_pagerank_percentile": source_ranks[actor]["percentile"] if actor in source_ranks else None,
                          "cross_genre_influence_credit": rounded(cross_credit[actor]),
                          "cross_genre_target_count": len(cross_targets[actor])}
            rolling = {"start_year": rolling_start, "end_year": year,
                       "observed_dataset_years": min(window, year - dataset_start + 1),
                       "work_count": sum(ds.nodes[w]["release_year"] >= rolling_start for w in works),
                       "collaborator_count": rolling_graph.degree(actor) if actor in rolling_graph else 0,
                       "new_collaborator_count": sum(graph[actor][i]["first_year"] >= rolling_start for i in neighbors),
                       "dated_influence_credit": rounded(recent_credit[actor])}
            annual = {"new_work_count": sum(ds.nodes[w]["release_year"] == year for w in works),
                      "new_collaborator_count": sum(graph[actor][i]["first_year"] == year for i in neighbors),
                      "new_dated_influence_credit": rounded(annual_credit[actor]),
                      "collaborator_change_yoy": degree - previous["cumulative"]["collaborator_count"] if previous else None}
            series[actor]["rows"].append({"year": year, "cumulative": cumulative, "rolling": rolling, "annual": annual})
    windows = genre_windows(ds, evidence, window)
    return {"meta": {**ds.meta, "window_years": window, "artist_year_range": [first_year, ds.cutoff],
                     "genre_year_range": [min((r["year"] for r in windows), default=ds.cutoff), ds.cutoff],
                     "cohort": cohort, "influence_scope": "dated, conservative, performer-attributed work references only",
                     "pagerank_scope": "recomputed on the entire as-of credited network; 0.85 damping; percentile for size-aware comparison",
                     "influence_percentile_scope": "only artists with positive dated outgoing influence; unavailable otherwise",
                     "rolling_origin_policy": "references dated within the window can cite older source works",
                     "history_limit": "retrospective final-cutoff cohort; release year proxies credit availability, not a collection-time backtest"},
            "artists": list(series.values()), "network_sizes": network_sizes,
            "genre_windows": windows}
