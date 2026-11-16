"""AXIOM v0.19 — source-grounded antecedent-aware graph experiments."""
import copy

import pytest

from axiom.graph_affine import AffineGraphConjecture, applicable
from axiom.graph_checker import reference_properties
from axiom.graph_guided import guided_mask, _guided_holdout, SCHEMA


def test_constructed_antecedents_are_always_satisfied():
    for assumption in ("ALL", "BIPARTITE", "TRIANGLE_FREE", "CONNECTED"):
        for i in range(36):
            mask = guided_mask("affine-graph:fixture", assumption, 42, i)
            props = reference_properties(7, mask)
            assert applicable(assumption, props)
    assert guided_mask("affine-graph:fixture", "BIPARTITE", 42, 1) == (
        guided_mask("affine-graph:fixture", "BIPARTITE", 42, 1))


def test_triangle_free_sample_includes_nonbipartite_five_cycle():
    for i in (2, 5, 8):
        props = reference_properties(
            7, guided_mask("affine-graph:fixture", "TRIANGLE_FREE", 7, i))
        assert props["triangle_free"] is True
        assert props["bipartite"] is False


def test_guided_sampler_excludes_old_masks_and_requires_antecedent():
    stmt = AffineGraphConjecture.normalized(
        {"independence": 1, "clique": 1, "n": -1}, 1, "BIPARTITE")
    item = {"candidate_id": stmt.id, "statement": stmt.to_dict()}
    old = {guided_mask(stmt.id, "BIPARTITE", 42, 0)}
    trial = _guided_holdout(item, "f" * 64, 42, 24, old)
    assert trial["status"] == "SURVIVED_BOUNDED_GUIDED_HOLDOUT"
    assert trial["assumption_satisfying_graphs"] == 24
    assert len(set(trial["masks_checked"])) == 24
    assert not set(trial["masks_checked"]).intersection(old)
    assert trial["sampling_not_uniform_random"] is True
    assert trial["lean_kernel_executed"] is False


def test_guided_counterexample_has_independent_oracle_confirmation():
    stmt = AffineGraphConjecture.normalized(
        {"edges": 1, "clique": -1}, 0, "CONNECTED")
    item = {"candidate_id": stmt.id, "statement": stmt.to_dict()}
    trial = _guided_holdout(item, "f" * 64, 42, 16, set())
    assert trial["status"] == "REFUTED_ON_GUIDED_HOLDOUT"
    assert trial["counterexample"]["independent_witness_check"] == (
        "ACCEPTED_BOTH_GRAPH_ORACLES")
    assert trial["assumption_satisfying_graphs"] == trial["graphs_checked"]
    assert trial["all_order_generalization"] == "NOT_PROVED"


def test_targeted_mask_constructor_rejects_invalid_inputs():
    for candidate, assumption, seed, index in (
        ("untrusted", "ALL", 42, 0),
        ("affine-graph:x", "UNKNOWN", 42, 0),
        ("affine-graph:x", "ALL", -1, 0),
        ("affine-graph:x", "ALL", 42, -1),
        ("affine-graph:x", "ALL", 42, 70000),
        ("affine-graph:x", "ALL", True, 0),
    ):
        with pytest.raises(ValueError):
            guided_mask(candidate, assumption, seed, index)
