"""AXIOM v0.18: reproducible compositional graph conjecture synthesis.

Discovers new affine inequality *statements* over eight integer graph
invariants. Full source replay precedes all computation; n5 and bounded n6
and historical n7 graph samples are discovery-only. A fresh n7 holdout is
allocated AFTER ranking, kept disjoint from every previously tested n7
source mask and from other holdout candidates, and cannot affect selection.

A surviving universal-quantified statement is ONLY a bounded survivor.
No Lean syntax generator exists for this richer grammar yet. Surviving
statements are recorded as OPEN Lean proof obligations, never promoted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, product
import hashlib
import json
import os
from pathlib import Path

from .graph_adaptive import _historical
from .graph_affine import (
    AffineGraphConjecture, INVARIANTS, ASSUMPTIONS,
    applicable, check_conjecture,
)
from .graph_campaign import _discovery_properties
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_model import SimpleGraph, edge_positions
from .graph_nonduplicate import _novel_masks
from .graph_research_cycle import _tasks

SCHEMA = "axiom.graph_affine_synthesis.v1"
POLICY = "source_trained_multiscale_affine_holdout_v1"


def _config(seed: int, n6_training: int, n7_training: int,
            holdout_budget: int, max_candidates: int) -> dict:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if type(n6_training) is not int or not 16 <= n6_training <= 256:
        raise ValueError("n6_training must be 16..256")
    if type(n7_training) is not int or not 16 <= n7_training <= 256:
        raise ValueError("n7_training must be 16..256")
    if type(holdout_budget) is not int or not 8 <= holdout_budget <= 256:
        raise ValueError("holdout_budget must be 8..256")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 8:
        raise ValueError("max_candidates must be 1..8")
    return {
        "seed": seed, "n6_training": n6_training,
        "n7_training": n7_training,
        "holdout_budget": holdout_budget, "max_candidates": max_candidates,
    }


def _bounded_masks(n: int, seed: int, budget: int) -> list[int]:
    if n != 6 or type(seed) is not int or type(budget) is not int:
        raise ValueError("unsupported bounded graph training order")
    total = 1 << len(edge_positions(n))
    selected, seen, index = [], set(), 0
    while len(selected) < budget:
        encoded = f"AXIOM-v018-n6-training:{seed}:{index}".encode("ascii")
        mask = int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % total
        index += 1
        if mask not in seen:
            selected.append(mask)
            seen.add(mask)
    return selected


def _choose_historical(masks: set[int], seed: int, budget: int) -> list[int]:
    if len(masks) < budget:
        raise ValueError("not enough historical order-seven graphs for training")
    return sorted(masks, key=lambda m: (
        hashlib.sha256(f"AXIOM-v018-historical:{seed}:{m}".encode("ascii")).digest(),
        m))[:budget]


def _data(masks: dict[int, list[int]]) -> tuple[dict[int, list[dict]], dict]:
    data: dict[int, list[dict]] = {}
    sample_hashes = {}
    for n in (5, 6, 7):
        group = masks[n]
        if len(group) != len(set(group)):
            raise ValueError("duplicate labelled graph in discovery corpus")
        data[n] = [reference_properties(n, mask) for mask in group]
        sample_hashes[str(n)] = {
            "graphs": len(group),
            "mask_sha256": digest(group),
            "scope": "ALL_LABELLED_GRAPHS_EXACT_N" if n == 5 else
                     "BOUNDED_LABELLED_GRAPHS_ONLY",
        }
    return data, sample_hashes


def _known_heuristic(stmt: AffineGraphConjecture) -> bool:
    """Known elementary inequalities are deferred; no local proof is claimed."""
    if stmt.assumption != "ALL":
        return False
    known = (
        ({"independence": 1, "clique": 1, "n": -1}, 1),
        ({"clique": 1, "chromatic": -1}, 0),
        ({"chromatic": 1, "maximum_degree": -1}, 1),
        ({"matching": 2, "n": -1}, 0),
        ({"maximum_degree": 1, "n": -1}, -1),
    )
    for terms, bound in known:
        if (dict(stmt.terms) == terms and stmt.upper == bound):
            return True
    return False


def _derive(training: dict[int, list[dict]]) -> tuple[list[dict], dict]:
    """Synthesize sparse affine bounds and reject marginally dominated ones.

    Candidate upper bounds are fitted ONLY to discovery data. Holdout data
    does not exist yet at this stage. For each assumption and each pair of
    invariants, compare the observed joint maximum with the independent
    marginal-max envelope over the SAME n and assumption group.
    """
    dedup: dict[str, dict] = {}
    counts = Counter()
    weights = (-2, -1, 1, 2)
    for assumption in ASSUMPTIONS:
        filtered = {
            n: [p for p in training[n] if applicable(assumption, p)]
            for n in (5, 6, 7)
        }
        if any(not filtered[n] for n in (5, 6, 7)):
            counts["NO_ANTECEDENT_AT_SOME_ORDER"] += 1
            continue
        for x, y in combinations(INVARIANTS, 2):
            for a, b, n_coeff in product(weights, weights, (-1, 0, 1)):
                raw_by_order = {
                    n: [a * p[x] + b * p[y] + n_coeff * n
                        for p in filtered[n]]
                    for n in (5, 6, 7)
                }
                maximum = max(max(raw_by_order[n]) for n in (5, 6, 7))
                if abs(maximum) > 256:
                    counts["TOO_LARGE_OR_TOO_SMALL_BOUND"] += 1
                    continue
                terms = {x: a, y: b}
                if n_coeff:
                    terms["n"] = n_coeff
                stmt = AffineGraphConjecture.normalized(terms, maximum, assumption)
                # Check exact canonical statement rather than a float proxy.
                tighter = set()
                support = {}
                for n in (5, 6, 7):
                    sat = sum(value == maximum for value in raw_by_order[n])
                    support[str(n)] = {
                        "applicable_graphs": len(filtered[n]),
                        "tight_graphs": sat,
                    }
                    if sat:
                        tighter.add(n)
                if len(tighter) < 2:
                    counts["NOT_CROSS_ORDER_TIGHT"] += 1
                    continue
                marginal = max(
                    max(a * p[x] for p in filtered[n])
                    + max(b * p[y] for p in filtered[n])
                    + n_coeff * n
                    for n in (5, 6, 7)
                )
                if marginal <= maximum:
                    counts["MARGINALLY_DOMINATED"] += 1
                    continue
                if _known_heuristic(stmt):
                    counts["KNOWN_ELEMENTARY_DEFERRAL"] += 1
                    continue
                margin = marginal - maximum
                # This is a *subjective compute-allocation ranking*, NOT a
                # mathematical truth probability or novelty assessment.
                score = (len(tighter) * 10000 + min(100, margin) * 20
                         + min(99, sum(v["tight_graphs"] for v in support.values()))
                         - 3 * sum(abs(coef) for _, coef in stmt.terms))
                candidate = {
                    "candidate_id": stmt.id,
                    "statement": stmt.to_dict(),
                    "selection_score": score,
                    "observed_joint_maximum": maximum,
                    "independent_marginal_envelope": marginal,
                    "observed_correlation_margin": margin,
                    "source_training_support": support,
                    "tight_source_orders": sorted(tighter),
                    "statement_is_a_proved_theorem": False,
                    "mathematical_novelty": "NOT_ASSESSED",
                }
                prev = dedup.get(stmt.id)
                if prev is None or (
                    candidate["selection_score"],
                    candidate["observed_correlation_margin"]
                ) > (
                    prev["selection_score"],
                    prev["observed_correlation_margin"]
                ):
                    dedup[stmt.id] = candidate
    ranked = sorted(dedup.values(), key=lambda item: (
        -item["selection_score"], item["candidate_id"]))
    counts["DEDUPED_CANDIDATES"] = len(ranked)
    return ranked, dict(sorted(counts.items()))


def _shortlist(bank: list[dict], quota: int) -> list[dict]:
    """Diversify among invariant pairs, not only near-duplicate coefficients."""
    selected = []
    pairs = set()
    for candidate in bank:
        stmt = AffineGraphConjecture.from_dict(candidate["statement"])
        pair = tuple(symbol for symbol, _ in stmt.terms if symbol != "n")
        if pair in pairs:
            continue
        pairs.add(pair)
        selected.append(candidate)
        if len(selected) == quota:
            break
    return selected


def _witness(stmt: AffineGraphConjecture, n: int, mask: int) -> dict:
    p = reference_properties(n, mask)
    applies, valid, value = check_conjecture(stmt, p)
    if not applies or valid:
        raise ValueError("candidate witness is not a mathematical refutation")
    independent = _discovery_properties(n, mask)
    d_applies, d_valid, d_value = check_conjecture(stmt, independent)
    if not d_applies or d_valid or d_value != value:
        raise ValueError("independent graph-invariant engines disagree")
    return {
        "graph": SimpleGraph.from_mask(n, mask).to_dict(),
        "exact_order": n,
        "labelled_edge_mask": mask,
        "left_hand_side": value,
        "right_hand_side": stmt.upper,
        "independent_witness_check": "ACCEPTED_BOTH_GRAPH_ORACLES",
    }


def _holdout(candidate: dict, source_fp: str, masks: list[int]) -> dict:
    stmt = AffineGraphConjecture.from_dict(candidate["statement"])
    examined = []
    applicable_count = 0
    counterexample = None
    for mask in masks:
        applies, valid, _ = check_conjecture(stmt, reference_properties(7, mask))
        examined.append(mask)
        if applies:
            applicable_count += 1
            if not valid:
                counterexample = _witness(stmt, 7, mask)
                break
    return {
        "candidate_id": candidate["candidate_id"],
        "statement": candidate["statement"],
        "source_fingerprint": source_fp,
        "scope": "n=7 labelled simple graphs; bounded held-out experiment only",
        "allocated_holdout": len(masks),
        "masks_checked": examined,
        "graphs_checked": len(examined),
        "assumption_satisfying_graphs": applicable_count,
        "status": ("REFUTED_ON_HOLDOUT" if counterexample is not None
                   else "INCONCLUSIVE_NO_ANTECEDENT_COVERAGE"
                   if applicable_count == 0 else "SURVIVED_BOUNDED_HOLDOUT"),
        "counterexample": counterexample,
        "lean_kernel_ran": False,
        "theorem_status": "NOT_PROVED",
    }


def synthesize(db_path: str, *, seed: int = 42, n6_training: int = 64,
               n7_training: int = 64, holdout_budget: int = 32,
               max_candidates: int = 4) -> dict:
    cfg = _config(seed, n6_training, n7_training,
                  holdout_budget, max_candidates)
    source_fp, _ = _tasks(db_path, 7)  # Full independent historical source replay.
    historical, _, _, _ = _historical(db_path)
    masks = {
        5: list(range(1 << len(edge_positions(5)))),  # genuinely exhaustive n5
        6: _bounded_masks(6, seed, n6_training),
        7: _choose_historical(historical, seed, n7_training),
    }
    training, training_meta = _data(masks)
    ranked, filter_counts = _derive(training)
    selected = _shortlist(ranked, max_candidates)

    # Holdout graphs are chosen only AFTER statement generation and ranking.
    # The same labelled graph is never tested twice in this entire campaign.
    excluded = set(historical)
    heldout = []
    for item in selected:
        available = _novel_masks(item["candidate_id"], seed, 0,
                                 holdout_budget, excluded)
        if set(available) & excluded:
            raise ValueError("a holdout graph leaked into source/training or earlier holdout")
        trial = _holdout(item, source_fp, available)
        if not set(trial["masks_checked"]).issubset(set(available)):
            raise ValueError("holdout evidence contains an unallocated graph")
        excluded.update(trial["masks_checked"])
        heldout.append(trial)

    return {
        "schema": SCHEMA,
        "selection_policy": POLICY,
        "configuration": cfg,
        "source_fingerprint": source_fp,
        "quantification": "all finite simple graphs (unproven conjectures)",
        "training": {
            "cohorts": training_meta,
            "n7_sample_is_from_audited_historical_sources": True,
            "historical_n7_distinct_masks": len(historical),
            "historical_n7_mask_sha256": digest(sorted(historical)),
        },
        "synthesis": {
            "raw_filtered_counts": filter_counts,
            "canonical_candidates_generated": len(ranked),
            "candidate_bank_sha256": digest(ranked),
            "candidate_bank_top20": ranked[:20],
            "selected": selected,
        },
        "holdout": {
            "policy": "source-disjoint_and_intercandidate-disjoint_exact_n7_masks",
            "experiments": heldout,
            "distinct_graphs_checked": sum(x["graphs_checked"] for x in heldout),
            "refutations": sum(x["status"] == "REFUTED_ON_HOLDOUT" for x in heldout),
            "survivals": sum(
                x["status"] == "SURVIVED_BOUNDED_HOLDOUT" for x in heldout),
            "inconclusive": sum(
                x["status"] == "INCONCLUSIVE_NO_ANTECEDENT_COVERAGE"
                for x in heldout),
            "selection_used_holdout_data": False,
        },
        "lean_handoff": [{
            "candidate_id": trial["candidate_id"],
            "statement": trial["statement"],
            "state": "PENDING_AFFINE_TO_LEAN_TRANSLATION",
            "requires_real_kernel_execution": True,
            "proof_available": False,
            "lean_formal_verification": "NOT_PERFORMED",
        } for trial in heldout if trial["status"] == "SURVIVED_BOUNDED_HOLDOUT"],
        "formal_lean_kernel_executed": False,
        "theorem_promotions": 0,
        "generalization_proved": False,
        "mathematical_novelty": "NOT_ASSESSED",
        "source_evidence_modified": False,
        "negative_results_preserved": True,
    }


def save_synthesis(db_path: str, output: str, *, seed: int = 42,
                   n6_training: int = 64, n7_training: int = 64,
                   holdout_budget: int = 32, max_candidates: int = 4) -> dict:
    cfg = _config(seed, n6_training, n7_training,
                  holdout_budget, max_candidates)
    target = Path(output)
    if target.exists():
        existing = audit_synthesis(db_path, output)["report"]
        if existing["configuration"] != cfg:
            raise ValueError("immutable research synthesis already exists with different parameters")
        return existing
    report = synthesize(db_path, **cfg)
    target.parent.mkdir(parents=True, exist_ok=True)
    buf = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as output_stream:
        output_stream.write(buf)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    return report


def audit_synthesis(db_path: str, report_path: str) -> dict:
    path = Path(report_path)
    if not path.is_file() or path.stat().st_size > 3_000_000:
        raise ValueError("missing or oversized graph synthesis evidence")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if type(loaded) is not dict or loaded.get("schema") != SCHEMA:
        raise ValueError("unknown graph synthesis schema")
    cfg = loaded.get("configuration")
    if type(cfg) is not dict or set(cfg) != {
        "seed", "n6_training", "n7_training", "holdout_budget",
        "max_candidates",
    }:
        raise ValueError("invalid graph synthesis configuration")
    expected = synthesize(db_path, **cfg)  # Independently rechecks all source records.
    if stable(expected) != stable(loaded):
        raise ValueError("graph synthesis differs from independent deterministic replay")
    return {
        "audit": "ACCEPTED_ALL_SOURCE_AND_HOLDOUT_REPLAY",
        "source_fingerprint": expected["source_fingerprint"],
        "candidate_count": expected["synthesis"]["canonical_candidates_generated"],
        "holdout_graphs": expected["holdout"]["distinct_graphs_checked"],
        "refutations": expected["holdout"]["refutations"],
        "survivals": expected["holdout"]["survivals"],
        "proofs_promoted": 0,
        "lean_executed": False,
        "report": expected,
    }
