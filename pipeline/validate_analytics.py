"""Cross-check the additive v1.1 evidence, time series and sensitivity contracts."""
from __future__ import annotations

from collections import defaultdict
import math

from pipeline.common import ACTOR_TYPES, INFLUENCE_TYPES
from pipeline.artist_features import chart_year_as_of
from pipeline.rankings import compare_rankings, top_set


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_analytics(files: dict, nodes: dict, links: dict, events: dict, feature_map: dict):
    evidence = files["influence_evidence.json"]
    by_id = {e["id"]: e for e in evidence["events"]}
    check(len(by_id) == len(evidence["events"]) and by_id.keys() == events.keys(), "Attribution evidence loses/duplicates references")
    for event in by_id.values():
        for key, value in events[event["id"]].items():
            check(event[key] == value, "Attribution evidence changes an original event")
        for side in ("source", "target"):
            credits = event[side + "_credits"]
            check(len({c["artist_id"] for c in credits}) == len(credits), "Multiple roles inflate attribution pairs")
            for credit in credits:
                actor, work = credit["artist_id"], credit["work_id"]
                check(actor in nodes and nodes[actor]["type"] in ACTOR_TYPES, "Non-artist credited as artist")
                if work is None:
                    check(actor == event[side] and not credit["edge_ids"], "Explicit artist relation has invented credits")
                else:
                    check(work == event[side] and bool(credit["edge_ids"]), "Work attribution lacks a credit edge")
                    for edge_id in credit["edge_ids"]:
                        edge = links[edge_id]
                        check((edge["source"], edge["target"], edge["type"]) == (actor, work, "PerformerOf"), "Default attribution is not backed by PerformerOf")
    focus = evidence["focus"]["id"]
    for direction in ("incoming", "outgoing"):
        for peer in evidence["focus"][direction]:
            check(peer["explicit_reference_count"] + peer["attributed_reference_count"] == len(peer["event_ids"]), "Focus evidence counts differ")
            check(peer["dated_count"] + peer["undated_count"] == len(peer["event_ids"]), "Focus dates differ")
            check(peer["omitted_example_count"] + len(peer["example_paths"]) == len(peer["event_ids"]), "Focus path examples silently truncated")
            expected_source, expected_target = (peer["id"], focus) if direction == "incoming" else (focus, peer["id"])
            for path in peer["example_paths"]:
                check(path["event_id"] in peer["event_ids"] and path["year"] == events[path["event_id"]]["year"], "Path has no corresponding reference/year")
                check(path["node_path"][0] == expected_source and path["node_path"][-1] == expected_target, "Attribution path endpoints differ")
                check(path["node_path"] == [path["steps"][0]["from"]] + [s["to"] for s in path["steps"]], "Path node list differs from steps")
                previous = expected_source
                for step in path["steps"]:
                    edge = links[step["edge_id"]]
                    expected = (edge["source"], edge["target"]) if step["traversal"] == "forward" else (edge["target"], edge["source"])
                    check((step["from"], step["to"]) == expected and previous == step["from"], "Path traverses an invented or disconnected edge")
                    previous = step["to"]
    dynamics = files["network_dynamics.json"]
    cutoff, window = dynamics["meta"]["cutoff_year"], dynamics["meta"]["window_years"]
    metrics = {r["id"]: r for r in files["node_metrics.json"]["nodes"]}
    check([r["id"] for r in dynamics["artists"]] == dynamics["meta"]["cohort"]["ids"], "Dynamics cohort differs from selection")
    for series in dynamics["artists"]:
        rows = series["rows"]
        if not rows:
            check(series["id"] not in feature_map, "Observed artist has an empty time series")
            continue
        feature = feature_map[series["id"]]
        check([r["year"] for r in rows] == list(range(feature["first_release_year"], cutoff + 1)), "Career network years missing/future")
        previous_degree = None
        for row in rows:
            year = row["year"]
            cumulative, rolling, annual = row["cumulative"], row["rolling"], row["annual"]
            works = [nodes[w] for w in feature["work_ids"] if nodes[w]["release_year"] <= year]
            check(cumulative["work_count"] == len(works), "Future work leaked into network history")
            check(cumulative["known_charted_work_count"] == sum(chart_year_as_of(w, year) is not None for w in works), "Future chart leaked into history")
            check(rolling["start_year"] == year - window + 1 and rolling["end_year"] == year, "Rolling window bounds differ")
            check(rolling["work_count"] == sum(w["release_year"] >= rolling["start_year"] for w in works), "Rolling works differ")
            check(annual["new_work_count"] == sum(w["release_year"] == year for w in works), "Annual works differ")
            degree = cumulative["collaborator_count"]
            expected_change = None if previous_degree is None else degree - previous_degree
            check(annual["collaborator_change_yoy"] == expected_change, "Annual collaborator change differs")
            if previous_degree is not None:
                check(degree >= previous_degree and annual["new_collaborator_count"] == expected_change, "Cumulative graph loses old collaborators")
            previous_degree = degree
            for key in ("collaboration_pagerank_percentile", "influence_source_pagerank_percentile"):
                check(cumulative[key] is None or 0 <= cumulative[key] <= 1, "Percentile out of bounds")
            if not cumulative["dated_influence_credit"]:
                check(cumulative["influence_source_pagerank_percentile"] is None, "No influence evidence assigned a prestige percentile")
            check(cumulative["cross_genre_influence_credit"] <= cumulative["dated_influence_credit"] + 1e-8, "Cross-genre credit exceeds total")
        final = rows[-1]["cumulative"]
        check(final["work_count"] == feature["work_count"] and final["collaborator_count"] == feature["collaborator_count"], "Final dynamics differs from canonical features")
        check(math.isclose(final["dated_influence_credit"], feature["influence_credit"], abs_tol=1e-8), "Final influence history differs from features")
        check(math.isclose(final["collaboration_pagerank"], metrics[series["id"]]["collaboration_pagerank"], abs_tol=1e-8), "Final PageRank history differs from metrics")
    if dynamics["network_sizes"]:
        last = dynamics["network_sizes"][-1]
        sizes = files["node_metrics.json"]["graph_sizes"]
        check(last["collaboration_nodes"] == sizes["collaboration_nodes"] and last["collaboration_edges"] == sizes["collaboration_edges"], "Final temporal graph size differs")
        check(last["artist_influence_edges"] == sizes["influence_edges"], "Final temporal influence edges differ")
    per_year = defaultdict(list)
    trends = files["genre_trends.json"]["rows"]
    for row in dynamics["genre_windows"]:
        per_year[row["year"]].append(row)
        matching = [r for r in trends if r["genre"] == row["genre"] and row["window_start"] <= r["year"] <= row["year"]]
        check(row["outbound_events"] == sum(r["outbound_events"] for r in matching), "Rolling genre outflow differs from annual evidence")
        check(row["inbound_events"] == sum(r["inbound_events"] for r in matching), "Rolling genre inflow differs from annual evidence")
        if row["previous_observed_years"] < window:
            check(row["outbound_change_vs_previous_window"] is None, "Partial history treated as a full comparison window")
    for rows in per_year.values():
        check(sum(r["outbound_events"] for r in rows) == sum(r["inbound_events"] for r in rows), "Rolling genre flow is not conserved")
    report = files["robustness_report.json"]
    scenarios = report["influence_scenarios"]
    check(len(scenarios) == 7 and len({r["id"] for r in scenarios}) == 7, "Missing influence sensitivity scenarios")
    for scenario in scenarios:
        check(set(scenario["weights"]) == INFLUENCE_TYPES and all(math.isfinite(w) and w >= 0 for w in scenario["weights"].values()), "Invalid relation weights")
        check(math.isclose(sum(scenario["relation_mass"].values()), scenario["weighted_event_mass"], abs_tol=1e-6), "Relation masses differ")
        for name in ("artist_comparison", "genre_comparison"):
            comparison = scenario[name]
            check(comparison["spearman"] is None or -1 <= comparison["spearman"] <= 1, "Rank correlation out of bounds")
            check(comparison["top_set_jaccard"] is None or 0 <= comparison["top_set_jaccard"] <= 1, "Top-set similarity out of bounds")
            for key in ("baseline_top", "scenario_top"):
                top = comparison[key]
                check(top["selected_count"] == len(top["ids"]) == len(set(top["ids"])), "Tie-aware top-set counts differ")
                check(top["unique_top_k_set"] == (top["selected_count"] == top["requested_k"]), "Ambiguous top set presented as unique")
    baseline = files["rising_star_baseline.json"]
    scores = {r["id"]: r["score"] for r in baseline["candidates"]}
    expected_top = top_set(scores, 3, False)
    check(report["diagnostics"]["baseline_candidate_top3"] == expected_top, "Candidate tie diagnostic differs")
    for scenario in report["candidate_weight_scenarios"]:
        candidate_scores = {r["id"]: r["score"] for r in scenario["candidates"]}
        check(candidate_scores.keys() == scores.keys(), "Weight experiment changes the candidate pool")
        check(scenario["comparison"] == compare_rankings(scores, candidate_scores, 3, False), "Candidate stability report differs from its scores")
        check(math.isclose(sum(scenario["weights"].values()), 1.0, abs_tol=1e-12), "Candidate experimental weights not normalized")
    check(scenarios[0]["event_count"] == sum(e["eligible_dated"] for e in events.values()), "Sensitivity baseline uses a different event set")
