"""Centrality, collaboration, evidence-backed influence paths and Sailor's ego graph."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import defaultdict, deque
import networkx as nx
from pipeline.common import (Dataset, OBSERVATION_YEAR, WORK_TYPES, actor_influence_graph,
                             collaboration_graph, load_dataset, parser, rounded, write_json)


def pagerank(graph):
    return nx.pagerank(graph, alpha=0.85, max_iter=500, tol=1e-10, weight="weight") if len(graph) else {}


def compute_metrics(ds: Dataset, samples: int = 96) -> tuple[dict, nx.Graph, nx.DiGraph]:
    if samples < 1:
        raise ValueError("betweenness samples must be positive")
    collab = collaboration_graph(ds)
    influence = actor_influence_graph(ds)
    pr = pagerank(collab)
    # Citations point back to the inspiration source for prestige ranking.
    source_pr = pagerank(influence.reverse(copy=False))
    k = min(samples, len(collab))
    between = nx.betweenness_centrality(collab, k=k, seed=ds.seed, weight="distance") if k else {}
    degree = nx.degree_centrality(collab)
    components = sorted(nx.weakly_connected_components(ds.graph), key=lambda c: (-len(c), min(c)))
    component_ids = {node: i for i, comp in enumerate(components) for node in comp}
    rows = []
    for i, n in ds.nodes.items():
        row = {"id": i, "type": n["type"], "component_id": component_ids[i],
               "raw_in_degree": ds.graph.in_degree(i), "raw_out_degree": ds.graph.out_degree(i),
               "raw_neighbor_count": len(set(ds.graph.predecessors(i)) | set(ds.graph.successors(i)))}
        if i in collab:
            row.update(collaborator_count=collab.degree(i),
                       collaboration_strength=collab.degree(i, weight="weight"),
                       collaboration_degree_centrality=rounded(degree[i]),
                       collaboration_pagerank=rounded(pr[i]),
                       collaboration_betweenness=rounded(between[i]),
                       influence_source_pagerank=rounded(source_pr.get(i, 0)),
                       influenced_artist_count=influence.out_degree(i),
                       inspiration_artist_count=influence.in_degree(i),
                       influence_out_strength=rounded(influence.out_degree(i, weight="weight")))
        rows.append(row)
    return ({"meta": {**ds.meta, "betweenness_samples": k, "betweenness_approximate": k < len(collab),
                      "betweenness_distance": "1 / shared_work_count", "pagerank_alpha": 0.85,
                      "raw_degree_scope": "full observed graph; not a historical feature",
                      "artist_metric_scope": "direct credits and dated work references through cutoff"},
             "nodes": rows,
             "graph_sizes": {"collaboration_nodes": len(collab), "collaboration_edges": collab.number_of_edges(),
                             "influence_nodes": len(influence), "influence_edges": influence.number_of_edges()}},
            collab, influence)


def influence_paths(events: list[dict], seeds: set[int], reverse: bool = False, max_hops: int = 3) -> list[dict]:
    """One deterministic shortest structural path per reachable node, with edge IDs."""
    adjacency = defaultdict(list)
    for e in events:
        s, t = (e["target"], e["source"]) if reverse else (e["source"], e["target"])
        adjacency[s].append((t, e))
    seen = set(seeds)
    queue = deque((s, [s], [], []) for s in sorted(seeds))
    result = []
    while queue:
        node, path, edge_ids, years = queue.popleft()
        if len(edge_ids) >= max_hops:
            continue
        for target, event in sorted(adjacency[node], key=lambda p: (p[0], p[1]["id"])):
            if target in seen:
                continue
            seen.add(target)
            new_path, new_edges, new_years = path + [target], edge_ids + [event["id"]], years + [event["year"]]
            result.append({"id": target, "hops": len(new_edges), "seed_id": path[0],
                           "node_path": new_path, "event_ids": new_edges,
                           "event_years": new_years, "fully_dated": None not in new_years})
            queue.append((target, new_path, new_edges, new_years))
    return sorted(result, key=lambda row: (row["hops"], row["id"]))


def sailor_profile(ds: Dataset, collab: nx.Graph, focus: int = 17255) -> dict:
    if focus not in ds.nodes:
        raise ValueError(f"Focus node {focus} is not present")
    _, by_actor = ds.credits()
    works = by_actor.get(focus, {})
    context_nodes = [i for i, n in ds.nodes.items() if n["type"] not in WORK_TYPES or ds.visible_work(i)]
    structural = ds.graph.subgraph(context_nodes).to_undirected()
    hops = dict(nx.single_source_shortest_path_length(structural, focus, cutoff=2))
    events = ds.influence_events()
    usable = [e for e in events if e["eligible_structural"]
              and (ds.cutoff == OBSERVATION_YEAR or e["eligible_dated"])]
    seeds = {focus} | set(works)
    collaborators = []
    if focus in collab:
        for person in collab.neighbors(focus):
            work_ids = collab[focus][person]["work_ids"]
            years = [ds.nodes[w]["release_year"] for w in work_ids]
            collaborators.append({"id": person, "name": ds.nodes[person]["display_name"],
                                  "shared_work_count": len(work_ids), "work_ids": work_ids,
                                  "first_year": min(years), "last_year": max(years)})
    direct_sources = defaultdict(list)
    direct_targets = defaultdict(list)
    for e in usable:
        if e["target"] in seeds and e["source"] not in seeds:
            direct_sources[e["source"]].append(e["id"])
        if e["source"] in seeds and e["target"] not in seeds:
            direct_targets[e["target"]].append(e["id"])

    def ranked(groups):
        return [{"id": i, "name": ds.nodes[i]["display_name"], "reference_count": len(ids),
                 "event_ids": sorted(ids)} for i, ids in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0]))]

    return {
        "meta": {**ds.meta, "ego_scope": "undirected 2-hop structural context, not causal influence",
                 "propagation_scope": "5 musical reference types only; up to 3 hops",
                 "seed_basis": "focus person + directly credited works (all four creative roles)",
                 "undated_actor_references_included": ds.cutoff == OBSERVATION_YEAR,
                 "membership_dates": "unknown; never infer attendance on a work"},
        "focus_id": focus,
        "works": [{"id": w, "roles": sorted(roles)} for w, roles in
                  sorted(works.items(), key=lambda p: (ds.nodes[p[0]]["release_year"], p[0]))],
        "collaborators": sorted(collaborators, key=lambda r: (-r["shared_work_count"], r["id"])),
        "memberships": [e for e in ds.links if e["type"] == "MemberOf" and e["source"] == focus],
        "ego": {"nodes": [{"id": i, "hop": h} for i, h in sorted(hops.items())],
                "links": [e for e in ds.links if e["source"] in hops and e["target"] in hops]},
        "inspiration_sources": ranked(direct_sources), "directly_influenced": ranked(direct_targets),
        "upstream_paths": influence_paths(usable, seeds, reverse=True),
        "downstream_paths": influence_paths(usable, seeds),
        "events": [e for e in events if e["source"] in seeds or e["target"] in seeds],
    }


def main():
    p = parser(__doc__)
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--focus-id", type=int, default=17255)
    args = p.parse_args()
    ds = load_dataset(args.raw, args.cutoff, args.seed)
    result, collab, _ = compute_metrics(ds, args.samples)
    write_json(args.out, "node_metrics.json", result)
    write_json(args.out, "sailor_shift.json", sailor_profile(ds, collab, args.focus_id))
    print(f"Metrics -> {args.out}; {result['graph_sizes']}")


if __name__ == "__main__":
    main()
