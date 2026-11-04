"""Audit actual data, including discrepancies with the official description."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import Counter, defaultdict
import networkx as nx
from pipeline.common import Dataset, WORK_TYPES, load_dataset, parser, write_json


def explore(ds: Dataset) -> dict:
    components = sorted(nx.weakly_connected_components(ds.graph), key=lambda c: (-len(c), min(c)))
    work = [n for n in ds.nodes.values() if n["type"] in WORK_TYPES]
    names = defaultdict(list)
    for i, n in ds.nodes.items():
        names[(n["type"], n["name"])].append(i)
    date_stats = {}
    for field in ("release_year", "written_year", "chart_year"):
        known = [n[field] for n in work if n[field] is not None]
        date_stats[field] = {"present": len(known), "missing": len(work) - len(known),
                             "min": min(known, default=None), "max": max(known, default=None)}
    return {
        "meta": ds.meta,
        "counts": {"nodes": len(ds.nodes), "links": len(ds.links),
                   "weak_components": len(components), "self_loops": nx.number_of_selfloops(ds.graph),
                   "node_types": dict(Counter(n["type"] for n in ds.nodes.values())),
                   "edge_types": dict(Counter(e["type"] for e in ds.links))},
        "official_description": {"nodes": 17412, "links": 37857, "weak_components_claim": 18},
        "components": [{"id": i, "size": len(c), "representative_id": min(c),
                        "contains_sailor_shift": 17255 in c,
                        "oceanus_work_count": sum(ds.nodes[n].get("genre") == "Oceanus Folk" for n in c)}
                       for i, c in enumerate(components)],
        "year_fields": date_stats,
        "chart_status": {"notable": sum(n.get("notable") is True for n in work),
                         "notable_without_year": sum(n.get("notable") is True and n["chart_year"] is None for n in work)},
        "duplicate_names": [{"type": t, "name": name, "ids": ids}
                            for (t, name), ids in sorted(names.items()) if len(ids) > 1],
        "issue_counts": dict(sorted(Counter(i["code"] for i in ds.issues).items())),
        "issues": ds.issues,
        "policy": {"raw_modified": False, "merge_by_name": False, "drop_components": False,
                   "impute_chart_year": False, "undated_membership_expanded": False,
                   "suspect_edges": "preserved in clean_graph; flagged/excluded from dated influence analysis"},
    }


def main():
    args = parser(__doc__).parse_args()
    result = explore(load_dataset(args.raw, args.cutoff, args.seed))
    path = write_json(args.out, "quality_report.json", result)
    print(f"Audit -> {path}\nCounts: {result['counts']}\nIssues: {result['issue_counts']}")


if __name__ == "__main__":
    main()
