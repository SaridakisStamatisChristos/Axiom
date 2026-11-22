"""Run the mutation-search pilot on frozen historical false graph statements."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import networkx as nx

from axiom.graph_active_refute import search
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import replay_witness
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1] / "research" / "autographforge"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-100", action="store_true")
    args = parser.parse_args()
    history = json.loads((ROOT / "discovery-v7.json").read_bytes())
    controls = json.loads((ROOT / "discovery-v7-expected.json").read_bytes())["refuted"]
    if args.frozen_100:
        cases = json.loads((ROOT / "active-refutation-100-v1.json").read_bytes())["cases"]
        history = {row["id"]: row for row in cases}
        controls = list(history)
    panels = [nx.empty_graph(n) for n in (0, 1, 2, 3)]
    panels.extend(graph for n in (5, 6, 7, 8, 10, 11, 12)
                  for graph in (nx.cycle_graph(n), nx.path_graph(n),
                                nx.complete_bipartite_graph(n // 2, n - n // 2),
                                nx.gnp_random_graph(n, 0.4, seed=44219 + n)))
    seeds = [ExplicitGraph.from_dict({"n": len(graph), "edges": [list(e) for e in graph.edges()]})
             for graph in panels]
    results = {}
    for identity in controls:
        claim = AffineRelation.from_dict(history[identity]["statement"])
        started = perf_counter()
        result = search(claim, seeds, seed=1729, budget=1000, beam=8)
        outcome = result["status"]
        if outcome == "REFUTED":
            replay_witness(claim, result["witness"])
        results[identity] = {"statement": claim.to_dict(), "result": result,
                             "wall_seconds": perf_counter() - started}
        print(identity[-8:], outcome, result["evaluations"], flush=True)
    report = {"schema": "axiom.graph.active_refutation_pilot.v1", "networkx": nx.__version__,
              "historical_false_total": len(controls), "results": results,
              "seed_graphs": [g.to_dict() for g in seeds],
              "note": "historical false statements; no equal-compute unseen-family evaluation"}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
