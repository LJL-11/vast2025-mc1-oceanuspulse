"""As-of artist features, dated career tracks and an explicitly heuristic candidate list."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import Counter, defaultdict
import math
from statistics import median

from pipeline.common import (Dataset, OBSERVATION_YEAR, collaboration_graph, load_dataset,
                             parser, performer_ids, rounded, write_json)

CANDIDATE_WEIGHTS = {"recent_5y_work_count": 0.20, "new_5y_collaborator_count": 0.25,
                     "recent_5y_influence_credit": 0.25, "genre_count": 0.10, "recent_work_share": 0.20}


def chart_year_as_of(node: dict, cutoff: int) -> int | None:
    """Unknown means unknown. A final-snapshot notable flag is not a historical event."""
    chart, release = node.get("chart_year"), node.get("release_year")
    if (node.get("notable") is True and chart is not None and release is not None
            and release <= chart <= cutoff):
        return chart
    return None


def artist_features(ds: Dataset) -> tuple[dict, dict]:
    by_work, by_actor = ds.credits()
    collab = collaboration_graph(ds)
    recent_start = ds.cutoff - 4
    influence_credit, recent_influence_credit = Counter(), Counter()
    influence_events_by_actor = defaultdict(set)
    for event in ds.influence_events():
        if not event["eligible_dated"]:
            continue
        origins = performer_ids(by_work, event["source"])
        consumers = performer_ids(by_work, event["target"])
        if not origins or not consumers:
            continue
        # Consistent with actor_influence_graph: exclude self-attribution without reallocating it.
        for origin in origins:
            weight = sum(consumer != origin for consumer in consumers) / (len(origins) * len(consumers))
            if weight:
                influence_credit[origin] += weight
                influence_events_by_actor[origin].add(event["id"])
                if event["year"] >= recent_start:
                    recent_influence_credit[origin] += weight

    feature_rows, timelines = [], []
    for actor, credits in sorted(by_actor.items()):
        works = [ds.nodes[w] for w in sorted(credits)]
        performed = [w for w in works if "PerformerOf" in credits[w["id"]]]
        oceanus_performed = [w for w in performed if w.get("genre") == "Oceanus Folk"]
        recent = [w for w in works if w["release_year"] >= recent_start]
        previous = [w for w in works if recent_start - 5 <= w["release_year"] < recent_start]
        releases = Counter(w["release_year"] for w in works)
        known_charts = [(w, chart_year_as_of(w, ds.cutoff)) for w in works]
        known_charts = [(w, y) for w, y in known_charts if y is not None]
        charts = Counter(year for _, year in known_charts)
        genre_counts = Counter(w["genre"] for w in works)
        role_counts = Counter(role for roles in credits.values() for role in roles)
        debut = min(releases)
        collaborators = sorted(collab.neighbors(actor))
        recent_collaborators = []
        new_collaborators = []
        first_collaborations = Counter()
        for neighbor in collaborators:
            years = [ds.nodes[w]["release_year"] for w in collab[actor][neighbor]["work_ids"]]
            first_collaborations[min(years)] += 1
            if max(years) >= recent_start:
                recent_collaborators.append(neighbor)
            if min(years) >= recent_start:
                new_collaborators.append(neighbor)
        chart_lags = [year - w["release_year"] for w, year in known_charts]
        counts = Counter(w["type"] for w in works)
        entropy = -sum((count / len(works)) * math.log2(count / len(works)) for count in genre_counts.values())
        first_chart = min(charts, default=None)
        row = {
            "id": actor, "name": ds.nodes[actor]["display_name"], "type": ds.nodes[actor]["type"],
            "first_release_year": debut, "last_release_year": max(releases),
            "years_since_last_observed_release": ds.cutoff - max(releases),
            "career_years_observed": ds.cutoff - debut + 1,
            "work_count": len(works), "song_count": counts["Song"], "album_count": counts["Album"],
            "performed_work_count": len(performed), "oceanus_performed_work_count": len(oceanus_performed),
            "oceanus_work_count": sum(w.get("genre") == "Oceanus Folk" for w in works),
            "genre_count": len(genre_counts), "genre_entropy": rounded(entropy),
            "genres": dict(sorted(genre_counts.items())), "roles": dict(sorted(role_counts.items())),
            "recent_5y_work_count": len(recent), "previous_5y_work_count": len(previous),
            "recent_work_share": rounded(len(recent) / len(works)),
            "productivity_change": len(recent) - len(previous),
            "collaborator_count": len(collaborators), "recent_5y_collaborator_count": len(recent_collaborators),
            "new_5y_collaborator_count": len(new_collaborators),
            "known_charted_work_count": len(known_charts), "first_known_chart_year": first_chart,
            "years_to_first_known_chart": first_chart - debut if first_chart is not None else None,
            "median_known_chart_lag": median(chart_lags) if chart_lags else None,
            "known_chart_lag_sample_size": len(chart_lags),
            "observed_notable_work_count": sum(w.get("notable") is True for w in works) if ds.cutoff == OBSERVATION_YEAR else None,
            "undated_notable_work_count": sum(w.get("notable") is True and w.get("chart_year") is None for w in works) if ds.cutoff == OBSERVATION_YEAR else None,
            "influence_credit": rounded(influence_credit[actor]),
            "recent_5y_influence_credit": rounded(recent_influence_credit[actor]),
            "influence_event_ids": sorted(influence_events_by_actor[actor]),
            "work_ids": sorted(credits), "performed_work_ids": sorted(w["id"] for w in performed),
        }
        feature_rows.append(row)
        cumulative_works, cumulative_charts, cumulative_collaborators = 0, 0, 0
        annual = []
        # Sparse event years avoid tens of MB of empty rows for one-credit artists.
        for year in sorted(set(releases) | set(charts) | set(first_collaborations)):
            cumulative_works += releases[year]
            cumulative_charts += charts[year]
            cumulative_collaborators += first_collaborations[year]
            annual.append({"year": year, "career_year": year - debut,
                           "releases": releases[year], "cumulative_works": cumulative_works,
                           "new_chart_entries_known_date": charts[year], "cumulative_known_charts": cumulative_charts,
                           "new_collaborators": first_collaborations[year],
                           "cumulative_collaborators": cumulative_collaborators})
        timelines.append({"id": actor, "year_range": [debut, ds.cutoff], "annual": annual,
                          "works": [{"id": w["id"], "year": w["release_year"], "genre": w["genre"],
                                     "roles": sorted(credits[w["id"]]),
                                     "chart_year_as_of": chart_year_as_of(w, ds.cutoff)} for w in works]})
    meta = {**ds.meta, "recent_window": [recent_start, ds.cutoff],
            "credit_scope": "direct PerformerOf / ComposerOf / ProducerOf / LyricistOf, one work counted once",
            "chart_scope": "explicit valid chart dates only; final observed status separately available only at 2040",
            "influence_scope": "fractional attribution to explicitly credited performers; self-influence excluded",
            "membership_scope": "undated MemberOf never expanded into work credits",
            "snapshot_limit": "release years proxy credit availability; source has no revision history",
            "timeline_storage": "sparse event years; zero-fill annual counts and forward-fill cumulative values within year_range",
            "prediction_target_period": [ds.cutoff + 1, ds.cutoff + 5]}
    return {"meta": meta, "artists": feature_rows}, {"meta": meta, "artists": timelines}


def candidate_baseline(features: dict, max_career_years: int = 10, active_within: int | None = None,
                       weights: dict | None = None) -> dict:
    """Transparent ranking for module-three experimentation, not a trained predictor."""
    cutoff = features["meta"]["cutoff_year"]
    if max_career_years < 1 or (active_within is not None and active_within < 1):
        raise ValueError("Candidate career/activity windows must be positive")
    pool = [r for r in features["artists"] if r["oceanus_performed_work_count"] > 0
            and r["career_years_observed"] <= max_career_years]
    candidates = [r for r in pool if active_within is None or r["last_release_year"] >= cutoff - active_within + 1]
    weights = dict(CANDIDATE_WEIGHTS if weights is None else weights)
    if (set(weights) != set(CANDIDATE_WEIGHTS) or any(not math.isfinite(v) or v < 0 for v in weights.values())
            or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12)):
        raise ValueError("Candidate weights must cover the five declared features, be finite/nonnegative and sum to 1")
    weights = {key: weights[key] for key in CANDIDATE_WEIGHTS}
    constant_features = [key for key in weights if len({r[key] for r in candidates}) <= 1]
    rows = []
    for r in candidates:
        contributions, score = {}, 0.0
        for feature, weight in weights.items():
            values = [other[feature] for other in candidates]
            less = sum(v < r[feature] for v in values)
            equal = sum(v == r[feature] for v in values)
            percentile = (less + (equal - 1) / 2) / (len(values) - 1) if len(values) > 1 else 0.5
            score += percentile * weight
            contributions[feature] = {"value": r[feature], "percentile": rounded(percentile),
                                      "weight": weight, "contribution": rounded(percentile * weight)}
        rows.append({"id": r["id"], "name": r["name"], "type": r["type"],
                     "last_release_year": r["last_release_year"],
                     "years_since_last_observed_release": r["years_since_last_observed_release"],
                     "score": rounded(score),
                     "contributions": contributions, "work_ids": r["work_ids"],
                     "influence_event_ids": r["influence_event_ids"]})
    rows.sort(key=lambda r: (-r["score"], r["id"]))
    previous_score, rank = None, 0
    for index, row in enumerate(rows, start=1):
        if row["score"] != previous_score:
            rank = index
        row["rank"] = rank
        previous_score = row["score"]
    return {"meta": {**features["meta"], "method": "weighted midrank percentile heuristic",
                     "status": "exploratory baseline, not validated prediction or probability",
                     "candidate_rule": "performed Oceanus Folk; bounded observed career; optional recent activity filter",
                     "max_career_years": max_career_years, "active_within": active_within,
                     "weights": weights, "tie_policy": "equal score = equal rank; id orders ties for display",
                     "constant_features": constant_features,
                     "constant_weight_mass": rounded(sum(weights[key] for key in constant_features)),
                     "caveat": "No calibrated success labels or 2041-2045 outcomes; no release record does not prove inactivity; module three owns final Top3 and validation"},
            "activity_filter_sensitivity": [{"active_within": window,
                                             "candidate_count": sum(window is None or r["last_release_year"] >= cutoff - window + 1 for r in pool)}
                                            for window in (None, 3, 5)],
            "candidate_count": len(rows), "candidates": rows}


def main():
    p = parser(__doc__)
    p.add_argument("--candidate-career-years", type=int, default=10)
    p.add_argument("--candidate-active-within", type=int, default=None)
    args = p.parse_args()
    ds = load_dataset(args.raw, args.cutoff, args.seed)
    features, timelines = artist_features(ds)
    write_json(args.out, "artist_features.json", features)
    write_json(args.out, "artist_timelines.json", timelines)
    baseline = candidate_baseline(features, args.candidate_career_years, args.candidate_active_within)
    write_json(args.out, "rising_star_baseline.json", baseline)
    print(f"{len(features['artists'])} artists; {baseline['candidate_count']} exploratory candidates -> {args.out}")


if __name__ == "__main__":
    main()
