"""Build a pinned corpus from nauty and independently check sampled canonicalization."""
import argparse
import json
from pathlib import Path
import subprocess
from time import perf_counter

from axiom.graph_corpus import file_digest, ingest, summarize
from axiom.graph_explicit import ExplicitGraph

COUNTS = (0, 1, 1, 2, 6, 21, 112, 853, 11117, 261080)
SOURCE = "https://pallini.di.uniroma1.it/nauty2_9_3.tar.gz"
SOURCE_SHA = "9fc4edae04f88a0f5883985be3b39cf7f898fd6cc96e96b9ee25452743cc1b5b"


def structured():
    import networkx as nx

    cohorts = {
        "trees": [nx.path_graph(n) for n in range(8, 20)] + [nx.star_graph(n - 1) for n in range(8, 20)],
        "regular": [nx.cycle_graph(n) for n in range(8, 20)],
        "multipartite": [nx.complete_multipartite_graph(2, 3, n) for n in range(4, 13)],
        "joins": [nx.full_join(nx.path_graph(n), nx.empty_graph(3), rename=("path", "isolates")) for n in range(7, 13)],
        "disjoint": [nx.disjoint_union(nx.cycle_graph(n), nx.path_graph(3)) for n in range(7, 13)],
        "grids": [nx.grid_2d_graph(m, n) for m, n in ((2, 5), (3, 4), (4, 4), (4, 5))],
        "extremal": [nx.complete_graph(n) for n in range(8, 20)] + [nx.barbell_graph(n, 0) for n in range(4, 10)],
        "named": [nx.petersen_graph(), nx.heawood_graph(), nx.mycielskian(nx.cycle_graph(5)),
                  nx.mycielskian(nx.cycle_graph(7))],
    }
    for family, graphs in cohorts.items():
        result = []
        for graph in graphs:
            graph = nx.convert_node_labels_to_integers(graph, ordering="sorted")
            result.append(ExplicitGraph.from_dict({"n": len(graph), "edges": [list(e) for e in graph.edges()]}).graph6())
        yield family, result, nx.__version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geng", type=Path, required=True)
    parser.add_argument("--labelg", type=Path, required=True)
    parser.add_argument("--nauty-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = perf_counter()
    if file_digest(args.nauty_archive) != SOURCE_SHA:
        raise ValueError("nauty archive differs from the pinned 2.9.3 release")
    geng = args.geng.resolve()
    db = args.output / "graphs.sqlite3"
    directory = args.output / "sources"
    directory.mkdir(parents=True, exist_ok=True)
    censuses = [(f"connected-{n}", ["-c", str(n)], COUNTS[n]) for n in range(1, 10)]
    censuses += [(f"all-{n}", [str(n)], None) for n in range(1, 8)]
    censuses.append(("connected-10-shard", ["-c", "10", "7/128"], None))
    binary = file_digest(geng)
    for family, options, expected in censuses:
        path = directory / f"{family}.g6"
        if not path.exists():
            pending = path.with_suffix(".pending")
            with pending.open("wb") as output:
                subprocess.run([str(geng), "-q", *options], stdout=output, check=True)
            pending.replace(path)
        if expected is not None:
            with path.open("rb") as stream:
                if sum(1 for _ in stream) != expected:
                    raise ValueError(f"census count mismatch for {family}")
        ingest(db, path, args.labelg, family=family, origin=SOURCE,
               parameters={"generator": "nauty geng 2.9.3", "sha256": binary,
                           "source_archive_sha256": SOURCE_SHA, "argv": options})
        print(family, flush=True)
    path = directory / "empty.g6"
    path.write_text("?\n", encoding="ascii")
    ingest(db, path, args.labelg, family="empty", origin="unique graph of order zero")
    for family, lines, version in structured():
        name = f"structured-{family}"
        path = directory / f"{name}.g6"
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        ingest(db, path, args.labelg, family=name, origin="NetworkX graph constructors",
               parameters={"networkx_version": version, "constructor_recipe": "axiom.structured.v1"})
    manifest = summarize(db)
    for order in range(1, 10):
        if manifest["sources"][f"connected-{order}"]["unique_graph_count"] != COUNTS[order]:
            raise ValueError(f"canonical census count mismatch for order {order}")
    if manifest["unique_graph_count"] < 350_000:
        raise ValueError("corpus below 350,000-graph gate")
    manifest["wall_seconds"] = perf_counter() - started
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(manifest["unique_graph_count"], manifest["corpus_sha256"], flush=True)


if __name__ == "__main__":
    main()
