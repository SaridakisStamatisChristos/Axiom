"""Compare AXIOM with AutoGraphForge heuristics using one exact graph objective."""
import argparse
from dataclasses import replace
import json
from math import inf
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

from axiom.graph_active_refute import _score, search
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import MAX_EXACT_ORDER, certify_witness
from axiom.graph_relations import AffineRelation
from benchmark_graph_active_refutation import ROOT, seed_panel

SEARCHERS = ("cross_entropy", "vns", "sa", "mcts")
TIME_LIMIT = 5


class EvaluationBudgetReached(BaseException):
    """Stop the external dispatcher even when a searcher catches Exception."""


class TypedObjective:
    def __init__(self, claim, budget):
        self.claim = claim
        self.budget = budget
        self.scores = {}
        self.witness = None

    def __call__(self, graph):
        if graph not in self.scores:
            if len(self.scores) >= self.budget:
                raise EvaluationBudgetReached
            score = _score(self.claim, graph)
            self.scores[graph] = -inf if score is None else score
            if score is not None and score > 0:
                self.witness = graph
        return self.scores[graph]


def compare(claim, initial, runner, problem_type, config, *, budget, seed):
    objective = TypedObjective(claim, budget)
    premise = claim.bound.assumption.lower()

    class SharedObjective(problem_type):
        def violation(self, graph):
            if graph is None:
                return -inf
            labels = {node: i for i, node in enumerate(sorted(graph.nodes))}
            explicit = ExplicitGraph.from_dict({"n": len(labels),
                                                "edges": [[labels[a], labels[b]] for a, b in graph.edges]})
            value = objective(explicit)
            if value > self.best_violation:
                self.best_violation, self.best_graph = value, graph.copy()
            return value

    started = perf_counter()
    exhausted = False
    try:
        if not any(objective(graph) > 0 for graph in initial):
            # Keep AutoGraphForge's class-preserving moves and dispatcher.
            # Supply only the exact objective and a hard unique-evaluation cap.
            with patch.dict(runner.__globals__, {"GraphSearchProblem": SharedObjective}):
                runner(None, [], config, hypothesis_class=None if premise == "all" else premise, seed=seed)
    except EvaluationBudgetReached:
        exhausted = True
    elapsed = perf_counter() - started
    if objective.witness is not None:
        certify_witness(claim, objective.witness, origin="AutoGraphForge shared objective")
    axiom = search(claim, initial, seed=seed, budget=budget)
    return {"id": claim.id, "autographforge_refuted": objective.witness is not None,
            "autographforge_evaluations": len(objective.scores), "autographforge_evaluation_cap": exhausted,
            "autographforge_seconds": elapsed,
            "axiom_refuted": axiom["status"] == "REFUTED", "axiom_evaluations": axiom["evaluations"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autographforge", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--budget", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    if not 1 <= args.budget <= 100_000:
        parser.error("budget must be between 1 and 100000")
    revision = subprocess.check_output(["git", "-C", str(args.autographforge), "rev-parse", "HEAD"],
                                       text=True).strip()
    sys.path.insert(0, str(args.autographforge.resolve()))
    from config import CONFIG
    from pipeline.search import GraphSearchProblem, find_counterexample

    orders = tuple(range(3, MAX_EXACT_ORDER + 1))
    config = replace(CONFIG, cegis_searchers=SEARCHERS, search_orders=orders,
                     search_time_budget_s=TIME_LIMIT, rl_enabled=False)
    initial = sorted(set(seed_panel()), key=lambda graph: (graph.n, graph.edges))
    outcomes = {}
    for suite in ("active-refutation-100-v1", "refutation-census-challenge-v1"):
        cases = json.loads((ROOT / f"{suite}.json").read_bytes())["cases"]
        outcomes[suite] = [
            compare(AffineRelation.from_dict(item["statement"]), initial, find_counterexample,
                    GraphSearchProblem, config, seed=args.seed, budget=args.budget)
            for item in cases
        ]
    report = {"schema": "axiom.graph.refutation_searcher_comparison.v1", "autographforge_commit": revision,
              "autographforge_searchers": SEARCHERS, "autographforge_orders": orders,
              "autographforge_time_limit_seconds": TIME_LIMIT, "budget": args.budget, "seed": args.seed,
              "suites": outcomes}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
