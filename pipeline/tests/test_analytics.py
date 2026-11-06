"""Ground-truth miniature graphs for attribution, historical networks and sensitivity."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.common import DEFAULT_RAW, INFLUENCE_TYPES, load_dataset
from pipeline.artist_features import artist_features, candidate_baseline
from pipeline.influence import build_evidence, dated_events, influence_scores
from pipeline.rankings import compare_rankings, rank_details, top_set
from pipeline.robustness import candidate_weight_scenarios, robustness_report, rule_scenarios
from pipeline.temporal import genre_windows, network_dynamics, select_cohort
from pipeline.tests.test_pipeline import fixture


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "fixture.json"
        self.payload = fixture()
        self.ds = self.load(self.payload)

    def load(self, payload, cutoff=2040):
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        return load_dataset(self.path, cutoff=cutoff)

    def evidence(self, ds=None, attribution="performers"):
        return build_evidence(ds or self.ds, focus_id=1, attribution=attribution)

    def test_work_attribution_path_is_three_real_edges_with_correct_directions(self):
        result = self.evidence()
        peer = next(r for r in result["focus"]["outgoing"] if r["id"] == 2)
        path = next(p for p in peer["example_paths"] if p["event_id"] == "11:10:0")
        self.assertEqual(path["node_path"], [1, 10, 11, 2])
        self.assertEqual([p["edge_id"] for p in path["steps"]], ["1:10:0", "11:10:0", "2:11:0"])
        self.assertEqual([p["traversal"] for p in path["steps"]], ["forward", "reverse", "reverse"])
        self.assertEqual(path["evidence_kind"], "work_attribution")

    def test_direct_undated_evidence_stays_separate_from_derived_dated_evidence(self):
        peer = next(r for r in self.evidence()["focus"]["outgoing"] if r["id"] == 2)
        self.assertEqual((peer["explicit_reference_count"], peer["attributed_reference_count"]), (1, 2))
        self.assertEqual((peer["dated_count"], peer["undated_count"]), (2, 1))
        self.assertEqual(peer["fractional_attributed_weight"], 1.0)
        direct = next(p for p in peer["example_paths"] if p["event_id"] == "2:1:0")
        self.assertEqual(direct["node_path"], [1, 2])
        self.assertIsNone(direct["year"])

    def test_historical_evidence_does_not_assign_undated_actor_relations(self):
        result = self.evidence(replace(self.ds, cutoff=2025))
        peer = next(r for r in result["focus"]["outgoing"] if r["id"] == 2)
        self.assertEqual(peer["explicit_reference_count"], 0)
        self.assertNotIn("2:1:0", peer["event_ids"])

    def test_multiple_credit_roles_change_scope_but_not_artist_pair_count(self):
        payload = deepcopy(self.payload)
        payload["links"].append({"source": 1, "target": 10, "key": 2, "Edge Type": "ComposerOf"})
        ds = self.load(payload)
        result = self.evidence(ds, "creative_credits")
        event = next(e for e in result["events"] if e["id"] == "11:10:1")
        self.assertEqual(len(event["source_credits"]), 3)
        credit = next(c for c in event["source_credits"] if c["artist_id"] == 1)
        self.assertEqual(credit["roles"], ["ComposerOf", "LyricistOf", "PerformerOf"])
        weights = {key: float(key == "CoverOf") for key in INFLUENCE_TYPES}
        scores = influence_scores(result, weights)
        self.assertAlmostEqual(sum(scores["artists"].values()), 2 / 3, places=9)
        self.assertAlmostEqual(scores["removed_self_mass"], 1 / 3, places=9)

    def test_reference_types_can_be_counted_separately(self):
        weights = {key: float(key == "CoverOf") for key in INFLUENCE_TYPES}
        scores = influence_scores(self.evidence(), weights)
        self.assertEqual(scores["event_count"], 1)
        self.assertEqual(scores["artists"], {1: 0.5, 3: 0.5})
        self.assertEqual(scores["genres"], {"Oceanus Folk": 1.0})

    def test_chronology_sensitivity_cannot_use_future_source_work(self):
        snapshot = replace(self.ds, cutoff=2023)
        events = list(dated_events(self.evidence(snapshot), include_chronology=True))
        self.assertNotIn("10:11:0", [e["id"] for e in events])
        full = list(dated_events(self.evidence(), include_chronology=True))
        self.assertIn("10:11:0", [e["id"] for e in full])
        self.assertNotIn("10:10:0", [e["id"] for e in full])
        self.assertNotIn("11:10:2", [e["id"] for e in full])

    def test_equal_type_mass_normalizes_relation_totals_without_changing_total_mass(self):
        evidence = self.evidence()
        scenario = next(s for s in rule_scenarios(evidence) if s["id"] == "equal_type_mass")
        scores = influence_scores(evidence, scenario["weights"])
        self.assertEqual(scores["event_count"], 3)
        self.assertEqual(scores["weighted_event_mass"], 3.0)
        self.assertEqual(scores["relation_mass"], {"CoverOf": 1.5, "InStyleOf": 1.5})

    def test_yearly_metrics_count_only_past_work_and_chart_events(self):
        ds = replace(self.ds, cutoff=2025)
        cohort = {"ids": [1, 2, 3]}
        result = network_dynamics(ds, self.evidence(ds), cohort)
        row = next(s for s in result["artists"] if s["id"] == 2)["rows"][0]
        self.assertEqual(row["year"], 2020)
        self.assertEqual(row["cumulative"]["work_count"], 1)
        self.assertEqual(row["cumulative"]["known_charted_work_count"], 0)
        self.assertEqual(row["cumulative"]["dated_influence_credit"], 0)
        self.assertIsNone(row["cumulative"]["influence_source_pagerank_percentile"])

    def test_rolling_influence_keeps_older_inspiration_work(self):
        ds = replace(self.ds, cutoff=2025)
        result = network_dynamics(ds, self.evidence(ds), {"ids": [1]}, window=5)
        row = result["artists"][0]["rows"][-1]
        self.assertEqual(row["rolling"]["start_year"], 2021)
        self.assertEqual(row["rolling"]["work_count"], 1)
        self.assertEqual(row["rolling"]["dated_influence_credit"], 1.0)
        self.assertEqual(row["annual"]["new_dated_influence_credit"], 1.0)

    def test_repeat_collaborator_is_active_but_not_new(self):
        ds = replace(self.ds, cutoff=2025)
        result = network_dynamics(ds, self.evidence(ds), {"ids": [1]}, window=5)
        row = result["artists"][0]["rows"][-1]
        self.assertEqual(row["rolling"]["collaborator_count"], 1)
        self.assertEqual(row["rolling"]["new_collaborator_count"], 0)
        self.assertEqual(row["annual"]["new_collaborator_count"], 0)

    def test_removing_future_records_does_not_change_network_history(self):
        ds = replace(self.ds, cutoff=2025)
        cohort = {"ids": [1, 2, 3]}
        before = network_dynamics(ds, self.evidence(ds), cohort)
        payload = deepcopy(self.payload)
        future = {12, 14}
        payload["nodes"] = [n for n in payload["nodes"] if n["id"] not in future]
        payload["links"] = [e for e in payload["links"] if e["source"] not in future and e["target"] not in future]
        next(n for n in payload["nodes"] if n["id"] == 11)["notoriety_date"] = "2039"
        after_ds = self.load(payload, cutoff=2025)
        after = network_dynamics(after_ds, self.evidence(after_ds), cohort)
        for key in ("artists", "network_sizes", "genre_windows"):
            self.assertEqual(before[key], after[key])

    def test_genre_windows_deduplicate_target_works_and_flag_partial_comparisons(self):
        rows = genre_windows(replace(self.ds, cutoff=2025), self.evidence(replace(self.ds, cutoff=2025)))
        row = next(r for r in rows if r["year"] == 2025 and r["genre"] == "Oceanus Folk")
        self.assertEqual(row["outbound_events"], 2)
        self.assertEqual(row["external_influenced_work_count"], 1)
        self.assertEqual(row["external_target_genre_count"], 1)
        self.assertIsNone(row["outbound_change_vs_previous_window"])
        self.assertEqual(row["previous_observed_years"], 1)

    def test_cohort_selection_rejects_non_artist_ids(self):
        features, _ = artist_features(self.ds)
        baseline = candidate_baseline(features)
        with self.assertRaisesRegex(ValueError, "Person/MusicalGroup"):
            select_cohort(self.ds, baseline, 1, [10])

    def test_invalid_rolling_window_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            genre_windows(self.ds, self.evidence(), window=0)

    def test_ties_at_top_k_boundary_are_not_broken_by_id(self):
        scores = {1: 3, 2: 2, 3: 1, 4: 1}
        top = top_set(scores, 3)
        self.assertEqual(top["ids"], [1, 2, 3, 4])
        self.assertFalse(top["unique_top_k_set"])
        self.assertEqual(top["boundary_tie_size"], 2)
        comparison = compare_rankings(scores, scores, 3)
        self.assertEqual(comparison["top_set_jaccard"], 1)
        self.assertFalse(comparison["scenario_top"]["unique_top_k_set"])

    def test_empty_evidence_has_no_fake_perfect_stability(self):
        result = compare_rankings({1: 0, 2: 0}, {1: 0, 2: 0})
        self.assertIsNone(result["spearman"])
        self.assertIsNone(result["top_set_jaccard"])
        self.assertEqual(result["comparison_count"], 0)

    def test_spearman_handles_reverse_ranking_and_ties(self):
        reverse = compare_rankings({1: 3, 2: 2, 3: 1}, {1: 1, 2: 2, 3: 3}, 1)
        self.assertEqual(reverse["spearman"], -1)
        self.assertEqual(reverse["top_set_jaccard"], 0)
        ranks = rank_details({1: 1, 2: 1, 3: 0})
        self.assertEqual(ranks[1]["percentile"], 0.75)
        self.assertEqual(ranks[2]["rank"], 1)

    def test_weight_experiments_keep_candidate_cohort_and_expose_constant_mass(self):
        features, _ = artist_features(replace(self.ds, cutoff=2025))
        baseline = candidate_baseline(features)
        rows = candidate_weight_scenarios(features, baseline)
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertEqual({r["id"] for r in row["candidates"]}, {r["id"] for r in baseline["candidates"]})
            self.assertAlmostEqual(sum(row["weights"].values()), 1)
        informative = next(r for r in rows if r["id"] == "informative_features_only")
        if not informative["no_informative_features"]:
            self.assertEqual(informative["constant_weight_mass"], 0)

    def test_invalid_candidate_weights_are_rejected(self):
        features, _ = artist_features(self.ds)
        for weights in ({"genre_count": 1}, {"recent_5y_work_count": float('nan')}):
            with self.assertRaisesRegex(ValueError, "weights"):
                candidate_baseline(features, weights=weights)

    def test_weight_dictionary_order_does_not_change_results(self):
        features, _ = artist_features(self.ds)
        original = candidate_baseline(features)
        reversed_weights = dict(reversed(list(original["meta"]["weights"].items())))
        self.assertEqual(original, candidate_baseline(features, weights=reversed_weights))

    def test_robustness_reports_all_predeclared_scenarios(self):
        features, _ = artist_features(self.ds)
        baseline = candidate_baseline(features)
        result = robustness_report(self.ds, self.evidence(), features, baseline, focus_id=1)
        self.assertEqual(len(result["influence_scenarios"]), 7)
        conservative = result["influence_scenarios"][0]
        including = next(r for r in result["influence_scenarios"] if r["id"] == "include_chronology")
        self.assertEqual(including["event_count"] - conservative["event_count"], 1)
        self.assertEqual(result["diagnostics"]["undated_explicit_reference_count"], 1)


@unittest.skipUnless(DEFAULT_RAW.exists(), "Official dataset not available")
class RealEvidenceTests(unittest.TestCase):
    def test_official_evidence_preserves_sparse_direct_reference_dates(self):
        ds = load_dataset()
        evidence = build_evidence(ds)
        self.assertEqual(evidence["summary"]["evidence_kinds"], {"explicit_artist_reference": 67, "work_attribution": 7340})
        self.assertEqual((len(evidence["focus"]["incoming"]), len(evidence["focus"]["outgoing"])), (58, 7))
        self.assertTrue(all(row["dated_count"] == 0 for row in evidence["focus"]["outgoing"]))


if __name__ == "__main__":
    unittest.main()
