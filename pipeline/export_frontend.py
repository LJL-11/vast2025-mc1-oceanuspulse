"""Bounded D3/ECharts views, deterministic offline layouts and sharded artist details."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import Counter
import math
import networkx as nx

from pipeline.common import Dataset, WORK_TYPES, parser, rounded

SHARD_COUNT = 64


def node_view(node: dict) -> dict:
    fields = ("id", "type", "name", "display_name", "stage_name", "genre", "release_year",
              "written_year", "chart_year", "notable", "single", "quality_flags")
    return {key: node[key] for key in fields if key in node}


def force_view(ds: Dataset, ids: list[int], scope: str) -> dict:
    selected = set(ids)
    graph = nx.Graph()
    graph.add_nodes_from(sorted(selected))
    links = [dict(e) for e in ds.links if e["source"] in selected and e["target"] in selected]
    # Layout is geometry, not an influence statistic. Parallel edges count once here.
    graph.add_edges_from((e["source"], e["target"]) for e in links if e["source"] != e["target"])
    positions = {}
    components = sorted(nx.connected_components(graph), key=lambda c: (-len(c), min(c)))
    # Pack disconnected components into separate grid cells to avoid overlap.
    columns = max(1, math.ceil(math.sqrt(len(components))))
    for index, component in enumerate(components):
        local = nx.spring_layout(graph.subgraph(sorted(component)).copy(), seed=ds.seed,
                                 iterations=100, scale=240, weight=None)
        cx, cy = (index % columns) * 600, (index // columns) * 600
        for node, coordinates in local.items():
            positions[node] = (rounded(coordinates[0] + cx), rounded(coordinates[1] + cy))
    return {"meta": {**ds.meta, "scope": scope, "direction": "original raw relation direction",
                     "layout": "component-packed NetworkX spring layout; 100 iterations; unweighted",
                     "node_count": len(selected), "link_count": len(links),
                     "full_node_count": len(ds.nodes), "omitted_node_count": len(ds.nodes) - len(selected)},
            "nodes": [{**node_view(ds.nodes[i]), "x": positions[i][0], "y": positions[i][1]} for i in sorted(selected)],
            "links": links}


def export_views(ds: Dataset, quality: dict, metrics: dict, sailor: dict,
                 features: dict, timelines: dict, baseline: dict, max_nodes: int = 600) -> dict[str, dict]:
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    # Priority: focal node and its nearest context, then high-degree nodes.
    ego_ids = [r["id"] for r in sorted(sailor["ego"]["nodes"], key=lambda r: (r["hop"], r["id"]))]
    ego_set = set(ego_ids)
    remaining = sorted((i for i, n in ds.nodes.items() if i not in ego_set
                        and (n["type"] not in WORK_TYPES or ds.visible_work(i))),
                       key=lambda i: (-ds.graph.degree(i), i))
    overview_ids = (ego_ids + remaining)[:max_nodes]
    overview = force_view(ds, overview_ids, "bounded overview: focal ego first, then high-degree nodes; not representative sampling")
    ego_view = force_view(ds, ego_ids, "complete focal 2-hop ego; structural context")
    # A complete node index is searchable without downloading the raw 37k edges.
    index = {"meta": {**ds.meta, "scope": "all observed entities; final-snapshot fields, not historical labels"},
             "nodes": [node_view(n) for n in ds.nodes.values()]}
    artist_metrics = {r["id"]: r for r in metrics["nodes"]}
    timeline_by_id = {r["id"]: r for r in timelines["artists"]}
    shards = {i: {} for i in range(SHARD_COUNT)}
    artist_index = []
    for row in features["artists"]:
        i = row["id"]
        shard = i % SHARD_COUNT
        shards[shard][str(i)] = {"features": row, "metrics": artist_metrics[i],
                               "timeline": timeline_by_id[i]}
        artist_index.append({key: row[key] for key in
                             ("id", "name", "type", "first_release_year", "last_release_year", "work_count", "oceanus_performed_work_count")})
    outputs = {"network_overview.json": overview, "sailor_ego.json": ego_view, "node_index.json": index,
               "artist_index.json": {"meta": {**ds.meta, "shard_count": SHARD_COUNT,
                                               "shard_path": "artists/{id % 64, zero-padded to 2 digits}.json"},
                                     "artists": artist_index},
               "overview.json": {"meta": ds.meta, "counts": quality["counts"],
                                 "year_fields": quality["year_fields"], "chart_status": quality["chart_status"],
                                 "issue_counts": quality["issue_counts"],
                                 "components": quality["components"], "graph_sizes": metrics["graph_sizes"],
                                 "focus_id": sailor["focus_id"], "candidate_count": baseline["candidate_count"],
                                 "node_types": sorted(quality["counts"]["node_types"]),
                                 "edge_types": sorted(quality["counts"]["edge_types"]),
                                 "genre_work_counts": dict(sorted(Counter(n["genre"] for n in ds.nodes.values() if ds.visible_work(n["id"])).items()))}}
    for shard, artists in shards.items():
        outputs[f"artists/{shard:02d}.json"] = {"meta": features["meta"], "artists": artists}
    return outputs


def main():
    # Running the exporter alone still builds coherent inputs; no stale-file dependency.
    from pipeline.run import run_pipeline
    p = parser(__doc__)
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--focus-id", type=int, default=17255)
    p.add_argument("--max-nodes", type=int, default=600)
    p.add_argument("--candidate-career-years", type=int, default=10)
    p.add_argument("--candidate-active-within", type=int, default=None)
    p.add_argument("--compare-ids", type=int, nargs="*", default=[])
    p.add_argument("--window-years", type=int, default=5)
    args = p.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
