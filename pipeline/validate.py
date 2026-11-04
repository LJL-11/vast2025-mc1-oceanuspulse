"""Validate a complete bundle, including provenance and independently checkable invariants."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import math
from pathlib import Path

from pipeline.common import DEFAULT_OUT, DEFAULT_RAW, OBSERVATION_YEAR, parser, sha256


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def strict_json(path: Path):
    def reject(value):
        raise ValueError(f"Non-finite JSON value {value} in {path}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def validate_bundle(out: Path = DEFAULT_OUT, raw: Path = DEFAULT_RAW) -> dict:
    out, raw = out.resolve(), raw.resolve()
    manifest = strict_json(out / "manifest.json")
    require(sha256(raw) == manifest["meta"]["source_sha256"], "Input hash differs from generated bundle")
    for name, digest in manifest["raw_files_sha256"].items():
        require(Path(name).name == name, "Invalid raw file name in manifest")
        require(sha256(raw.parent / name) == digest, f"Raw file changed: {name}")
    inventory = manifest["files"]
    require(len({r['path'] for r in inventory}) == len(inventory), "Duplicate manifest path")
    files = {}
    for entry in inventory:
        path = (out / entry["path"]).resolve()
        require(out in path.parents, "Manifest path escapes output directory")
        require(path.stat().st_size == entry["bytes"], f"Size mismatch: {entry['path']}")
        require(sha256(path) == entry["sha256"], f"Hash mismatch: {entry['path']}")
        data = strict_json(path)
        for field in ("source_sha256", "schema_version", "seed", "cutoff_year"):
            require(data["meta"][field] == manifest["meta"][field], f"Mixed bundle metadata: {entry['path']}/{field}")
        files[entry["path"]] = data
    mandatory = {"clean_graph.json", "quality_report.json", "node_metrics.json", "sailor_shift.json",
                 "influence_events.json", "genre_trends.json", "genre_flows.json", "artist_features.json",
                 "artist_timelines.json", "rising_star_baseline.json", "artist_networks.json",
                 "network_overview.json", "sailor_ego.json", "node_index.json", "artist_index.json", "overview.json",
                 "influence_evidence.json", "network_dynamics.json", "robustness_report.json"}
    require(mandatory <= files.keys(), "Bundle is missing required artifacts")
    original = strict_json(raw)
    original_nodes = {r["id"]: r for r in original["nodes"]}
    clean = files["clean_graph.json"]
    require(clean["directed"] is True and clean["multigraph"] is True, "Graph semantics lost")
    require(clean["graph"] == original.get("graph", {}), "Graph metadata lost")
    nodes = {r["id"]: r for r in clean["nodes"]}
    links = {r["id"]: r for r in clean["links"]}
    require(len(nodes) == len(clean["nodes"]) == len(original["nodes"]), "Node loss or duplicate IDs")
    require(len(links) == len(clean["links"]) == len(original["links"]), "Edge loss or duplicate IDs")
    for i, node in nodes.items():
        require(node["raw_attributes"] == {k: v for k, v in original_nodes[i].items() if k != "id"}, f"Original node attributes lost: {i}")
    for e in original["links"]:
        edge = links[f"{e['source']}:{e['target']}:{e['key']}"]
        require((edge["source"], edge["target"], edge["type"], edge["key"]) ==
                (e["source"], e["target"], e["Edge Type"], e["key"]), "Original edge altered")
    counts = files["quality_report.json"]["counts"]
    require(counts["nodes"] == len(nodes) and counts["links"] == len(links), "Audit counts mismatch")
    require(sum(c["size"] for c in files["quality_report.json"]["components"]) == len(nodes), "Components lose nodes")
    require({r["id"] for r in files["node_metrics.json"]["nodes"]} == nodes.keys(), "Metric node IDs mismatch")
    require({r["id"] for r in files["node_index.json"]["nodes"]} == nodes.keys(), "Index node IDs mismatch")

    events = {e["id"]: e for e in files["influence_events.json"]["events"]}
    cutoff = manifest["meta"]["cutoff_year"]
    for e in events.values():
        original_edge = links[e["id"]]
        require((e["source"], e["target"]) == (original_edge["target"], original_edge["source"]), "Influence arrow reversed incorrectly")
        if e["eligible_dated"]:
            require(e["year"] is not None and e["year"] <= cutoff, "Future or undated event enters dated analysis")
            require(e["source"] != e["target"], "Self loop enters influence statistics")
            require(not set(e["quality_flags"]) & {"duplicate_relation", "influence_chronology"}, "Flagged event enters dated analysis")
    used_events = []
    for flow in files["genre_flows.json"]["flows"]:
        require(flow["value"] == len(flow["event_ids"]), "Flow count lacks evidence")
        for event_id in flow["event_ids"]:
            event = events[event_id]
            require(event["eligible_dated"], "Excluded event enters genre flow")
            require((flow["source"], flow["target"], flow["year"], flow["type"]) ==
                    (event["source_genre"], event["target_genre"], event["year"], event["type"]), "Genre attribution mismatch")
            used_events.append(event_id)
    expected_events = {e["id"] for e in events.values() if e["eligible_dated"] and e["source_genre"] and e["target_genre"]}
    require(set(used_events) == expected_events and len(used_events) == len(expected_events), "Genre evidence duplicated or lost")
    trend_rows = files["genre_trends.json"]["rows"]
    require(sum(r["outbound_events"] for r in trend_rows) == sum(r["inbound_events"] for r in trend_rows), "Genre in/out totals differ")
    require(sum(r["internal_events"] + r["outbound_events"] for r in trend_rows) == len(expected_events), "Trends and flows differ")
    require(sum(r["work_count"] for r in trend_rows) == sum(n.get("release_year") is not None and n["release_year"] <= cutoff for n in nodes.values()), "Release counts differ")

    for name in ("network_overview.json", "sailor_ego.json"):
        view = files[name]
        ids = {r["id"] for r in view["nodes"]}
        require(len(ids) == len(view["nodes"]), "Duplicate layout node")
        for n in view["nodes"]:
            require(n["id"] in nodes and all(math.isfinite(n[axis]) for axis in ("x", "y")), "Invalid layout node/coordinate")
        for e in view["links"]:
            require(e["source"] in ids and e["target"] in ids, "Dangling view edge")
    require(len(files["network_overview.json"]["nodes"]) <= manifest["parameters"]["max_nodes"], "Overview exceeds node budget")
    require({r["id"] for r in files["sailor_ego.json"]["nodes"]} ==
            {r["id"] for r in files["sailor_shift.json"]["ego"]["nodes"]}, "Ego layout silently truncated")

    networks = files["artist_networks.json"]
    for e in networks["collaboration_links"]:
        require(e["source"] != e["target"], "Collaboration self-loop")
        require(e["weight"] == len(e["work_ids"]) == len(set(e["work_ids"])), "Multiple roles inflated shared work count")
        require(all(nodes[w]["release_year"] <= cutoff for w in e["work_ids"]), "Future collaboration")
    for e in networks["influence_links"]:
        require(e["weight"] > 0 and e["source"] != e["target"], "Invalid artist influence edge")
        require(all(events[i]["eligible_dated"] for i in e["event_ids"]), "Artist influence uses excluded event")

    features = files["artist_features.json"]["artists"]
    artist_ids = {r["id"] for r in features}
    require(len(artist_ids) == len(features), "Duplicate artist feature row")
    for row in features:
        require(row["work_count"] == len(row["work_ids"]) == len(set(row["work_ids"])), "Artist works duplicated")
        require(row["last_release_year"] <= cutoff, "Future release leaked into features")
        require(row["first_known_chart_year"] is None or row["first_known_chart_year"] <= cutoff, "Future chart leaked into features")
        require(row["median_known_chart_lag"] is None or row["median_known_chart_lag"] >= 0, "Negative chart lag")
        if cutoff < OBSERVATION_YEAR:
            require(row["observed_notable_work_count"] is None and row["undated_notable_work_count"] is None, "Final status leaked into history")
    timeline_rows = {r["id"]: r for r in files["artist_timelines.json"]["artists"]}
    require(timeline_rows.keys() == artist_ids, "Missing career timelines")
    shard_count = files["artist_index.json"]["meta"]["shard_count"]
    sharded_ids = []
    for shard in range(shard_count):
        rows = files[f"artists/{shard:02d}.json"]["artists"]
        for i, row in rows.items():
            require(int(i) % shard_count == shard, "Incorrect shard assignment")
            require(row["timeline"] == timeline_rows[int(i)], "Shard timeline differs from canonical output")
            sharded_ids.append(int(i))
    require(set(sharded_ids) == artist_ids and len(sharded_ids) == len(artist_ids), "Artist shard coverage mismatch")
    for row in features:
        annual = timeline_rows[row["id"]]["annual"]
        require(sum(r["releases"] for r in annual) == row["work_count"], "Career release total mismatch")
        require(sum(r["new_chart_entries_known_date"] for r in annual) == row["known_charted_work_count"], "Career chart total mismatch")
        require(annual[-1]["cumulative_collaborators"] == row["collaborator_count"], "Career collaboration total mismatch")
    feature_map = {r["id"]: r for r in features}
    baseline = files["rising_star_baseline.json"]
    for candidate in baseline["candidates"]:
        row = feature_map[candidate["id"]]
        active = baseline["meta"]["active_within"]
        require(row["oceanus_performed_work_count"] > 0
                and row["career_years_observed"] <= baseline["meta"]["max_career_years"]
                and (active is None or row["last_release_year"] >= cutoff - active + 1), "Ineligible candidate")
        require(0 <= candidate["score"] <= 1, "Baseline score out of bounds")
        require(math.isclose(candidate["score"], sum(c["contribution"] for c in candidate["contributions"].values()), abs_tol=1e-9), "Unexplained score")
    from pipeline.validate_analytics import validate_analytics
    validate_analytics(files, nodes, links, events, feature_map)
    return {"valid": True, "file_count": len(inventory) + 1, "node_count": len(nodes),
            "edge_count": len(links), "dated_genre_events": len(expected_events)}


def main():
    args = parser(__doc__).parse_args()
    print(validate_bundle(args.out, args.raw))


if __name__ == "__main__":
    main()
