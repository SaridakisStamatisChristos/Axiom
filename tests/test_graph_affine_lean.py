"""AXIOM v0.19 — reject false proof claims, verify semantic/scope binding."""
import copy

import pytest

from axiom.graph_affine import AffineGraphConjecture
from axiom.graph_affine_lean import (
    build_affine_lean_source, verify_affine_lean,
    audit_affine_lean_record, SOURCE_SCHEMA,
)
from axiom.lean_backend import LeanBackendError


def stmt(coeff, upper, assumption="ALL"):
    return AffineGraphConjecture.normalized(
        coeff, upper, assumption).to_dict()


def test_canonical_closed_translator_preserves_exact_n6_semantics():
    subject = stmt({"edges": 1, "triangles": 1}, 35)
    a = build_affine_lean_source(subject)
    b = build_affine_lean_source(subject)
    assert a == b
    assert a["exact_graph_order"] == 6
    assert a["schema"] == SOURCE_SCHEMA
    assert a["envelope_upper_bound"] == 35
    assert a["all_orders_verified"] is False
    assert "(edgeCount mask : Int)" in a["source"]
    assert "(triangleCount mask : Int)" in a["source"]
    assert "#print axioms" in a["source"]
    assert not any(x in a["source"] for x in ("sorry", "native_decide", "admit"))


def test_negative_optional_n_term_respected_under_exact_envelope():
    subject = stmt({"edges": 2, "triangles": 1, "n": -1}, 44)
    result = build_affine_lean_source(subject)
    assert result["envelope_upper_bound"] == 44
    assert "(-1 : Int) * (6 : Int)" in result["source"]


def test_too_tight_or_conditional_or_unrepresented_is_rejected():
    subjects = [
        stmt({"edges": 1, "triangles": 1}, 34),
        stmt({"edges": 1, "triangles": 1}, 35, "BIPARTITE"),
        stmt({"independence": 1, "clique": 1, "n": -1}, 1),
        stmt({"edges": -1, "triangles": 1}, 20),
    ]
    for source in subjects:
        with pytest.raises(LeanBackendError):
            build_affine_lean_source(source)


def test_fabricated_formal_success_and_scope_are_never_accepted():
    subject = stmt({"edges": 1, "triangles": 1}, 35)
    pending = verify_affine_lean(subject, project_root="/missing-axiom-lean-root")
    assert pending["status"] == "CONFIGURATION_MISSING"
    assert pending["accepted"] is False
    assert audit_affine_lean_record(pending)
    for change in [
        {"status": "FORMALLY_VERIFIED", "accepted": True},
        {"universal_lean_proof": True},
        {"all_orders_verified": True},
        {"source": pending["source"] + "\nby omega"},
    ]:
        forged = copy.deepcopy(pending)
        forged.update(change)
        with pytest.raises(LeanBackendError):
            audit_affine_lean_record(forged)


def test_malformed_affine_ast_rejected_before_leancode():
    source = stmt({"edges": 1, "triangles": 1}, 35)
    source["lhs"][0]["numerator"] = 0
    with pytest.raises(LeanBackendError):
        build_affine_lean_source(source)
