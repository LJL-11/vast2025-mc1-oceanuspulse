"""Tie-aware descriptive rankings; do not turn absent evidence into perfect stability."""
from __future__ import annotations

from itertools import groupby
from scipy.stats import spearmanr

from pipeline.common import rounded


def rank_details(scores: dict) -> dict:
    values = {key: rounded(value) for key, value in scores.items()}
    ordered = sorted(values, key=lambda key: (-values[key], key))
    result, offset, count = {}, 0, len(ordered)
    for score, group in groupby(ordered, key=values.get):
        ids = list(group)
        below = count - offset - len(ids)
        percentile = (below + (len(ids) - 1) / 2) / (count - 1) if count > 1 else 0.5
        for key in ids:
            result[key] = {"score": score, "rank": offset + 1, "tie_size": len(ids),
                           "percentile": rounded(percentile)}
        offset += len(ids)
    return result


def top_set(scores: dict, k: int, positive_only: bool = True) -> dict:
    if k < 1:
        raise ValueError("k must be positive")
    eligible = {i: rounded(v) for i, v in scores.items() if not positive_only or rounded(v) > 0}
    ranks = rank_details(eligible)
    selected = [i for i, row in ranks.items() if row["rank"] <= k]
    boundary = ranks[selected[-1]] if selected else None
    return {"requested_k": k, "eligible_count": len(eligible), "ids": selected,
            "selected_count": len(selected), "unique_top_k_set": len(selected) == k,
            "boundary_tie_size": boundary["tie_size"] if boundary else 0,
            "fewer_than_k_eligible": len(eligible) < k,
            "rows": [{"id": i, **ranks[i]} for i in selected]}


def compare_rankings(baseline: dict, scenario: dict, k: int = 5, positive_only: bool = True) -> dict:
    all_ids = sorted(set(baseline) | set(scenario))
    ids = [i for i in all_ids if not positive_only or rounded(baseline.get(i, 0)) > 0 or rounded(scenario.get(i, 0)) > 0]
    a = {i: rounded(baseline.get(i, 0)) for i in ids}
    b = {i: rounded(scenario.get(i, 0)) for i in ids}
    constant = len(set(a.values())) < 2 or len(set(b.values())) < 2
    rho = None if len(ids) < 2 or constant else rounded(spearmanr(list(a.values()), list(b.values())).statistic)
    top_a, top_b = top_set(baseline, k, positive_only), top_set(scenario, k, positive_only)
    set_a, set_b = set(top_a["ids"]), set(top_b["ids"])
    rank_a, rank_b = rank_details(a), rank_details(b)
    shifts = [{"id": i, "baseline_rank": rank_a[i]["rank"], "scenario_rank": rank_b[i]["rank"],
               "rank_change": rank_a[i]["rank"] - rank_b[i]["rank"]} for i in ids]
    shifts.sort(key=lambda r: (-abs(r["rank_change"]), r["id"]))
    return {"comparison_count": len(ids), "excluded_common_zero_count": len(all_ids) - len(ids),
            "spearman": rho, "spearman_unavailable_reason":
            ("fewer_than_two_entities" if len(ids) < 2 else "constant_scores" if constant else None),
            "top_set_jaccard": rounded(len(set_a & set_b) / len(set_a | set_b)) if set_a | set_b else None,
            "baseline_top": top_a, "scenario_top": top_b,
            "entered_top": sorted(set_b - set_a), "left_top": sorted(set_a - set_b),
            "largest_rank_changes": shifts[:10]}
