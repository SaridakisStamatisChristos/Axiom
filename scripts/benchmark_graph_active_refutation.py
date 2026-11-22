"""Compare bounded graph refutation profiles on frozen false statements."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import networkx as nx

from axiom.graph_active_refute import PROFILES, search
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import certify_witness, replay_witness
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1] / "research" / "autographforge"


def seed_panel():
    panels = [nx.empty_graph(n) for n in (0, 1, 2, 3)]
    panels.extend(graph for n in (5, 6, 7, 8, 10, 11, 12)
                  for graph in (nx.cycle_graph(n), nx.path_graph(n),
                                nx.complete_bipartite_graph(n // 2, n - n // 2),
                                nx.gnp_random_graph(n, 0.4, seed=44219 + n)))
    return [ExplicitGraph.from_dict({"n": len(graph), "edges": [list(e) for e in graph.edges()]})
            for graph in panels]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    suite = parser.add_mutually_exclusive_group()
    suite.add_argument("--frozen-100", action="store_true")
    suite.add_argument("--census-challenge", action="store_true")
    parser.add_argument("--profile", choices=PROFILES, default="portfolio-v2")
    parser.add_argument("--budget", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    history = json.loads((ROOT / "discovery-v7.json").read_bytes())
    controls = json.loads((ROOT / "discovery-v7-expected.json").read_bytes())["refuted"]
    if args.frozen_100:
        cases = json.loads((ROOT / "active-refutation-100-v1.json").read_bytes())["cases"]
        history = {row["id"]: row for row in cases}
        controls = list(history)
    if args.census_challenge:
        cases = json.loads((ROOT / "refutation-census-challenge-v1.json").read_bytes())["cases"]
        history = {row["id"]: row for row in cases}
        controls = list(history)
    seeds = seed_panel()
    results = {}
    for identity in controls:
        claim = AffineRelation.from_dict(history[identity]["statement"])
        if claim.id != identity:
            raise ValueError("benchmark claim ID differs")
        if args.census_challenge:
            graph = ExplicitGraph.from_graph6(history[identity]["witness_graph6"])
            certify_witness(claim, graph, origin="independent census label")
        started = perf_counter()
        result = search(claim, seeds, seed=args.seed, budget=args.budget, beam=8, profile=args.profile)
        outcome = result["status"]
        if outcome == "REFUTED":
            replay_witness(claim, result["witness"])
        results[identity] = {"statement": claim.to_dict(), "result": result,
                             "wall_seconds": perf_counter() - started}
        print(identity[-8:], outcome, result["evaluations"], flush=True)
    report = {"schema": "axiom.graph.active_refutation_benchmark.v2", "networkx": nx.__version__,
              "profile": args.profile, "budget": args.budget, "seed": args.seed,
              "case_count": len(controls), "results": results,
              "seed_graphs": [g.to_dict() for g in seeds],
              "suite": "census_challenge" if args.census_challenge else (
                  "frozen_100" if args.frozen_100 else "historical_pilot")}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
