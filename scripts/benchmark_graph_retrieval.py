"""Compare graph proof fallbacks on separate frozen composite goals."""
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
    fallback = parser.add_mutually_exclusive_group()
    fallback.add_argument("--synthesis", action="store_true",
                          help="compare retrieval alone with retrieval plus projection")
    fallback.add_argument("--order-split", action="store_true",
                          help="compare retrieval and projection with and without case splitting")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.order_split:
        suite = root / "research/proof_engine/order_split_targets.json"
        modes = {"synthesis": (5, 3, False), "order_split": (5, 3, True)}
        schema = "axiom.graph_order_split_benchmark.v1"
        scope = "zero and positive graph order on frozen evaluation goals"
    elif args.synthesis:
        suite = root / "research/proof_engine/synthesis_targets.json"
        modes = {"retrieval": (5, 0, False), "synthesis": (5, 3, False)}
        schema = "axiom.graph_synthesis_benchmark.v1"
        scope = "one-step affine projection and frozen composite evaluation goals"
    else:
        suite = root / "research/proof_engine/retrieval_targets.json"
        modes = {"fixed": (0, 0, False), "retrieval": (1, 0, False)}
        schema = "axiom.graph_retrieval_benchmark.v1"
        scope = "curated Mathlib index and fixed composite evaluation goals"
    baseline, upgraded = modes
    counts = {mode: Counter() for mode in modes}
    cases = []
    failures = []
    for name, premise, weights, rhs, expected_selection in json.loads(suite.read_text(encoding="utf-8")):
        case = args.output / name
        case.mkdir(parents=True, exist_ok=True)
        claim = AffineRelation.normalized(weights, rhs, premise)
        statement = case / "statement.json"
        write_json(statement, claim.to_dict())
        outcomes = {}
        for mode, (retrieve_limit, synthesize_limit, split_order) in modes.items():
            output, source = case / (mode + ".json"), case / (mode + ".lean")
            subprocess.run([sys.executable, "-m", "axiom", "graph-prove", str(statement),
                            "--project-root", str(root), "--retrieve-lemmas", str(retrieve_limit),
                            "--synthesize-lemmas", str(synthesize_limit),
                            "--output", str(output), "--source", str(source),
                            *(["--split-order"] if split_order else [])], check=True)
            record = json.loads(output.read_text(encoding="utf-8"))
            audit(record)
            if record["generated"] is not None:
                assert source.read_text(encoding="utf-8") == record["generated"]["source"]
            outcomes[mode] = record["status"]
            counts[mode][record["status"]] += 1
        if args.order_split:
            split = record["order_split"]
            selection_ok = split["attempted"] and expected_selection in split["positive_facts"]
            evidence = {"order_split": split}
        elif args.synthesis:
            selected = record["synthesis"]["selected"]
            used = {lemma["theorem"] for direction in (record["derivation"] or {}).get("directions", ())
                    for lemma in direction["lemmas"] or ()}
            selection_ok = any(step["pivot"] == expected_selection and step["lemma"]["theorem"] in used
                               for step in selected)
            evidence = {"synthesized": selected}
        else:
            selected = record["retrieval"]["selected"]
            selection_ok = [x["adapter"] for x in selected] == ["retrieved_" + expected_selection]
            evidence = {"retrieved": selected}
        violations = check_small_graphs(claim)
        cases.append({"name": name, "outcomes": outcomes, **evidence,
                      "small_graph_violations": violations})
        expected = {baseline: "SEARCH_EXHAUSTED", upgraded: "FORMALLY_VERIFIED"}
        if outcomes != expected or violations or not selection_ok:
            failures.append(name)
        print(f"{name}: {outcomes[baseline]} -> {outcomes[upgraded]}", flush=True)
    write_json(args.output / "summary.json", {
        "schema": schema,
        "targets_sha256": sha256(suite.read_bytes()).hexdigest(),
        "counts": counts, "cases": cases, "failures": failures,
        "scope": scope,
    })
    if failures:
        raise SystemExit("Proof fallback regression: " + ", ".join(failures))


if __name__ == "__main__":
    main()
