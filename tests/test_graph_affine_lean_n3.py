"""AXIOM v0.19: soundly scoped n3 affine theorem-to-Lean semantics."""
import copy

import pytest

from axiom.graph_affine import AffineGraphConjecture
from axiom.graph_lean import LeanBackendError
from axiom.graph_affine_lean_n3 import (
    build_n3_affine_source, verify_n3_affine, audit_n3_affine,
)


def true_stmt():
    return AffineGraphConjecture.normalized(
        {"triangles": 1, "edges": -1}, 0).to_dict()


def test_actual_graph_semantics_source_has_real_bit_definitions_not_tables():
    proof = build_n3_affine_source(true_stmt())
    source = proof["source"]
    assert "Nat.testBit mask i" in source
    assert "bit mask 0 + bit mask 1 + bit mask 2" in source
    assert "bit mask 0 = 1 ∧ bit mask 1 = 1 ∧ bit mask 2 = 1" in source
    assert "theorem axiom_affine_n3_" in source
    assert "(mask : Fin 8)" in source
    assert "fin_cases mask <;> decide" in source
    assert proof["labelled_graphs_semantically_prechecked"] == 8
    assert proof["all_order_generalization"] == "NOT_PROVED"
    assert build_n3_affine_source(true_stmt()) == proof


def test_refuted_exact_order_cannot_enter_lean_bridge():
    false_stmt = AffineGraphConjecture.normalized(
        {"edges": 1, "triangles": -1}, 0).to_dict()
    with pytest.raises(LeanBackendError, match="refuted"):
        build_n3_affine_source(false_stmt)


def test_unsupported_invariants_and_conditional_assumptions_fail_closed():
    unsupported = AffineGraphConjecture.normalized(
        {"clique": 1, "edges": -1}, 0).to_dict()
    with pytest.raises(LeanBackendError, match="unsupported"):
        build_n3_affine_source(unsupported)
    conditional = AffineGraphConjecture.normalized(
        {"triangles": 1, "edges": -1}, 0, "BIPARTITE").to_dict()
    with pytest.raises(LeanBackendError, match="unsupported"):
        build_n3_affine_source(conditional)


def test_absent_lean_toolchain_is_not_false_success(tmp_path):
    result = verify_n3_affine(true_stmt(), project_root=str(tmp_path))
    assert result["status"] == "CONFIGURATION_MISSING"
    assert result["accepted"] is False
    assert result["lean_kernel_executed"] is False
    assert audit_n3_affine(result)


def test_tampered_source_or_forged_kernel_record_is_rejected(tmp_path):
    record = verify_n3_affine(true_stmt(), project_root=str(tmp_path))
    altered = copy.deepcopy(record)
    altered["source"] += "\naxiom bogus : False"
    with pytest.raises(LeanBackendError, match="altered"):
        audit_n3_affine(altered)
    fake = copy.deepcopy(record)
    fake["status"] = "FORMALLY_VERIFIED_EXACT_N3"
    fake["accepted"] = True
    with pytest.raises(LeanBackendError, match="forged"):
        audit_n3_affine(fake)
    promoted = copy.deepcopy(record)
    promoted["all_order_generalization"] = "PROVED"
    with pytest.raises(LeanBackendError):
        audit_n3_affine(promoted)


def test_source_scope_is_not_the_all_order_statement():
    theorem = build_n3_affine_source(true_stmt())
    assert "all_orders" in theorem["statement"]["quantifier"]
    assert theorem["formal_graph_order"] == 3
    assert theorem["formal_scope"].endswith("exactly n=3 vertices")
    assert theorem["all_order_generalization"] == "NOT_PROVED"
