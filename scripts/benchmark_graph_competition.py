"""Replay the frozen v7 proof suite or compare exact implication with CPU controls."""
import argparse
from collections import Counter
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from axiom.graph_lemma_retrieval import (
    PALETTE_INDEX, CERTIFICATE_INDEX, CLIQUE_INDEPENDENCE_INDEX, DECOMPOSITION_INDEX, SCHEDULED_INDEX,
)
from axiom.graph_novelty import PROFILE, PROFILES, NoveltyFilter, entails, fact_bank
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation, _vector

from benchmark_graph_proof import check_small_graphs, write_json

ROOT = Path(__file__).resolve().parents[1]
SUITES = ROOT / "research" / "autographforge"
ALIAS = {"n": "n", "edges": "m", "triangles": "tri", "independence": "alpha", "clique": "omega",
         "chromatic": "chi", "maximum_degree": "Delta", "matching": "nu", "components": "components"}


def read(name):
    return json.loads((SUITES / name).read_bytes())


def load_upstream(path):
    pin = read("baseline-v7.json")["competitor"]["upstream_snapshot"]
    sha = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if sha != pin:
        raise ValueError("upstream repository is not at the frozen comparator revision")
    sys.path.insert(0, str(path))
    from conjecture import Conjecture, Inequality
    from pipeline import novelty

    # The common scope includes order zero. Use the same nonnegative lower
    # bounds while leaving all upstream relation rows and solver code intact.
    novelty.LOWER_BOUNDS = dict.fromkeys(novelty.LOWER_BOUNDS, 0.0)

    def classify(claim):
        details = []
        for side in claim.inequalities():
            leads = [(name, weight) for name, weight in side.terms if weight > 0]
            if not leads:
                details.append({"status": "UNSUPPORTED", "reason": "no positive leading invariant"})
                continue
            evidence = []
            for name, weight in leads:
                other = [(-value, ALIAS[symbol]) for symbol, value in side.terms if symbol != name]
                first, *extra = other or [(0, ALIAS[name])]
                assumption = None if side.assumption == "ALL" else side.assumption.lower()
                ineq = Inequality(ALIAS[name], first[1], coeff_a=weight, coeff_b=first[0],
                                  offset=side.upper, extra_terms=extra, hypothesis=assumption)
                known, why = novelty.classify(Conjecture(statement="", inequality=ineq))
                if known:
                    evidence.append(why)
            details.append({"status": "KNOWN" if evidence else "UNKNOWN", "matches": evidence})
        statuses = {row["status"] for row in details}
        return {"status": "KNOWN" if statuses == {"KNOWN"} else
                "UNSUPPORTED" if "UNSUPPORTED" in statuses else "UNKNOWN", "directions": details}

    return classify


def lp_control(claim, *, profile=PROFILE):
    from scipy.optimize import linprog

    for side in claim.inequalities():
        rows = [row for row in fact_bank(profile)[0].values() if entails(side.assumption, row.premise)]
        result = linprog([0] * len(rows), A_eq=list(zip(*(row.vector for row in rows))),
                         b_eq=_vector(side.terms), A_ub=[[row.rhs for row in rows]], b_ub=[side.upper],
                         method="highs-ds", options={"maxiter": 1000})
        if not result.success:
            return "UNKNOWN"
    return "NUMERICALLY_FEASIBLE"


def controls(output, upstream, profile=PROFILE):
    agf = load_upstream(upstream)
    axiom = NoveltyFilter(profile=profile)
    raw_lp = partial(lp_control, profile=profile)
    cases = []
    for ident, assumption, weights, rhs, op in read("implication-v1.json")["cases"]:
        claim = AffineRelation.normalized(weights, rhs, assumption, op)
        timings = {}
        result = {"id": ident, "claim_id": claim.id}
        for name, engine in (("axiom", axiom.classify), ("raw_lp", raw_lp), ("autographforge", agf)):
            start = perf_counter()
            result[name] = engine(claim)
            timings[name] = perf_counter() - start
        cases.append({**result, "seconds": timings})
    expected = read("implication-v1-expected.json")
    stats = {}
    for name, positive in (("axiom", True), ("raw_lp", "NUMERICALLY_FEASIBLE"), ("autographforge", "KNOWN")):
        score = {case["id"]: case[name]["status"] if name == "autographforge" else case[name] for case in cases}
        stats[name] = {"known": sum(score[ident] == positive for ident in expected["known"]),
                       "false_positives": [ident for ident in expected["false_witnesses"] if score[ident] == positive],
                       "statuses": dict(Counter(score.values()))}
    write_json(output, {"scope": "development implication fixture; upstream low-level classifier only",
                        "cases": cases, "stats": stats, "exact_certificates": axiom.report()})
    print(stats)


def proofs(output, *, retrieval_index=CLIQUE_INDEPENDENCE_INDEX):
    path = SUITES / "heldout-proof-v1.json"
    frozen = read("baseline-v7.json")["frozen_holdouts"][path.name]["sha256"]
    if sha256(path.read_bytes()).hexdigest() != frozen:
        raise ValueError("proof regression suite differs from its frozen content")
    output.mkdir()
    outcomes = Counter()
    for case, premise, weights, rhs, op, _ in read(path.name):
        claim = AffineRelation.normalized(weights, rhs, premise, op)
        attempt = prove(claim.to_dict(), timeout=45, witness_order=5, project_root=ROOT,
                        retrieval_index=retrieval_index, retrieval_limit=5,
                        synthesis_limit=3, split_order=True, induct_edges=True, plan_limit=16)
        verified = audit(attempt)
        violations = check_small_graphs(claim)
        status = attempt["status"]
        if (status == "COUNTEREXAMPLE") != bool(violations):
            raise ValueError(f"independent witness disagreement on {case}")
        if status == "FORMALLY_VERIFIED" and not attempt["kernel"]["lean_kernel_executed"]:
            raise ValueError(f"missing Lean execution on {case}")
        outcomes[status] += 1
        write_json(output / f"{case}.json", {"attempt": attempt, "audit": verified,
                                           "independent_violations": violations})
        print(case, status, flush=True)
    write_json(output / "summary.json", dict(outcomes))
    if outcomes != {"FORMALLY_VERIFIED": 22, "COUNTEREXAMPLE": 10}:
        raise ValueError("outcome differs from the preserved proof regression count")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--autographforge", type=Path)
    proof_indexes = {
        "v7": CLIQUE_INDEPENDENCE_INDEX,
        "v9": DECOMPOSITION_INDEX,
        "v10": SCHEDULED_INDEX,
        "v12": PALETTE_INDEX, "v11": CERTIFICATE_INDEX,
    }
    parser.add_argument("--proof-index", choices=proof_indexes, default="v7",
                        help="retrieval index for the same frozen 32-case proof regression")
    parser.add_argument("--novelty-profile", choices=PROFILES, default=PROFILE)
    args = parser.parse_args()
    if args.autographforge:
        controls(args.output, args.autographforge.resolve(), args.novelty_profile)
    else:
        proofs(args.output, retrieval_index=proof_indexes[args.proof_index])


if __name__ == "__main__":
    main()
