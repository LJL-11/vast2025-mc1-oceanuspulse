"""Predeclared sensitivity scenarios for influence rules and candidate weights."""
from __future__ import annotations

from collections import Counter

from pipeline.common import Dataset, INFLUENCE_TYPES, rounded
from pipeline.artist_features import CANDIDATE_WEIGHTS, candidate_baseline
from pipeline.influence import build_evidence, dated_events, influence_scores
from pipeline.rankings import compare_rankings, top_set


def rule_scenarios(evidence: dict) -> list[dict]:
    counts = Counter(e["type"] for e in dated_events(evidence))
    total = sum(counts.values())
    types = sorted(INFLUENCE_TYPES)
    uniform = {key: 1.0 for key in types}
    equal_mass = {key: total / (len(counts) * counts[key]) if counts[key] else 0.0 for key in types}
    definitions = [
        ("baseline", "all five reference types, conservative chronology, performer attribution", uniform, False, "performers"),
        ("include_chronology", "include flagged chronology only when both endpoints are visible by cutoff", uniform, True, "performers"),
        ("style_only", "InStyleOf only", {key: float(key == "InStyleOf") for key in types}, False, "performers"),
        ("recording_reuse", "CoverOf, DirectlySamples and InterpolatesFrom only", {key: float(key in {"CoverOf", "DirectlySamples", "InterpolatesFrom"}) for key in types}, False, "performers"),
        ("without_lyrical_reference", "exclude LyricalReferenceTo", {key: float(key != "LyricalReferenceTo") for key in types}, False, "performers"),
        ("equal_type_mass", "equal total mass per observed relation type; total event mass preserved", equal_mass, False, "performers"),
        ("creative_credit_attribution", "all four explicit creative credit roles, artist deduplicated within each work", uniform, False, "creative_credits"),
    ]
    return [{"id": key, "description": text, "weights": weights,
             "include_chronology": chronology, "attribution_scope": attribution}
            for key, text, weights, chronology, attribution in definitions]


def candidate_weight_scenarios(features: dict, baseline: dict) -> list[dict]:
    constants = baseline["meta"]["constant_features"]
    base_weights = baseline["meta"]["weights"]
    informative_mass = sum(value for key, value in base_weights.items() if key not in constants)
    informative = {key: value / informative_mass if key not in constants else 0.0
                   for key, value in base_weights.items()} if informative_mass else dict(base_weights)
    keys = list(CANDIDATE_WEIGHTS)
    profiles = [
        ("baseline", dict(base_weights)),
        ("informative_features_only", informative),
        ("equal_feature_weights", {key: 1 / len(keys) for key in keys}),
        ("productivity_emphasis", dict(zip(keys, (0.40, 0.25, 0.10, 0.05, 0.20)))),
        ("network_emphasis", dict(zip(keys, (0.15, 0.40, 0.30, 0.05, 0.10)))),
    ]
    original = {r["id"]: r["score"] for r in baseline["candidates"]}
    rows = []
    for key, weights in profiles:
        ranking = candidate_baseline(features, baseline["meta"]["max_career_years"],
                                     baseline["meta"]["active_within"], weights)
        scores = {r["id"]: r["score"] for r in ranking["candidates"]}
        rows.append({"id": key, "weights": weights, "constant_weight_mass": ranking["meta"]["constant_weight_mass"],
                     "available_informative_weight_mass": rounded(1 - ranking["meta"]["constant_weight_mass"]),
                     "no_informative_features": not informative_mass,
                     "candidates": [{"id": r["id"], "name": r["name"], "score": r["score"], "rank": r["rank"]}
                                    for r in ranking["candidates"]],
                     "comparison": compare_rankings(original, scores, k=3, positive_only=False)})
    return rows


def robustness_report(ds: Dataset, evidence: dict, features: dict, baseline: dict, focus_id: int = 17255) -> dict:
    scenarios = rule_scenarios(evidence)
    alternate = build_evidence(ds, focus_id, "creative_credits")
    base_weights = scenarios[0]["weights"]
    base = influence_scores(evidence, base_weights)
    rows = []
    for definition in scenarios:
        source = alternate if definition["attribution_scope"] == "creative_credits" else evidence
        scores = influence_scores(source, definition["weights"], definition["include_chronology"])
        rows.append({**definition,
                     "event_count": scores["event_count"], "weighted_event_mass": scores["weighted_event_mass"],
                     "relation_mass": scores["relation_mass"], "attributed_artist_mass": scores["attributed_artist_mass"],
                     "removed_self_mass": scores["removed_self_mass"],
                     "focus_dated_outgoing_credit": scores["artists"].get(focus_id, 0.0),
                     "artist_comparison": compare_rankings(base["artists"], scores["artists"], k=5),
                     "genre_comparison": compare_rankings(base["genres"], scores["genres"], k=5),
                     "genre_scores": [{"genre": g, "score": value} for g, value in
                                      sorted(scores["genres"].items(), key=lambda p: (-p[1], p[0]))]})
    candidates = candidate_weight_scenarios(features, baseline)
    baseline_top = top_set({r["id"]: r["score"] for r in baseline["candidates"]}, 3, False)
    return {
        "meta": {**ds.meta, "scenario_policy": "predeclared rule changes; no outcome-based tuning",
                 "artist_metric": "fractional outgoing dated musical reference credit; not popularity or causal effect",
                 "genre_metric": "weighted cross-genre outgoing reference events",
                 "rank_comparison": "tie-aware Spearman; exclude common-zero entities for influence comparisons",
                 "top_set_policy": "include every boundary tie, never break ties by ID; empty sets give null similarity",
                 "interpretation": "descriptive sensitivity, not significance testing, validation accuracy, or confidence probability",
                 "undated_policy": "undated direct artist references excluded from every dated scenario"},
        "influence_scenarios": rows, "candidate_weight_scenarios": candidates,
        "diagnostics": {"baseline_dated_event_count": base["event_count"],
                        "undated_explicit_reference_count": sum(e["year"] is None and e["evidence_kind"] == "explicit_artist_reference" for e in evidence["events"]),
                        "baseline_candidate_top3": baseline_top,
                        "candidate_constant_features": baseline["meta"]["constant_features"],
                        "candidate_constant_weight_mass": baseline["meta"]["constant_weight_mass"],
                        "candidate_top3_unique_in_all_scenarios": bool(baseline["candidate_count"]) and all(
                            r["comparison"]["scenario_top"]["unique_top_k_set"] for r in candidates),
                        "warning": "Stable top-set overlap does not imply a unique Top3; inspect tie size and informative feature mass"},
    }
