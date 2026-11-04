"""Preserve evidence, normalize years and export a lossless directed multigraph."""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.common import Dataset, load_dataset, parser, write_json


def build(ds: Dataset) -> dict:
    return {"meta": ds.meta, "directed": True, "multigraph": True, "graph": ds.graph_attributes,
            "nodes": list(ds.nodes.values()), "links": ds.links}


def main():
    args = parser(__doc__).parse_args()
    ds = load_dataset(args.raw, args.cutoff, args.seed)
    path = write_json(args.out, "clean_graph.json", build(ds))
    print(f"{len(ds.nodes)} nodes, {len(ds.links)} links -> {path}")


if __name__ == "__main__":
    main()
