"""One command: audit -> graphs -> metrics -> features -> frontend bundles -> validate."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathlib import Path
import platform
import time

import networkx as nx
import numpy as np
import scipy

from pipeline.build_graph import build
from pipeline.common import load_dataset, parser, sha256, write_json
from pipeline.explore import explore
from pipeline.export_frontend import export_views
from pipeline.artist_features import artist_features, candidate_baseline
from pipeline.genres import genre_analytics
from pipeline.metrics import compute_metrics, sailor_profile
from pipeline.influence import build_evidence
from pipeline.robustness import robustness_report
from pipeline.temporal import network_dynamics, select_cohort


def run_pipeline(args) -> dict:
    start = time.perf_counter()
    raw, out = Path(args.raw).resolve(), Path(args.out).resolve()
    if out == raw.parent or raw.parent in out.parents:
        raise ValueError("Output must not be inside the input/raw directory")
    raw_hashes = {p.name: sha256(p) for p in sorted(raw.parent.iterdir()) if p.is_file()}
    print("[1/6] Loading and auditing original evidence...", flush=True)
    ds = load_dataset(raw, args.cutoff, args.seed)
    quality = explore(ds)
    print("[2/6] Computing collaboration and influence metrics...", flush=True)
    metrics, collab, influence = compute_metrics(ds, args.samples)
    sailor = sailor_profile(ds, collab, args.focus_id)
    print("[3/6] Aggregating genre evidence and as-of artist features...", flush=True)
    trends, flows = genre_analytics(ds)
    features, timelines = artist_features(ds)
    baseline = candidate_baseline(features, args.candidate_career_years, args.candidate_active_within)
    print("[3/6] Building attribution evidence, yearly networks and rule sensitivity...", flush=True)
    evidence = build_evidence(ds, args.focus_id)
    cohort = select_cohort(ds, baseline, args.focus_id, args.compare_ids)
    dynamics = network_dynamics(ds, evidence, cohort, args.window_years)
    robustness = robustness_report(ds, evidence, features, baseline, args.focus_id)
    outputs = {"clean_graph.json": build(ds), "quality_report.json": quality,
               "node_metrics.json": metrics, "sailor_shift.json": sailor,
               "influence_events.json": {"meta": {**ds.meta, "direction": "inspiration -> influenced"},
                                         "events": ds.influence_events()},
               "genre_trends.json": trends, "genre_flows.json": flows,
               "artist_features.json": features, "artist_timelines.json": timelines,
               "rising_star_baseline.json": baseline,
               "influence_evidence.json": evidence, "network_dynamics.json": dynamics,
               "robustness_report.json": robustness,
               "artist_networks.json": {"meta": {**ds.meta,
                                                   "collaboration_direction": "undirected; one shared work = weight 1",
                                                   "influence_direction": "inspiration performer -> influenced performer"},
                                         "collaboration_nodes": sorted(collab),
                                         "collaboration_links": [{"source": a, "target": b, **d} for a, b, d in sorted(collab.edges(data=True))],
                                         "influence_nodes": sorted(influence),
                                         "influence_links": [{"source": a, "target": b, **d} for a, b, d in sorted(influence.edges(data=True))]}}
    print("[4/6] Precomputing bounded force layouts and artist shards...", flush=True)
    outputs.update(export_views(ds, quality, metrics, sailor, features, timelines, baseline, args.max_nodes))
    print("[5/6] Writing strict JSON and content-hash manifest...", flush=True)
    inventory = []
    for name, data in sorted(outputs.items()):
        # Nested shards are still exclusively inside data/processed/ by default.
        path = write_json(out / Path(name).parent, Path(name).name, data)
        inventory.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    after_hashes = {p.name: sha256(p) for p in sorted(raw.parent.iterdir()) if p.is_file()}
    if after_hashes != raw_hashes:
        raise RuntimeError("Input directory changed during the run; no new manifest published")
    manifest = {"meta": ds.meta, "raw_files_sha256": raw_hashes,
                "parameters": {"samples": args.samples, "focus_id": args.focus_id, "max_nodes": args.max_nodes,
                               "candidate_career_years": args.candidate_career_years,
                               "candidate_active_within": args.candidate_active_within,
                               "window_years": args.window_years, "compare_ids": sorted(set(args.compare_ids))},
                "runtime": {"python": platform.python_version(), "networkx": nx.__version__,
                            "numpy": np.__version__, "scipy": scipy.__version__},
                "files": inventory}
    write_json(out, "manifest.json", manifest)
    print("[6/6] Validating hashes, references, counts, charts and layouts...", flush=True)
    from pipeline.validate import validate_bundle
    validation = validate_bundle(out, raw)
    elapsed = time.perf_counter() - start
    print(f"PASS: {len(ds.nodes):,} nodes / {len(ds.links):,} edges; "
          f"{quality['counts']['weak_components']} weak components; "
          f"{len(inventory) + 1} JSON files; {elapsed:.1f}s\nOutput: {out}", flush=True)
    return validation


def main():
    p = parser(__doc__)
    p.add_argument("--samples", type=int, default=96, help="Seeded betweenness source samples")
    p.add_argument("--focus-id", type=int, default=17255)
    p.add_argument("--max-nodes", type=int, default=600, help="Maximum overview nodes; focal ego is exported separately")
    p.add_argument("--candidate-career-years", type=int, default=10)
    p.add_argument("--candidate-active-within", type=int, default=None,
                   help="Optional activity window; absent records do not imply inactivity")
    p.add_argument("--compare-ids", type=int, nargs="*", default=[], help="Additional artist IDs for yearly network comparisons")
    p.add_argument("--window-years", type=int, default=5, help="Window for network dynamics; existing recent_5y features stay five-year")
    run_pipeline(p.parse_args())


if __name__ == "__main__":
    main()
