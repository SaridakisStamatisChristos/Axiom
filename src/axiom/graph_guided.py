"""AXIOM v0.19: assumption-aware holdout, independently source-replayed.

This is a separate schema and does NOT revise or overwrite v0.18 experiments.
A deterministic graph constructor guarantees a meaningful holdout for
bipartite, triangle-free and connected antecedents; selection is based only
on fully audited preexisting source graphs. Constructed samples are NOT
uniform random graphs, nor do bounded survivors constitute proofs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .graph_affine import AffineGraphConjecture, check_conjecture
from .graph_adaptive import _historical
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_model import edge_positions
from .graph_research_cycle import _tasks
from .graph_synthesis import (
    _config, _bounded_masks, _choose_historical, _data, _derive,
    _historical_preflight, _witness,
)

SCHEMA = "axiom.graph_guided_synthesis.v1"
SAMPLER = "deterministic_antecedent_construction_nonuniform_v1"
EDGE_INDEX = {pair: i for i, pair in enumerate(edge_positions(7))}
GRAPH_SPACE = 1 << len(EDGE_INDEX)


def _edges_to_mask(edges: list[tuple[int, int]]) -> int:
    return sum(1 << EDGE_INDEX[tuple(sorted(edge))] for edge in edges)


def guided_mask(candidate_id: str, assumption: str, seed: int, index: int) -> int:
    """Construct explicit labelled graphs, not a statistical i.i.d. sample.

    For conditional statements use graph families that satisfy assumptions
    by construction. TRIANGLE_FREE includes odd-cycle families to avoid
    testing bipartite graphs exclusively.
    """
    if type(candidate_id) is not str or not candidate_id.startswith("affine-graph:"):
        raise ValueError("invalid exact candidate identifier")
    if assumption not in ("ALL", "CONNECTED", "BIPARTITE", "TRIANGLE_FREE"):
        raise ValueError("unknown graph assumption")
    if (type(seed) is not int or not 0 <= seed < 2**32
            or type(index) is not int or not 0 <= index < 65536):
        raise ValueError("invalid deterministic graph sampling parameter")
    raw = hashlib.sha256(
        f"AXIOM-GUIDED-v019:{candidate_id}:{seed}:{assumption}:{index}".encode("ascii")
    ).digest()
    bits = int.from_bytes(raw[8:16], "big") & (GRAPH_SPACE - 1)
    if assumption == "ALL":
        return bits
    order = sorted(range(7), key=lambda v: hashlib.sha256(
        raw + bytes([v])).digest())
    if assumption == "CONNECTED":
        path = [tuple(sorted((a, b))) for a, b in zip(order, order[1:])]
        return bits | _edges_to_mask(path)
    if assumption == "TRIANGLE_FREE" and index % 3 == 2:
        # Five-cycle with two isolated vertices: nonbipartite, triangle-free.
        path = order[:5]
        cycle = [(path[j], path[(j + 1) % 5]) for j in range(5)]
        return _edges_to_mask(cycle)
    # Any subset of the cross-partition edges is bipartite and triangle-free.
    cut = 1 + (int.from_bytes(raw[:4], "big") % 126)
    membership = {v for v in range(7) if (cut >> v) & 1}
    cross = [
        (a, b) for a, b in edge_positions(7)
        if (a in membership) != (b in membership)
    ]
    return bits & _edges_to_mask(cross)


def _guided_holdout(candidate: dict, source_fp: str,
                    seed: int, budget: int, excluded: set[int]) -> dict:
    stmt = AffineGraphConjecture.from_dict(candidate["statement"])
    if candidate["candidate_id"] != stmt.id:
        raise ValueError("candidate identity does not match exact statement")
    visited = []
    skip_historical = 0
    skip_duplicates = 0
    local = set()
    witness = None
    for i in range(max(2048, budget * 128)):
        if len(visited) == budget or witness is not None:
            break
        mask = guided_mask(stmt.id, stmt.assumption, seed, i)
        if mask in excluded:
            skip_historical += 1
            continue
        if mask in local:
            skip_duplicates += 1
            continue
        local.add(mask)
        relevant, correct, _ = check_conjecture(
            stmt, reference_properties(7, mask))
        if not relevant:
            raise ValueError("constructed graph violated declared antecedent")
        visited.append(mask)
        if not correct:
            witness = _witness(stmt, 7, mask)
    if not visited:
        raise ValueError("no new assumption-satisfying holdout graph could be allocated")
    status = "REFUTED_ON_GUIDED_HOLDOUT" if witness else (
        "SURVIVED_BOUNDED_GUIDED_HOLDOUT" if len(visited) == budget else
        "INCOMPLETE_GUIDED_SAMPLE_BUDGET")
    return {
        "candidate_id": candidate["candidate_id"],
        "statement": candidate["statement"],
        "source_fingerprint": source_fp,
        "assumption": stmt.assumption,
        "method": SAMPLER,
        "sampling_not_uniform_random": True,
        "labelled_graph_space": GRAPH_SPACE,
        "budget": budget,
        "masks_checked": visited,
        "graphs_checked": len(visited),
        "assumption_satisfying_graphs": len(visited),
        "historical_or_prior_candidate_proposals_skipped": skip_historical,
        "duplicate_proposals_skipped": skip_duplicates,
        "status": status,
        "counterexample": witness,
        "proof_available": False,
        "lean_kernel_executed": False,
        "all_order_generalization": "NOT_PROVED",
    }


def guided_synthesis(db_path: str, *, seed: int = 42, n6_training: int = 64,
                     n7_training: int = 64, holdout_budget: int = 32,
                     max_candidates: int = 4) -> dict:
    cfg = _config(seed, n6_training, n7_training,
                  holdout_budget, max_candidates)
    source_fp, _ = _tasks(db_path, 7)  # Independently replay every source layer.
    history, _, _, sources = _historical(db_path)
    training_masks = {
        5: list(range(1 << len(edge_positions(5)))),
        6: _bounded_masks(6, seed, n6_training),
        7: _choose_historical(history, seed, n7_training),
    }
    training, training_meta = _data(training_masks)
    candidates, elimination = _derive(training)
    selected, preflight = _historical_preflight(
        candidates, history, max_candidates)
    # Exactly the selected candidate statements, untouched by new holdout
    # results. Independent, fresh source-novel masks allocated only now.
    excluded = set(history)
    experiments = []
    for item in selected:
        trial = _guided_holdout(
            item, source_fp, seed, holdout_budget, excluded)
        if set(trial["masks_checked"]) & excluded:
            raise ValueError("holdout samples reused audited source or another trial")
        excluded.update(trial["masks_checked"])
        experiments.append(trial)
    return {
        "schema": SCHEMA,
        "configuration": cfg,
        "source_fingerprint": source_fp,
        "source_layers": sources,
        "training": training_meta,
        "historical_n7_masks_sha256": digest(sorted(history)),
        "historical_n7_count": len(history),
        "generated_canonical_candidates": len(candidates),
        "filter_counts": elimination,
        "candidate_bank_sha256": digest(candidates),
        "historical_preflight": preflight,
        "selected": selected,
        "guided_holdout": {
            "method": SAMPLER,
            "not_uniform_random": True,
            "selection_used_holdout_data": False,
            "results": experiments,
            "distinct_new_graphs_checked": sum(
                trial["graphs_checked"] for trial in experiments),
            "refutations": sum(
                trial["status"] == "REFUTED_ON_GUIDED_HOLDOUT"
                for trial in experiments),
            "nonvacuous_survivals": sum(
                trial["status"] == "SURVIVED_BOUNDED_GUIDED_HOLDOUT"
                for trial in experiments),
            "incomplete_budget": sum(
                trial["status"] == "INCOMPLETE_GUIDED_SAMPLE_BUDGET"
                for trial in experiments),
        },
        "lean_handoff": [{
            "candidate_id": trial["candidate_id"],
            "statement": trial["statement"],
            "state": "PENDING_AFFINE_TO_LEAN_TRANSLATION",
            "proof_available": False,
            "lean_formal_verification": "NOT_PERFORMED",
        } for trial in experiments if
            trial["status"] == "SURVIVED_BOUNDED_GUIDED_HOLDOUT"],
        "mathematical_novelty": "NOT_ASSESSED",
        "formal_kernel_executed": False,
        "all_order_theorems_proved": 0,
        "historical_evidence_modified": False,
    }


def save_guided(db_path: str, output: str, *, seed: int = 42,
                n6_training: int = 64, n7_training: int = 64,
                holdout_budget: int = 32, max_candidates: int = 4) -> dict:
    cfg = _config(seed, n6_training, n7_training,
                  holdout_budget, max_candidates)
    path = Path(output)
    if path.exists():
        old = audit_guided(db_path, output)["report"]
        if old["configuration"] != cfg:
            raise ValueError("immutable guided run cannot be overwritten")
        return old
    report = guided_synthesis(db_path, **cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(buf)
        handle.flush()
        os.fsync(handle.fileno())
    return report


def audit_guided(db_path: str, output: str) -> dict:
    path = Path(output)
    if not path.is_file() or path.stat().st_size > 3_000_000:
        raise ValueError("missing or oversized guided research result")
    report = json.loads(path.read_text(encoding="utf-8"))
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unknown guided research schema")
    config = report.get("configuration")
    if type(config) is not dict or set(config) != {
        "seed", "n6_training", "n7_training", "holdout_budget", "max_candidates"
    }:
        raise ValueError("invalid guided research configuration")
    expected = guided_synthesis(db_path, **config)
    if stable(expected) != stable(report):
        raise ValueError("guided research report failed complete source replay")
    return {
        "audit": "ACCEPTED_SOURCE_AND_GUIDED_HOLDOUT_REPLAY",
        "source_fingerprint": expected["source_fingerprint"],
        "generated_candidates": expected["generated_canonical_candidates"],
        "holdout_graphs": expected["guided_holdout"]["distinct_new_graphs_checked"],
        "refutations": expected["guided_holdout"]["refutations"],
        "proofs_produced": 0,
        "report": expected,
    }
