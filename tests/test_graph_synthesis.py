"""AXIOM v0.18 symbolic grammar, evidence separation, and refutation tests."""
from fractions import Fraction
import copy

import pytest

from axiom.graph_affine import (
    AffineGraphConjecture, check_conjecture, applicable,
)
from axiom.graph_synthesis import (
    _bounded_masks, _choose_historical, _config, _data, _derive,
    _known_heuristic, _shortlist, _witness, _holdout,
)


def test_fractional_coefficients_normalize_to_exact_equivalent_integers():
    stmt = AffineGraphConjecture.normalized({
        "independence": Fraction(1, 2),
        "clique": Fraction(1, 2),
        "n": Fraction(-1, 2),
    }, Fraction(1, 2))
    assert stmt.terms == (("clique", 1), ("independence", 1), ("n", -1))
    assert stmt.upper == 1
    assert AffineGraphConjecture.from_dict(stmt.to_dict()) == stmt
    assert stmt.id == AffineGraphConjecture.normalized({
        "clique": 2, "independence": 2, "n": -2,
    }, 2).id


def test_negative_scaling_cannot_silently_reverse_an_inequality():
    upper = AffineGraphConjecture.normalized({"edges": 1, "n": -1}, 0)
    lower = AffineGraphConjecture.normalized({"edges": -1, "n": 1}, 0)
    assert upper.id != lower.id
    assert check_conjecture(upper, {"n": 5, "edges": 10})[1] is False
    assert check_conjecture(lower, {"n": 5, "edges": 10})[1] is True


def test_invalid_or_noncanonical_serialized_inequalities_fail_closed():
    stmt = AffineGraphConjecture.normalized({
        "edges": 1, "triangles": -1, "n": -1,
    }, 0)
    tampered = stmt.to_dict()
    tampered["lhs"][0]["denominator"] = 2
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_dict(tampered)
    noncanonical = stmt.to_dict()
    noncanonical["lhs"].reverse()
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_dict(noncanonical)
    with pytest.raises(ValueError):
        AffineGraphConjecture.normalized({"edges": 0.25, "triangles": 1}, 2)
    with pytest.raises(ValueError):
        AffineGraphConjecture.normalized({"edges": 1, "not_a_feature": 1}, 2)
    with pytest.raises(ValueError):
        AffineGraphConjecture.normalized({"edges": 1, "triangles": 1}, 1, "INVALID")


def test_bounded_training_samples_are_reproducible_and_unique():
    masks = _bounded_masks(6, 42, 128)
    assert len(masks) == len(set(masks)) == 128
    assert masks == _bounded_masks(6, 42, 128)
    old = set(range(512))
    assert len(_choose_historical(old, 42, 32)) == 32
    assert set(_choose_historical(old, 42, 32)) <= old


def test_mathematical_known_fact_deferral_is_not_certification():
    known = AffineGraphConjecture.normalized({
        "independence": 1, "clique": 1, "n": -1,
    }, 1)
    assert _known_heuristic(known)
    assert known.to_dict()["mathematical_novelty"] == "NOT_ASSESSED"


def test_independent_counterexample_both_oracles_agree_on_actual_graph():
    stmt = AffineGraphConjecture.normalized({"edges": 1, "n": -1}, -7)
    graph = _witness(stmt, 7, (1 << 21) - 1)
    assert graph["left_hand_side"] > graph["right_hand_side"]
    assert graph["independent_witness_check"] == "ACCEPTED_BOTH_GRAPH_ORACLES"
    candidate = {"candidate_id": stmt.id, "statement": stmt.to_dict()}
    trial = _holdout(candidate, "f" * 64, [(1 << 21) - 1])
    assert trial["status"] == "REFUTED_ON_HOLDOUT"
    assert trial["lean_kernel_ran"] is False
    assert trial["theorem_status"] == "NOT_PROVED"


def test_nonvacuous_cross_order_synthesis_and_audited_separation():
    masks = {5: [0, 1, 2, 3, 15, 31, 63],
             6: [0, 1, 2, 3, 15, 31, 63],
             7: [0, 1, 2, 3, 15, 31, 63]}
    training, meta = _data(masks)
    assert meta["5"]["graphs"] == 7
    ranked, counts = _derive(training)
    assert type(ranked) is list
    assert type(counts) is dict
    selected = _shortlist(ranked, 3)
    assert len(selected) <= 3
    assert len({
        tuple(symbol for symbol, _ in
              AffineGraphConjecture.from_dict(item["statement"]).terms
              if symbol != "n")
        for item in selected
    }) == len(selected)
    for candidate in selected:
        assert candidate["statement_is_a_proved_theorem"] is False
        assert candidate["mathematical_novelty"] == "NOT_ASSESSED"


@pytest.mark.parametrize("patch", [
    {"seed": True}, {"seed": -1}, {"n6_training": 0},
    {"n7_training": 257}, {"holdout_budget": 7},
    {"max_candidates": 9}, {"max_candidates": False},
])
def test_bad_source_or_holdout_budget_is_rejected(patch):
    args = dict(seed=42, n6_training=64, n7_training=64,
                holdout_budget=32, max_candidates=4)
    args.update(patch)
    with pytest.raises(ValueError):
        _config(**args)
