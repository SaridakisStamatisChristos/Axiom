"""Measure public literature-transfer representation and exact finite coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path

import networkx as nx

from axiom.graph_explicit import ExplicitGraph
from axiom.graph_transfer import TransferStatement, check, replay

ROOT = Path(__file__).resolve().parents[1]


def explicit(graph):
    return ExplicitGraph.from_dict({"n": len(graph), "edges": [list(e) for e in graph.edges()]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads((ROOT / "research/autographforge/typed-literature-v1.json").read_bytes())
    cases = {name: TransferStatement.from_dict(row) for name, row in raw.items()}
    # The atlas is a public development corpus. Named cases check source-known
    # outcomes, including the order-nine friendship counterexample to TXG-4.
    named = {"K2": nx.complete_graph(2), "friendship-4": nx.windmill_graph(4, 3),
             "C6": nx.cycle_graph(6), "Petersen": nx.petersen_graph()}
    graphs = {f"atlas-{i}": g for i, g in enumerate(nx.graph_atlas_g())
              if not any(g.order() == target.order() and nx.is_isomorphic(g, target)
                         for target in named.values())}
    graphs.update(named)
    outcomes = {}
    for name, statement in cases.items():
        counts = Counter()
        hits = {}
        sample = {}
        for ident, g in graphs.items():
            record = check(statement, explicit(g))
            counts[record["status"]] += 1
            if ident in named or record["status"] == "COUNTEREXAMPLE":
                replay(statement, record)
            if record["status"] == "COUNTEREXAMPLE":
                hits[ident] = record
            if ident in named:
                sample[ident] = record
        outcomes[name] = {"counts": dict(counts), "counterexamples": hits, "named_evidence": sample}
    if outcomes["TXG-1"]["named_evidence"]["K2"]["status"] != "COUNTEREXAMPLE":
        raise ValueError("K2 did not reproduce the published-scope boundary issue")
    friendship = outcomes["TXG-4"]["named_evidence"]["friendship-4"]
    if (friendship["status"], friendship["left"], friendship["right"]) != ("COUNTEREXAMPLE", "4", "18/5"):
        raise ValueError("friendship-graph refutation differs from the source")
    report = {"schema": "axiom.graph.transfer_benchmark.v1", "networkx": nx.__version__,
              "representable": len(cases), "submitted": len(raw), "lean_verified": 0,
              "graphs_per_target": len(graphs), "targets": outcomes,
              "prior_art": {
                  "TXG-1": "https://arxiv.org/abs/2607.01438",
                  "TXG-3": "https://github.com/djma/TxGraffiti-conjecture3-counterexample",
                  "TXG-4": "https://arxiv.org/abs/2606.15761",
              }}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print({name: row["counts"] for name, row in outcomes.items()}, flush=True)


if __name__ == "__main__":
    main()
