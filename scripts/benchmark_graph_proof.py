"""Run the frozen comparison through the CLI and both real Lean proof paths."""
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

from axiom.graph_affine import AffineGraphConjecture
from axiom.graph_affine_lean_n3 import run_affine_kernel
from axiom.graph_claims import digest
from axiom.graph_proof import audit
from axiom.graph_relations import AffineRelation
from axiom.graph_universal_lean import (
    PINNED_MATHLIB_SHA, VERIFIED, audit_universal_proof, build_universal_source,
)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def legacy(statement, premise_dir):
    start = perf_counter()
    result = None
    if statement["bound"]["schema"] == AffineGraphConjecture.schema:
        result = build_universal_source(statement)
        status = "SUPPORTED" if result else "UNSUPPORTED_RELATION"
    else:
        status = "UNSUPPORTED_LEGACY_GRAMMAR"
    elapsed = perf_counter() - start
    if result is not None:
        record = run_affine_kernel(result, ".", 180, VERIFIED,
                                   expected_mathlib_revision=PINNED_MATHLIB_SHA, retain_logs=True)
        audit_universal_proof(record)
        status = record["status"]
        write_json(premise_dir / "legacy.json", record)
        (premise_dir / "legacy.lean").write_text(result["source"], encoding="utf-8")
    return {"status": status, "matcher_seconds": elapsed,
            "kernel_seconds": record["duration_seconds"] if result is not None else None}


def check_small_graphs(claim):
    from axiom.graph_affine import check_conjecture
    from axiom.graph_campaign import _discovery_properties
    from axiom.graph_checker import reference_properties
    from axiom.graph_model import edge_positions

    violations = 0
    for order in range(6):
        for mask in range(1 << len(edge_positions(order))):
            reference = reference_properties(order, mask)
            discovery = _discovery_properties(order, mask)
            for side in claim.inequalities():
                applies, valid, value = check_conjecture(side, reference)
                if (applies, valid, value) != check_conjecture(side, discovery):
                    raise AssertionError("independent bounded graph oracles disagree")
                if applies and not valid:
                    violations += 1
                    break
    return violations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    suite = Path("research/proof_engine/targets.json")
    rows, failures = [], []
    for name, premise, weights, rhs, operator, expected in json.loads(suite.read_text()):
        case = out / name
        case.mkdir(exist_ok=True)
        claim = AffineRelation.normalized(weights, rhs, premise, operator)
        input_path, output_path, source = (case / filename for filename in
                                          ("statement.json", "attempt.json", "proof.lean"))
        write_json(input_path, claim.to_dict())
        old = legacy(claim.to_dict(), case)
        subprocess.run([sys.executable, "-m", "axiom", "graph-prove", str(input_path),
                        "--project-root", ".", "--output", str(output_path), "--source", str(source)],
                       check=True)
        attempt = json.loads(output_path.read_text(encoding="utf-8"))
        if attempt["generated"] is not None:
            assert source.read_text(encoding="utf-8") == attempt["generated"]["source"]
        audit(attempt)
        if attempt["kernel"]:
            for stream in ("stdout", "stderr"):
                log = attempt["kernel"][stream]
                if log is not None:
                    (case / (stream + ".log")).write_text(log, encoding="utf-8")
        violations = check_small_graphs(claim)
        rows.append({"name": name, "premise": premise, "weights": weights, "rhs": rhs,
                     "operator": operator, "legacy": old, "status": attempt["status"],
                     "reason": attempt["reason"], "derivation": attempt["derivation"],
                     "counterexample": attempt["counterexample"], "scope": attempt["scope"],
                     "axioms": attempt["kernel"]["axioms"] if attempt["kernel"] else None,
                     "search_seconds": attempt["search_elapsed_seconds"],
                     "kernel_seconds": attempt["kernel"]["duration_seconds"] if attempt["kernel"] else None,
                     "small_graph_violations": violations, "attempt_sha256": attempt["record_sha256"]})
        target_status = {"proof": VERIFIED, "witness": "COUNTEREXAMPLE", "exhausted": "SEARCH_EXHAUSTED"}
        if attempt["status"] != target_status[expected] or (violations > 0) != (expected == "witness"):
            failures.append(name)
        if name.startswith("P") and (
            not attempt["derivation"] or len(attempt["derivation"]["directions"][0]["lemmas"] or ())
            < (3 if name == "P6" else 2)
        ):
            failures.append(name + " composition depth")
        print(f"{name}: {old['status']} -> {attempt['status']}", flush=True)
    old_counts = Counter(row["legacy"]["status"] for row in rows)
    new_counts = Counter(row["status"] for row in rows)
    if new_counts[VERIFIED] <= old_counts[VERIFIED]:
        failures.append("no positive capability delta")
    search_times = [row["search_seconds"] for row in rows]
    matcher_times = [row["legacy"]["matcher_seconds"] for row in rows]
    lean_version = subprocess.run(["lake", "env", "lean", "--version"], capture_output=True, text=True)
    cpu = platform.processor()
    if Path("/proc/cpuinfo").is_file():
        cpu = next((line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")), cpu)
    write_json(out / "benchmark.json", {
        "schema": "axiom.graph_proof_benchmark.v1", "target_suite_sha256": sha256(suite.read_bytes()).hexdigest(),
        "runtime": {"os": platform.platform(), "python": platform.python_version(),
                    "cpu": cpu, "logical_cpus": os.cpu_count(), "lean": lean_version.stdout.strip(),
                    "mathlib": PINNED_MATHLIB_SHA},
        "cases": rows, "attempts_per_engine": len(rows), "legacy_counts": dict(old_counts),
        "composition_counts": dict(new_counts), "certified_delta": new_counts[VERIFIED] - old_counts[VERIFIED],
        "search_with_witness_precheck_seconds": {"median": median(search_times), "worst": max(search_times),
                                                "attempts_per_second": len(rows) / sum(search_times)},
        "legacy_matcher_only_seconds": {"median": median(matcher_times), "worst": max(matcher_times)},
        "timing_scope": "new search includes witness scan; legacy measures dispatch only",
        "search_limits": attempt["search_limits"], "witness_order_limit": attempt["witness_order_limit"],
        "failures": failures, "mathematical_novelty": "NOT_ASSESSED", "cases_sha256": digest(rows),
    })
    if failures:
        raise SystemExit("Benchmark gate failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
