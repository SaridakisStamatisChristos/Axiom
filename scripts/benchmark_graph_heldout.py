"""Compare AXIOM releases on the frozen held-out affine graph suite."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from statistics import median
import subprocess
import sys
from time import perf_counter

from axiom.graph_relations import AffineRelation

from benchmark_graph_proof import check_small_graphs, write_json

BASELINE = "f283c09f5269470369e1c9695b5dbc978913b0b9"
CURRENT = "fa2988031c1431eefd6311e72cf6db139893e68d"
SUITE = Path("research/proof_engine/heldout_graphs_v1.json")
SUITE_SHA256 = "70c5d5022b723f31942791d84c75735e5feda90415a4564d3282c151202e9a88"
COMMON = ("--max-lemmas", "3", "--max-coefficient", "3", "--max-nodes", "10000",
          "--witness-order", "5", "--timeout", "45")
FALLBACKS = ("--retrieve-lemmas", "5", "--synthesize-lemmas", "3",
             "--split-order", "--induct-edges", "--proof-plans", "16")
PROFILES = {
    "baseline": (),
    "extended": (*FALLBACKS, "--retrieval-index", "v1"),
    "structural": (*FALLBACKS, "--retrieval-index", "v2"),
    "matching": (*FALLBACKS, "--retrieval-index", "v3"),
}
VERIFIED = "FORMALLY_VERIFIED"


def outcome_strategy(attempt):
    if attempt["status"] != VERIFIED:
        return None, []
    plans = attempt.get("proof_plans", {})
    index = plans.get("accepted_index")
    if index is not None:
        return "proof_plan", plans["candidates"][index]
    lemmas = sorted({lemma["theorem"] for side in attempt["derivation"]["directions"]
                     for lemma in side["lemmas"]})
    for field in ("edge_induction", "order_split", "synthesis", "retrieval"):
        if attempt.get(field, {}).get("attempted"):
            return field, lemmas
    return "fixed_bank", lemmas


def run_attempt(code, root, case, profile, claim, violations):
    work = case / profile
    work.mkdir()
    source = work / "proof.lean"
    evidence = work / "attempt.json"
    env = dict(os.environ, PYTHONPATH=str(code / "src"))
    cli = [sys.executable, "-m", "axiom"]
    start = perf_counter()
    subprocess.run([*cli, "graph-prove", str(case / "statement.json"),
                    "--project-root", str(root), "--output", str(evidence),
                    "--source", str(source), *COMMON, *PROFILES[profile]],
                   cwd=code, env=env, check=True, timeout=90)
    elapsed = perf_counter() - start
    with (work / "audit.json").open("w", encoding="utf-8") as audit:
        subprocess.run([*cli, "graph-prove-audit", str(evidence)], cwd=code, env=env,
                       stdout=audit, check=True, timeout=90)
    attempt = json.loads(evidence.read_bytes())
    kernel = attempt["kernel"]
    status = attempt["status"]
    if (attempt["statement"] != claim.to_dict()
            or (status == "COUNTEREXAMPLE") != (violations > 0)):
        raise ValueError(f"statement or bounded-oracle disagreement in {evidence}")
    if status not in {VERIFIED, "COUNTEREXAMPLE", "SEARCH_EXHAUSTED", "LEAN_REJECTED"}:
        raise ValueError(f"unexpected benchmark outcome {status} in {evidence}")
    if attempt["generated"] is not None:
        if source.read_text(encoding="utf-8") != attempt["generated"]["source"]:
            raise ValueError(f"source does not match proof attempt in {evidence}")
    if status == VERIFIED and (attempt["scope"] != "ALL_GRAPH_ORDERS"
                               or not kernel["lean_kernel_executed"]):
        raise ValueError(f"missing universal Lean proof in {evidence}")
    strategy, lemmas = outcome_strategy(attempt)
    return {
        "status": status, "reason": attempt["reason"], "strategy": strategy,
        "lemmas": lemmas, "witness": attempt["counterexample"],
        "search_nodes": (attempt["derivation"] or {}).get("nodes"),
        "search_seconds": attempt["search_elapsed_seconds"],
        "lean_seconds": kernel["duration_seconds"] if kernel else None,
        "cli_seconds": elapsed, "axioms": kernel["axioms"] if kernel else None,
        "attempt_sha256": attempt["record_sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    trees = {name: path.resolve() for name, path in
             (("baseline", args.baseline), ("current", args.current))}
    for name, expected in (("baseline", BASELINE), ("current", CURRENT)):
        code = trees[name]
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=code, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=code, text=True)
        if sha != expected or dirty:
            raise ValueError(f"{name} requires a clean checkout at {expected}")
    raw = SUITE.read_bytes()
    if sha256(raw).hexdigest() != SUITE_SHA256:
        raise ValueError("held-out suite differs from the pre-execution freeze")
    out = args.output.resolve()
    out.mkdir(parents=True)
    rows = []
    profiles = list(PROFILES)
    with (out / "progress.ndjson").open("w", encoding="utf-8", buffering=1) as progress:
        for i, (case_id, premise, weights, rhs, op, cohort) in enumerate(json.loads(raw)):
            claim = AffineRelation.normalized(weights, rhs, premise, op)
            case = out / case_id
            case.mkdir()
            write_json(case / "statement.json", claim.to_dict())
            violations = check_small_graphs(claim)
            if cohort == "negative" and not violations:
                raise ValueError(f"negative control has no independently checked witness: {case_id}")
            offset = i % len(profiles)
            results = {name: run_attempt(trees["baseline" if name == "baseline" else "current"],
                                         root, case, name, claim, violations)
                       for name in profiles[offset:] + profiles[:offset]}
            row = {"id": case_id, "cohort": cohort, "statement": claim.to_dict(),
                   "small_graph_violations": violations, "profiles": results}
            rows.append(row)
            progress.write(json.dumps(row, sort_keys=True) + "\n")
            print(case_id, *(f"{name}={results[name]['status']}" for name in profiles), flush=True)
    summaries = {}
    for name in profiles:
        runs = [row["profiles"][name] for row in rows]
        timings = [r["cli_seconds"] for r in runs]
        summaries[name] = {
            "outcomes": dict(Counter(r["status"] for r in runs)),
            "proof_strategies": dict(Counter(r["strategy"] for r in runs if r["strategy"])),
            "median_cli_seconds": median(timings), "worst_cli_seconds": max(timings),
        }
    lean = subprocess.check_output(["lake", "env", "lean", "--version"], text=True).strip()
    mathlib = subprocess.check_output(
        ["git", "-C", ".lake/packages/mathlib", "rev-parse", "HEAD"], text=True).strip()
    write_json(out / "benchmark.json", {
        "schema": "axiom.graph_heldout_benchmark.v1", "suite_sha256": SUITE_SHA256,
        "baseline_sha": BASELINE, "current_sha": CURRENT,
        "runtime": {"os": platform.platform(), "python": platform.python_version(),
                    "lean": lean, "mathlib": mathlib},
        "common_cli_args": COMMON, "profile_cli_args": PROFILES,
        "profiles": summaries, "cases": rows,
    })


if __name__ == "__main__":
    main()
