"""Semantic tests: arrows, dates, attribution, role deduplication and export integrity."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.common import (DEFAULT_RAW, actor_influence_graph, collaboration_graph,
                             load_dataset, valid_year, write_json)
from pipeline.explore import explore
from pipeline.export_frontend import force_view
from pipeline.artist_features import artist_features, candidate_baseline, chart_year_as_of
from pipeline.genres import genre_analytics
from pipeline.metrics import influence_paths, sailor_profile


def fixture():
    nodes = [
        {"id": 1, "Node Type": "Person", "name": "Same Name"},
        {"id": 2, "Node Type": "Person", "name": "Same Name"},
        {"id": 3, "Node Type": "MusicalGroup", "name": "Group"},
        {"id": 4, "Node Type": "RecordLabel", "name": "Label"},
        {"id": 5, "Node Type": "Person", "name": "Isolated"},
    ]
    for i, year, genre, chart, notable in [
        (10, 2020, "Oceanus Folk", 2022, True),
        (11, 2025, "Indie Folk", None, True),
        (12, 2030, "Oceanus Folk", 2032, True),
        (13, 2022, "Oceanus Folk", 2021, True),
        (14, 2040, "Oceanus Folk", None, False),
        (15, 2023, "Oceanus Folk", 2023, False),
    ]:
        row = {"id": i, "Node Type": "Song", "name": f"Work {i}", "genre": genre,
               "release_date": str(year), "notable": notable, "single": True}
        if chart is not None:
            row["notoriety_date"] = str(chart)
        nodes.append(row)
    nodes[8]["written_date"] = "2023"  # Work 13, after its 2022 release.
    links = []
    def edge(s, t, relation, key=0):
        links.append({"source": s, "target": t, "key": key, "Edge Type": relation})
    edge(1, 10, "PerformerOf")
    edge(1, 10, "LyricistOf", 1)
    edge(2, 10, "ProducerOf")
    edge(3, 10, "PerformerOf")
    edge(2, 11, "PerformerOf")
    edge(1, 11, "LyricistOf")
    edge(2, 12, "PerformerOf")
    edge(3, 14, "PerformerOf")
    edge(1, 3, "MemberOf")
    edge(11, 10, "InStyleOf")
    edge(11, 10, "CoverOf", 1)
    edge(11, 10, "InStyleOf", 2)  # Semantic duplicate with a distinct raw key.
    edge(10, 11, "LyricalReferenceTo")  # Chronology anomaly.
    edge(10, 10, "CoverOf")  # Self reference.
    edge(2, 1, "InStyleOf")  # Undated actor relation.
    edge(4, 11, "RecordedBy")  # Official endpoint schema deviation; retain.
    edge(12, 11, "InStyleOf")
    return {"directed": True, "multigraph": True, "nodes": nodes, "links": links}


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "raw.json"
        self.payload = fixture()
        self.path.write_text(json.dumps(self.payload), encoding="utf-8")
        self.ds = load_dataset(self.path)

    def reload(self, payload, cutoff=2040):
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        return load_dataset(self.path, cutoff=cutoff)

    def test_identity_is_id_not_name_and_parallel_edges_survive(self):
        self.assertEqual(len(self.ds.nodes), 11)
        self.assertEqual(self.ds.graph.number_of_edges(1, 10), 2)
        self.assertEqual(self.ds.nodes[1]["name"], self.ds.nodes[2]["name"])
        self.assertIn(5, self.ds.nodes)

    def test_duplicate_node_id_fails(self):
        self.payload["nodes"].append(deepcopy(self.payload["nodes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate node id"):
            self.reload(self.payload)

    def test_missing_endpoint_fails(self):
        self.payload["links"][0]["target"] = 999
        with self.assertRaisesRegex(ValueError, "Dangling endpoint"):
            self.reload(self.payload)

    def test_key_collision_fails_instead_of_overwriting(self):
        self.payload["links"].append(deepcopy(self.payload["links"][0]))
        with self.assertRaisesRegex(ValueError, "overwrite evidence"):
            self.reload(self.payload)

    def test_year_parser_does_not_invent_missing_or_malformed_year(self):
        for value in (None, "", "unknown", "2020-03", True, 2020.5):
            self.assertIsNone(valid_year(value))
        self.assertEqual(valid_year(" 2040 "), 2040)
        self.assertNotIn("beyond_observation_release_year", self.ds.nodes[14]["quality_flags"])

    def test_raw_write_guard(self):
        with self.assertRaisesRegex(ValueError, "read-only"):
            write_json(DEFAULT_RAW.parent / "nested", "blocked.json", {})

    def test_diffusion_reverses_reference_and_uses_consumer_year(self):
        event = next(e for e in self.ds.influence_events() if e["id"] == "11:10:0")
        self.assertEqual((event["source"], event["target"], event["year"]), (10, 11, 2025))
        self.assertTrue(event["eligible_dated"])

    def test_suspect_edges_retained_but_excluded(self):
        events = {e["id"]: e for e in self.ds.influence_events()}
        for i in ("10:10:0", "10:11:0", "11:10:2"):
            self.assertIn(i, events)
            self.assertFalse(events[i]["eligible_dated"])
        self.assertTrue(events["11:10:1"]["eligible_dated"])

    def test_undated_actor_relation_is_not_assigned_a_year(self):
        event = next(e for e in self.ds.influence_events() if e["id"] == "2:1:0")
        self.assertTrue(event["eligible_structural"])
        self.assertFalse(event["eligible_dated"])
        self.assertIsNone(event["year"])

    def test_multiple_roles_do_not_inflate_collaboration(self):
        graph = collaboration_graph(self.ds)
        self.assertEqual(graph[1][2]["weight"], 2)
        self.assertEqual(graph[1][2]["work_ids"], [10, 11])
        self.assertNotIn(4, graph)

    def test_undated_membership_does_not_become_work_credit(self):
        _, credits = self.ds.credits()
        self.assertNotIn(14, credits[1])
        self.assertIn(14, credits[3])

    def test_fractional_influence_excludes_self_and_preserves_evidence(self):
        graph = actor_influence_graph(self.ds)
        # Two distinct relations, two origin performers, one consumer performer.
        self.assertEqual(graph[1][2]["weight"], 1.0)
        self.assertEqual(graph[3][2]["weight"], 1.0)
        self.assertFalse(graph.has_edge(2, 2))
        self.assertEqual(graph[1][2]["event_ids"], ["11:10:0", "11:10:1"])

    def test_missing_or_conflicting_chart_dates_are_not_zero_lags(self):
        self.assertIsNone(chart_year_as_of(self.ds.nodes[11], 2040))
        self.assertIsNone(chart_year_as_of(self.ds.nodes[13], 2040))
        self.assertIsNone(chart_year_as_of(self.ds.nodes[15], 2040))
        self.assertIsNone(chart_year_as_of(self.ds.nodes[12], 2031))
        self.assertEqual(chart_year_as_of(self.ds.nodes[10], 2040), 2022)

    def test_historical_snapshot_excludes_future_releases_charts_and_labels(self):
        features, _ = artist_features(replace(self.ds, cutoff=2025))
        rows = {r["id"]: r for r in features["artists"]}
        self.assertNotIn(12, rows[2]["work_ids"])
        self.assertEqual(rows[2]["known_charted_work_count"], 1)
        self.assertEqual(rows[2]["median_known_chart_lag"], 2)
        self.assertIsNone(rows[2]["observed_notable_work_count"])
        self.assertIsNone(rows[2]["undated_notable_work_count"])
        self.assertNotIn("12:11:0", rows[2]["influence_event_ids"])

    def test_removing_future_evidence_does_not_change_past_features(self):
        before, _ = artist_features(replace(self.ds, cutoff=2025))
        future_ids = {12, 14}
        self.payload["nodes"] = [n for n in self.payload["nodes"] if n["id"] not in future_ids]
        self.payload["links"] = [e for e in self.payload["links"] if e["source"] not in future_ids and e["target"] not in future_ids]
        # A later-discovered chart event cannot modify the 2025 feature vector.
        next(n for n in self.payload["nodes"] if n["id"] == 11)["notoriety_date"] = "2039"
        after, _ = artist_features(self.reload(self.payload, cutoff=2025))
        self.assertEqual(before["artists"], after["artists"])

    def test_genre_flow_direction_count_and_denominator(self):
        trends, flows = genre_analytics(replace(self.ds, cutoff=2025))
        self.assertEqual(sum(r["value"] for r in flows["flows"]), 2)
        self.assertTrue(all(r["source"] == "Oceanus Folk" and r["target"] == "Indie Folk" for r in flows["flows"]))
        row = next(r for r in trends["rows"] if r["year"] == 2025 and r["genre"] == "Oceanus Folk")
        self.assertEqual(row["outbound_events"], 2)
        self.assertEqual(row["external_influenced_work_count"], 1)
        self.assertEqual(row["external_work_coverage"], 1)

    def test_zero_years_are_present_and_zero_denominator_is_null(self):
        trends, _ = genre_analytics(replace(self.ds, cutoff=2025))
        row = next(r for r in trends["rows"] if r["year"] == 2021 and r["genre"] == "Oceanus Folk")
        self.assertEqual(row["work_count"], 0)
        self.assertIsNone(row["outbound_share"])

    def test_influence_path_has_verifiable_edge_ids(self):
        events = [e for e in self.ds.influence_events() if e["eligible_dated"]]
        paths = {r["id"]: r for r in influence_paths(events, {10})}
        self.assertEqual(paths[12]["node_path"], [10, 11, 12])
        self.assertEqual(paths[12]["event_ids"], ["11:10:0", "12:11:0"])

    def test_layout_is_deterministic_complete_and_finite(self):
        first = force_view(self.ds, list(self.ds.nodes), "test")
        second = force_view(self.ds, list(self.ds.nodes), "test")
        self.assertEqual(first, second)
        self.assertEqual(len(first["nodes"]), len(self.ds.nodes))
        json.dumps(first, allow_nan=False)

    def test_candidate_ties_and_constant_features_are_explicit(self):
        row = {"id": 1, "name": "A", "type": "Person", "oceanus_performed_work_count": 1,
               "career_years_observed": 5, "last_release_year": 2035, "years_since_last_observed_release": 5,
               "recent_5y_work_count": 1, "new_5y_collaborator_count": 0, "recent_5y_influence_credit": 0,
               "genre_count": 1, "recent_work_share": 1, "work_ids": [10], "influence_event_ids": []}
        features = {"meta": {"cutoff_year": 2040}, "artists": [row, {**row, "id": 2}]}
        baseline = candidate_baseline(features)
        self.assertEqual([r["rank"] for r in baseline["candidates"]], [1, 1])
        self.assertEqual([r["score"] for r in baseline["candidates"]], [0.5, 0.5])
        self.assertEqual(len(baseline["meta"]["constant_features"]), 5)
        self.assertEqual(candidate_baseline(features, active_within=3)["candidate_count"], 0)


@unittest.skipUnless(DEFAULT_RAW.exists(), "Official dataset not available")
class OfficialDataRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = load_dataset()

    def test_actual_counts_and_source_fingerprint(self):
        report = explore(self.ds)
        self.assertEqual(self.ds.source_sha256, "21d0af1923c48e6f6a2d442940f85f717d97675c59776401ed2b7df56916fac9")
        self.assertEqual((len(self.ds.nodes), len(self.ds.links), report["counts"]["weak_components"]), (17412, 37857, 16))
        self.assertEqual(report["issue_counts"]["notable_without_chart_year"], 3648)
        self.assertEqual(report["issue_counts"]["influence_chronology"], 84)
        self.assertEqual(report["issue_counts"]["schema_endpoint_deviation"], 550)

    def test_sailor_context_and_credits(self):
        profile = sailor_profile(self.ds, collaboration_graph(self.ds))
        self.assertEqual(self.ds.nodes[17255]["name"], "Sailor Shift")
        self.assertEqual(self.ds.graph.degree(17255), 60)
        self.assertEqual((len(profile["works"]), len(profile["collaborators"])), (38, 48))
        self.assertEqual((len(profile["ego"]["nodes"]), len(profile["ego"]["links"])), (269, 546))

    def test_all_influence_exclusions_are_accounted_for(self):
        events = self.ds.influence_events()
        self.assertEqual(len(events), 7407)
        self.assertEqual(sum(e["eligible_dated"] for e in events), 7255)
        self.assertEqual(sum(e["year"] is None for e in events), 67)


if __name__ == "__main__":
    unittest.main()
