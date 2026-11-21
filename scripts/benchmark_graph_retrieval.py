"""Compare fixed-bank and Mathlib retrieval modes on separate composite goals."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from axiom.graph_proof import audit
from axiom.graph_relations import AffineRelation
from benchmark_graph_proof import check_small_graphs, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suite = root / "research/proof_engine/retrieval_targets.json"
    counts = {"fixed": Counter(), "retrieval": Counter()}
    cases = []
    failures = []
    for name, premise, weights, rhs, adapter in json.loads(suite.read_text(encoding="utf-8")):
        case = args.output / name
        case.mkdir(parents=True, exist_ok=True)
        claim = AffineRelation.normalized(weights, rhs, premise)
        statement = case / "statement.json"
        write_json(statement, claim.to_dict())
        outcomes = {}
        for mode, limit in (("fixed", 0), ("retrieval", 1)):
            output, source = case / (mode + ".json"), case / (mode + ".lean")
            subprocess.run([sys.executable, "-m", "axiom", "graph-prove", str(statement),
                            "--project-root", str(root), "--retrieve-lemmas", str(limit),
                            "--output", str(output), "--source", str(source)], check=True)
            record = json.loads(output.read_text(encoding="utf-8"))
            audit(record)
            if record["generated"] is not None:
                assert source.read_text(encoding="utf-8") == record["generated"]["source"]
            outcomes[mode] = record["status"]
            counts[mode][record["status"]] += 1
        selected = record["retrieval"]["selected"]
        violations = check_small_graphs(claim)
        cases.append({"name": name, "outcomes": outcomes, "retrieved": selected,
                      "small_graph_violations": violations})
        expected = {"fixed": "SEARCH_EXHAUSTED", "retrieval": "FORMALLY_VERIFIED"}
        if (outcomes != expected or violations
                or [x["adapter"] for x in selected] != ["retrieved_" + adapter]):
            failures.append(name)
        print(f"{name}: {outcomes['fixed']} -> {outcomes['retrieval']}", flush=True)
    write_json(args.output / "summary.json", {
        "schema": "axiom.graph_retrieval_benchmark.v1",
        "targets_sha256": sha256(suite.read_bytes()).hexdigest(),
        "counts": counts, "cases": cases, "failures": failures,
        "scope": "curated Mathlib index and fixed composite evaluation goals",
    })
    if failures:
        raise SystemExit("Retrieval regression: " + ", ".join(failures))


if __name__ == "__main__":
    main()
