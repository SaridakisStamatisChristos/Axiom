"""AXIOM v0.19 — premise-aware *bounded* follow-up experiments.

This adds a new, immutable, audited lane alongside the v0.18 holdout; it does
not alter historical research or reclassify any finite observation as a proof.

The generator is explicitly STRATIFIED and NOT uniform over all graphs that
satisfy each assumption. In particular, the BIPARTITE stratum constructs a
random partition and a random subset of cross-edges, introducing bias.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .graph_adaptive import _historical
from .graph_affine import AffineGraphConjecture, applicable, check_conjecture
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_model import edge_positions
from .graph_nonduplicate import _novel_masks
from .graph_synthesis import audit_synthesis, _witness

SCHEMA = "axiom.graph_assumption_holdout.v1"
METHOD = "EXPLICIT_ASSUMPTION_STRATA_NONUNIFORM_V1"
N = 7
SPACE = 1 << len(edge_positions(N))
PAIRS = edge_positions(N)


def _configuration(seed: int, budget: int, max_proposals: int) -> dict:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if type(budget) is not int or not 1 <= budget <= 256:
        raise ValueError("budget must be 1..256")
    if type(max_proposals) is not int or not budget <= max_proposals <= 50000:
        raise ValueError("max_proposals must be >= budget and <= 50000")
    return {"seed": seed, "budget": budget, "max_proposals": max_proposals}


def _digest_int(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("ascii")).digest(), "big")


def _candidate_mask(candidate_id: str, assumption: str, seed: int,
                    attempt: int) -> int:
    prefix = f"AXIOM-v019:{candidate_id}:{seed}:{attempt}:"
    if assumption == "BIPARTITE":
        # Partition labels into two colour classes; only between-class edges
        # can be selected. This is NOT a uniform labelled bipartite sampler.
        cut = _digest_int(prefix + "partition") & ((1 << N) - 1)
        if cut in (0, (1 << N) - 1):
            cut = 0b1010101
        edge_bits = _digest_int(prefix + "edges")
        mask = 0
        for i, (a, b) in enumerate(PAIRS):
            if ((cut >> a) & 1) != ((cut >> b) & 1):
                if (edge_bits >> i) & 1:
                    mask |= 1 << i
        return mask
    # Full-period labelled space traversal via an odd stride for the
    # unconstrained, connected and triangle-free strata. Premise filtering
    # below is mandatory; no conditional sample is accepted on blind trust.
    raw = hashlib.sha256(
        f"AXIOM-v019:{candidate_id}:{seed}:oddstride".encode("ascii")
    ).digest()
    start = int.from_bytes(raw[:8], "big") % SPACE
    stride = (int.from_bytes(raw[8:16], "big") % (SPACE // 2)) * 2 + 1
    return (start + stride * attempt) % SPACE


def sample_stratum(candidate_id: str, assumption: str, seed: int,
                   budget: int, forbidden: set[int], *,
                   max_proposals: int = 20000) -> tuple[list[int], dict]:
    _configuration(seed, budget, max_proposals)
    if (type(candidate_id) is not str or not candidate_id.startswith("affine-graph:")
            or assumption not in ("ALL", "CONNECTED", "BIPARTITE", "TRIANGLE_FREE")
            or type(forbidden) is not set or
            any(type(x) is not int or not 0 <= x < SPACE for x in forbidden)):
        raise ValueError("malformed typed graph stratum")
    selected, own = [], set()
    rejected_source, rejected_premise, duplicates = 0, 0, 0
    if assumption == "ALL":
        selected = _novel_masks(candidate_id, seed, 19, budget, forbidden)
        proposals = len(selected)
    else:
        proposals = 0
        for attempt in range(max_proposals):
            proposals += 1
            mask = _candidate_mask(candidate_id, assumption, seed, attempt)
            if mask in forbidden:
                rejected_source += 1
                continue
            if mask in own:
                duplicates += 1
                continue
            if not applicable(assumption, reference_properties(N, mask)):
                rejected_premise += 1
                continue
            own.add(mask)
            selected.append(mask)
            if len(selected) == budget:
                break
    assert len(selected) == len(set(selected))
    if set(selected) & forbidden:
        raise ValueError("stratified graph sample reused prior evidence")
    if any(not applicable(assumption, reference_properties(N, mask))
           for mask in selected):
        raise ValueError("stratified graph sampler returned wrong premise")
    return selected, {
        "assumption": assumption, "sampling_method": METHOD,
        "uniform_over_eligible_graphs": False,
        "requested_graphs": budget,
        "accepted_premise_satisfying_graphs": len(selected),
        "proposals_examined": proposals,
        "excluded_previous_graphs": len(forbidden),
        "source_rejections": rejected_source,
        "premise_rejections": rejected_premise,
        "duplicate_proposals": duplicates,
        "exhaustive": False,
        "formal_lean_verified": False,
    }


def _run(db_path: str, v018_report: str, cfg: dict) -> dict:
    original = audit_synthesis(db_path, v018_report)["report"]
    historical, _, _, _ = _historical(db_path)
    original_used = {
        mask for experiment in original["holdout"]["experiments"]
        for mask in experiment["masks_checked"]
    }
    forbidden = set(historical) | original_used
    parent_sha256 = digest(original)
    results = []
    for candidate in original["synthesis"]["selected"]:
        stmt = AffineGraphConjecture.from_dict(candidate["statement"])
        masks, sampling = sample_stratum(
            candidate["candidate_id"], stmt.assumption,
            cfg["seed"], cfg["budget"], forbidden,
            max_proposals=cfg["max_proposals"])
        tested = []
        witness = None
        for mask in masks:
            applies, valid, _ = check_conjecture(
                stmt, reference_properties(N, mask))
            if not applies:
                raise ValueError("selected holdout graph failed its assumption")
            tested.append(mask)
            if not valid:
                witness = _witness(stmt, N, mask)
                break
        forbidden.update(tested)
        result = {
            "candidate_id": candidate["candidate_id"],
            "statement": stmt.to_dict(),
            "sampling": sampling,
            "masks_checked": tested,
            "premise_satisfying_graphs_checked": len(tested),
            "status": (
                "REFUTED_WITH_TWO_INDEPENDENT_ORACLES" if witness is not None
                else "SURVIVED_STRATIFIED_BOUNDED_HOLDOUT"
                if tested else "INCONCLUSIVE_NO_PREMISE_GRAPHS_OBTAINED"),
            "counterexample": witness,
            "all_graph_orders_proved": False,
            "lean_kernel_executed": False,
        }
        results.append(result)
    return {
        "schema": SCHEMA, "sampling_method": METHOD, "configuration": cfg,
        "parent_report_sha256": parent_sha256,
        "historical_source_fingerprint": original["source_fingerprint"],
        "historical_labelled_masks_excluded": len(historical),
        "v018_holdout_masks_excluded": len(original_used),
        "results": results,
        "new_distinct_masks_checked": sum(
            len(result["masks_checked"]) for result in results),
        "independently_verified_counterexamples": sum(
            result["counterexample"] is not None for result in results),
        "all_order_generalization": "NOT_PROVED",
        "formal_lean_verification": "NOT_PERFORMED",
        "nonuniform_conditional_sampling": True,
        "historical_evidence_modified": False,
        "new_theorems_proved": 0,
    }


def followup(db_path: str, v018_report: str, *, seed: int = 43,
             budget: int = 24, max_proposals: int = 20000) -> dict:
    cfg = _configuration(seed, budget, max_proposals)
    return _run(db_path, v018_report, cfg)


def save_followup(db_path: str, v018_report: str, output: str, *,
                  seed: int = 43, budget: int = 24,
                  max_proposals: int = 20000) -> dict:
    cfg = _configuration(seed, budget, max_proposals)
    path = Path(output)
    if path.exists():
        prev = audit_followup(db_path, v018_report, output)["report"]
        if cfg != prev["configuration"]:
            raise ValueError("cannot overwrite immutable premise-aware experiment")
        return prev
    report = _run(db_path, v018_report, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_EXCL | os.O_CREAT | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return report


def audit_followup(db_path: str, v018_report: str, evidence_file: str) -> dict:
    path = Path(evidence_file)
    if not path.is_file() or path.stat().st_size > 3_000_000:
        raise ValueError("missing or oversized premise-aware experiment")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if type(recorded) is not dict or recorded.get("schema") != SCHEMA:
        raise ValueError("unrecognized premise-aware experiment schema")
    cfg = recorded.get("configuration")
    if type(cfg) is not dict or set(cfg) != {
        "seed", "budget", "max_proposals",
    }:
        raise ValueError("unknown premise-aware experiment configuration")
    _configuration(**cfg)
    replay = _run(db_path, v018_report, cfg)
    if stable(recorded) != stable(replay):
        raise ValueError("premise-aware experiment failed deterministic source replay")
    return {
        "audit": "ACCEPTED_FULL_SOURCE_AND_CONDITIONAL_REPLAY",
        "checked_new_graphs": replay["new_distinct_masks_checked"],
        "independent_counterexamples":
            replay["independently_verified_counterexamples"],
        "theorems_proved": 0,
        "report": replay,
    }
