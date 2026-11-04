"""Shared schema, conservative normalization and traceable graph projections."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import sys

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data/raw/MC1_graph.json"
DEFAULT_OUT = ROOT / "data/processed"
SCHEMA_VERSION = "1.1.0"
OBSERVATION_YEAR = 2040  # Story time, independent of the computer's date.
WORK_TYPES = {"Song", "Album"}
ACTOR_TYPES = {"Person", "MusicalGroup"}
CREDIT_TYPES = {"PerformerOf", "ComposerOf", "ProducerOf", "LyricistOf"}
INFLUENCE_TYPES = {
    "InStyleOf", "InterpolatesFrom", "CoverOf", "LyricalReferenceTo", "DirectlySamples"
}
NODE_TYPES = WORK_TYPES | ACTOR_TYPES | {"RecordLabel"}
EDGE_TYPES = CREDIT_TYPES | INFLUENCE_TYPES | {"RecordedBy", "DistributedBy", "MemberOf"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(out: Path, name: str, value) -> Path:
    """Atomic individual files; no NaN, platform newlines or timestamps."""
    out = out.resolve()
    raw = (ROOT / "data/raw").resolve()
    if out == raw or raw in out.parents:
        raise ValueError("data/raw/ is read-only; choose data/processed/ or a scratch directory")
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False,
                              sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)
    return path


def parser(description: str) -> argparse.ArgumentParser:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--cutoff", type=int, default=OBSERVATION_YEAR,
                   help="As-of year in the synthetic story (default: 2040)")
    p.add_argument("--seed", type=int, default=42)
    return p


def valid_year(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    return int(text) if re.fullmatch(r"[0-9]{4}", text) else None


def official_endpoint_types(edge_type: str, source: str, target: str) -> bool:
    if edge_type == "PerformerOf":
        return source in ACTOR_TYPES and target in WORK_TYPES
    if edge_type in {"ComposerOf", "LyricistOf"}:
        return source == "Person" and target in WORK_TYPES
    if edge_type == "ProducerOf":
        return source in {"Person", "RecordLabel"} and target in WORK_TYPES | ACTOR_TYPES
    if edge_type in {"RecordedBy", "DistributedBy"}:
        return source in WORK_TYPES and target == "RecordLabel"
    if edge_type == "MemberOf":
        return source == "Person" and target == "MusicalGroup"
    if edge_type == "InStyleOf":
        return source in WORK_TYPES and target in WORK_TYPES | ACTOR_TYPES
    if edge_type in INFLUENCE_TYPES:
        return source in WORK_TYPES and target in WORK_TYPES
    return False


@dataclass
class Dataset:
    nodes: dict[int, dict]
    links: list[dict]
    graph: nx.MultiDiGraph
    issues: list[dict]
    source_sha256: str
    cutoff: int = OBSERVATION_YEAR
    seed: int = 42
    graph_attributes: dict = field(default_factory=dict)

    @property
    def meta(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "source_sha256": self.source_sha256,
                "observation_year": OBSERVATION_YEAR, "cutoff_year": self.cutoff,
                "seed": self.seed}

    def visible_work(self, node_id: int) -> bool:
        n = self.nodes[node_id]
        return (n["type"] in WORK_TYPES and n.get("release_year") is not None
                and n["release_year"] <= self.cutoff)

    def credits(self) -> tuple[dict, dict]:
        """Direct dated credits only. Membership has no dates: never expand it."""
        by_work = defaultdict(lambda: defaultdict(set))
        by_actor = defaultdict(lambda: defaultdict(set))
        for e in self.links:
            a, w = e["source"], e["target"]
            if (e["type"] in CREDIT_TYPES and self.nodes[a]["type"] in ACTOR_TYPES
                    and self.visible_work(w)):
                by_work[w][a].add(e["type"])
                by_actor[a][w].add(e["type"])
        return by_work, by_actor

    def influence_events(self) -> list[dict]:
        """Reverse reference arrows for diffusion; retain all raw edge provenance."""
        result = []
        for e in self.links:
            if e["type"] not in INFLUENCE_TYPES:
                continue
            consumer, origin = self.nodes[e["source"]], self.nodes[e["target"]]
            year = consumer.get("release_year") if consumer["type"] in WORK_TYPES else None
            flags = set(e["quality_flags"])
            if consumer["type"] in WORK_TYPES and year is None:
                flags.add("missing_event_year")
            observable = all(n["type"] not in WORK_TYPES or self.visible_work(n["id"])
                             for n in (consumer, origin))
            invalid = bool(flags & {"self_loop", "duplicate_relation", "influence_chronology"})
            result.append({
                "id": e["id"], "type": e["type"],
                "source": origin["id"], "target": consumer["id"],
                "raw_source": consumer["id"], "raw_target": origin["id"],
                "year": year, "year_basis": "influenced_work_release" if year else "unknown",
                "source_genre": origin.get("genre"), "target_genre": consumer.get("genre"),
                "quality_flags": sorted(flags),
                "eligible_dated": observable and not invalid and year is not None,
                "eligible_structural": observable and not invalid,
            })
        return result


def load_dataset(raw: Path = DEFAULT_RAW, cutoff: int = OBSERVATION_YEAR, seed: int = 42) -> Dataset:
    if not 1000 <= cutoff <= OBSERVATION_YEAR:
        raise ValueError("cutoff must be a four-digit year <= 2040")
    content = raw.read_bytes()
    data = json.loads(content.decode("utf-8-sig"))
    if not data.get("directed") or not data.get("multigraph"):
        raise ValueError("Expected an official directed multigraph")
    nodes, issues = {}, []

    def issue(code, **detail):
        issues.append({"code": code, **detail})

    for row in data["nodes"]:
        i = row["id"]
        if not isinstance(i, int) or isinstance(i, bool) or i in nodes:
            raise ValueError(f"Invalid or duplicate node id: {i!r}")
        node_type = row["Node Type"]
        if node_type not in NODE_TYPES:
            raise ValueError(f"Unknown node type {node_type!r} at {i}")
        n = {"id": i, "type": node_type, "name": row["name"],
             "display_name": row.get("stage_name") or row["name"],
             "quality_flags": [], "raw_attributes": {k: v for k, v in row.items() if k != "id"}}
        for key in ("stage_name", "genre", "notable", "single"):
            if key in row:
                n[key] = row[key]
        if node_type in WORK_TYPES:
            for old, new in (("release_date", "release_year"), ("written_date", "written_year"),
                             ("notoriety_date", "chart_year")):
                n[new] = valid_year(row.get(old))
                if old in row and n[new] is None:
                    n["quality_flags"].append("invalid_" + new)
                    issue("invalid_year", node_id=i, field=old, value=row[old])
                if n[new] is not None and n[new] > OBSERVATION_YEAR:
                    n["quality_flags"].append("beyond_observation_" + new)
                    issue("beyond_observation_year", node_id=i, field=old, value=row[old])
            if n["release_year"] is None:
                n["quality_flags"].append("missing_release_year")
                issue("missing_release_year", node_id=i)
            for key, code in (("written_year", "written_after_release"), ("chart_year", "chart_before_release")):
                value, release = n[key], n["release_year"]
                invalid = value is not None and release is not None and (
                    value > release if key == "written_year" else value < release)
                if invalid:
                    n["quality_flags"].append(code)
                    issue(code, node_id=i, release_year=release, value=value)
            if row.get("notable") is True and n["chart_year"] is None:
                issue("notable_without_chart_year", node_id=i)
                n["quality_flags"].append("notable_without_chart_year")
            if row.get("notable") is False and n["chart_year"] is not None:
                issue("chart_status_conflict", node_id=i)
                n["quality_flags"].append("chart_status_conflict")
        nodes[i] = n

    links, keys, relations = [], set(), set()
    for row in data.get("links", data.get("edges", [])):
        s, t, key, relation = row["source"], row["target"], row["key"], row["Edge Type"]
        if s not in nodes or t not in nodes:
            raise ValueError(f"Dangling endpoint: {s} -> {t}")
        if (s, t, key) in keys:
            raise ValueError(f"Duplicate multigraph key would overwrite evidence: {(s, t, key)}")
        if relation not in EDGE_TYPES:
            raise ValueError(f"Unknown edge type: {relation}")
        keys.add((s, t, key))
        e = {"id": f"{s}:{t}:{key}", "source": s, "target": t, "key": key,
             "type": relation, "quality_flags": []}
        if not official_endpoint_types(relation, nodes[s]["type"], nodes[t]["type"]):
            e["quality_flags"].append("schema_endpoint_deviation")
        if s == t:
            e["quality_flags"].append("self_loop")
        if (s, t, relation) in relations:
            e["quality_flags"].append("duplicate_relation")
        relations.add((s, t, relation))
        sy, ty = nodes[s].get("release_year"), nodes[t].get("release_year")
        if relation in INFLUENCE_TYPES and sy is not None and ty is not None and sy < ty:
            e["quality_flags"].append("influence_chronology")
        for flag in e["quality_flags"]:
            issue(flag, edge_id=e["id"], source=s, target=t, relation=relation)
        links.append(e)
    nodes = dict(sorted(nodes.items()))
    links.sort(key=lambda e: (e["source"], e["target"], e["key"]))
    graph = nx.MultiDiGraph()
    graph.graph.update(data.get("graph", {}))
    graph.add_nodes_from((i, n) for i, n in nodes.items())
    # Explicit construction avoids NetworkX's changing links/edges JSON default.
    for e in links:
        graph.add_edge(e["source"], e["target"], key=e["key"],
                       **{k: v for k, v in e.items() if k not in {"source", "target", "key"}})
    return Dataset(nodes, links, graph, issues, hashlib.sha256(content).hexdigest(), cutoff, seed,
                   graph_attributes=data.get("graph", {}))


def collaboration_graph(ds: Dataset) -> nx.Graph:
    by_work, by_actor = ds.credits()
    graph = nx.Graph()
    graph.add_nodes_from(sorted(by_actor))
    for work, people in sorted(by_work.items()):
        for a, b in combinations(sorted(people), 2):
            if not graph.has_edge(a, b):
                graph.add_edge(a, b, weight=0, work_ids=[])
            graph[a][b]["weight"] += 1
            graph[a][b]["work_ids"].append(work)
    for _, _, d in graph.edges(data=True):
        d["distance"] = 1 / d["weight"]
    return graph


def performer_ids(by_work: dict, work_id: int) -> list[int]:
    return sorted(a for a, roles in by_work.get(work_id, {}).items() if "PerformerOf" in roles)


def actor_influence_graph(ds: Dataset) -> nx.DiGraph:
    """Dated work references only; fractional attribution avoids large-cast inflation."""
    by_work, by_actor = ds.credits()
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(by_actor))
    for e in ds.influence_events():
        if not e["eligible_dated"]:
            continue
        origins = performer_ids(by_work, e["source"])
        consumers = performer_ids(by_work, e["target"])
        if not origins or not consumers:
            continue
        weight = 1 / (len(origins) * len(consumers))
        for a in origins:
            for b in consumers:
                if a == b:
                    continue
                if not graph.has_edge(a, b):
                    graph.add_edge(a, b, weight=0.0, event_ids=[])
                graph[a][b]["weight"] += weight
                graph[a][b]["event_ids"].append(e["id"])
    return graph


def rounded(value: float) -> float:
    return round(float(value), 10)
