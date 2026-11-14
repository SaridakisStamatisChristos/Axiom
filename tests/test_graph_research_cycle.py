"""Adversarial v0.15 graph-research-cycle boundaries."""
import copy
import pytest

from axiom.graph_claims import GraphStatement
from axiom.graph_research_cycle import (
    _mask_stream, audit_bounded_trial, bounded_trial, execute_cycle,
)


def task(template: str) -> dict:
    statement = GraphStatement(7, template).to_dict()
    return {
        "task_id": "test:" + template,
        "statement_id": "test:statement:" + template,
        "statement": statement,
        "action": "EXTEND_BOUNDED_FALSIFICATION",
    }


def test_independent_bounded_survival_is_never_a_proof():
    t = task("handshake")
    fingerprint = "a" * 64
    result = bounded_trial(t, fingerprint, search_budget=16, seed=91)
    assert result["status"] == "SURVIVED_BOUNDED_SEARCH"
    assert result["formal_lean_verification"] == "NOT_PERFORMED"
    assert result["exhaustive"] is False
    assert len(set(result["masks_checked"])) == 16
    assert audit_bounded_trial(t, fingerprint, result)
    assert result == bounded_trial(t, fingerprint, search_budget=16, seed=91)


def test_independent_witness_is_genuine_and_bound_to_claim():
    t = task("edges_le_vertices")
    fingerprint = "b" * 64
    result = bounded_trial(t, fingerprint, search_budget=32, seed=42)
    assert result["status"] == "REFUTED"
    assert result["counterexample"] is not None
    assert result["independent_witness_audit"] is True
    assert audit_bounded_trial(t, fingerprint, result)
    altered = copy.deepcopy(result)
    altered["counterexample"]["edges"] = []
    with pytest.raises(ValueError):
        audit_bounded_trial(t, fingerprint, altered)


def test_tampered_larger_scope_and_forged_proof_are_rejected():
    t = task("handshake")
    result = bounded_trial(t, "c" * 64, search_budget=8, seed=3)
    modified = copy.deepcopy(result)
    modified["status"] = "FORMALLY_VERIFIED"
    with pytest.raises(ValueError):
        audit_bounded_trial(t, "c" * 64, modified)
    modified = copy.deepcopy(result)
    modified["masks_checked"][0] ^= 1
    with pytest.raises(ValueError):
        audit_bounded_trial(t, "c" * 64, modified)
    modified = copy.deepcopy(t)
    modified["statement"]["n"] = 6
    with pytest.raises(ValueError):
        bounded_trial(modified, "c" * 64)


def test_budget_and_seed_limits_before_source_access(tmp_path):
    missing = str(tmp_path / "no.sqlite3")
    output = str(tmp_path / "runs")
    for bad in (True, 0, 8):
        with pytest.raises(ValueError):
            execute_cycle(missing, output, proof_quota=bad)
    for bad in (0, 11):
        with pytest.raises(ValueError):
            execute_cycle(missing, output, experiment_quota=bad)
    for bad in (0, 257):
        with pytest.raises(ValueError):
            execute_cycle(missing, output, search_budget=bad)
    with pytest.raises(ValueError):
        execute_cycle(missing, output, seed=-1)
    assert _mask_stream("x", 7, 5, 24) == _mask_stream("x", 7, 5, 24)
