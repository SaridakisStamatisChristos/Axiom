"""AXIOM v0.18 symbolic grammar, evidence separation, and refutation tests."""
from fractions import Fraction
import copy

import pytest

from axiom.graph_affine import (
    AffineExpression, AffineGraphConjecture, GraphAssumption, GraphInvariant,
    check_conjecture, applicable,
)
from axiom.graph_synthesis import (
    _bounded_masks, _choose_historical, _config, _data, _derive,
    _known_heuristic, _shortlist, _witness, _holdout,
)


def test_two_sided_composition_preserves_canonical_source_identity():
    invariant = AffineExpression.invariant
    clique = invariant(GraphInvariant.CLIQUE)
    independence = invariant(GraphInvariant.INDEPENDENCE)
    order = invariant(GraphInvariant.ORDER)
    offset = invariant(GraphInvariant.EDGES).scaled(100) + AffineExpression(
        constant=Fraction(1, 7))

    # Cancel the shared affine offset, then clear the positive denominators.
    lhs = offset + (independence + clique).scaled(Fraction(2, 3))
    rhs = (order + AffineExpression(constant=1)).scaled(Fraction(2, 3)) + offset
    statement = AffineGraphConjecture.from_expressions(lhs, rhs)
    legacy = AffineGraphConjecture.normalized(
        {"clique": 1, "independence": 1, "n": -1}, 1)
    assert statement.to_dict() == legacy.to_dict()
    assert AffineGraphConjecture.from_dict(statement.to_dict()) == statement
    assert statement.id == (
        "affine-graph:b5d0b57210d245260f3b3651dc0dc98f4ba31f3218551e7fa9010e79c811e1f4")


def test_side_and_assumption_are_part_of_the_composed_statement():
    edges = AffineExpression.invariant(GraphInvariant.EDGES)
    clique = AffineExpression.invariant(GraphInvariant.CLIQUE)
    upper = AffineGraphConjecture.from_expressions(edges, clique)
    lower = AffineGraphConjecture.from_expressions(clique, edges)
    conditional = AffineGraphConjecture.from_expressions(
        edges, clique, assumption=GraphAssumption.BIPARTITE)

    assert len({upper.id, lower.id, conditional.id}) == 3
    graph = {"n": 4, "edges": 6, "clique": 4, "bipartite": False}
    assert check_conjecture(upper, graph) == (True, False, 2)
    assert check_conjecture(lower, graph) == (True, True, -2)
    assert check_conjecture(conditional, graph) == (False, False, 2)


@pytest.mark.parametrize("invalid", [True, 0.5, "1", None])
def test_expression_rejects_inexact_or_mistyped_numbers(invalid):
    with pytest.raises(ValueError):
        AffineExpression(constant=invalid)
    with pytest.raises(ValueError):
        AffineExpression(((GraphInvariant.EDGES, invalid),))
    with pytest.raises(ValueError):
        AffineExpression.invariant(GraphInvariant.EDGES).scaled(invalid)


def test_expression_rejects_untyped_symbols_assumptions_and_cancelled_statements():
    with pytest.raises(ValueError):
        AffineExpression.invariant("edges")
    edges = AffineExpression.invariant(GraphInvariant.EDGES)
    clique = AffineExpression.invariant(GraphInvariant.CLIQUE)
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_expressions(edges, clique, assumption="ALL")
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_expressions(edges, 0)
    with pytest.raises(ValueError):
        AffineGraphConjecture.from_expressions(edges + clique, edges + clique)


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
    upper = AffineGraphConjecture.normalized({"edges": 1, "triangles": -1}, 0)
    lower = AffineGraphConjecture.normalized({"edges": -1, "triangles": 1}, 0)
    assert upper.id != lower.id
    assert check_conjecture(upper, {"n": 5, "edges": 10, "triangles": 0})[1] is False
    assert check_conjecture(lower, {"n": 5, "edges": 10, "triangles": 0})[1] is True


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
    stmt = AffineGraphConjecture.normalized({"edges": 1, "clique": -1}, 0)
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


def test_antecedent_free_holdout_is_inconclusive_not_a_survival():
    stmt = AffineGraphConjecture.normalized(
        {"edges": 1, "clique": -1}, 0, "BIPARTITE")
    item = {"candidate_id": stmt.id, "statement": stmt.to_dict()}
    # The complete seven-vertex graph contains triangles, so no sample
    # satisfies the bipartite antecedent. No theorem evidence is earned.
    trial = _holdout(item, "f" * 64, [(1 << 21) - 1])
    assert trial["status"] == "INCONCLUSIVE_NO_ANTECEDENT_COVERAGE"
    assert trial["assumption_satisfying_graphs"] == 0
    assert trial["counterexample"] is None
    assert trial["theorem_status"] == "NOT_PROVED"


def test_original_source_preflight_rejects_false_conjectures():
    from axiom.graph_synthesis import _historical_preflight
    false_stmt = AffineGraphConjecture.normalized(
        {"edges": 1, "clique": -1}, 0)
    good_stmt = AffineGraphConjecture.normalized(
        {"independence": 1, "clique": 1, "n": -1}, 1)
    bank = [
        {"candidate_id": false_stmt.id,
         "statement": false_stmt.to_dict(), "selection_score": 100},
        {"candidate_id": good_stmt.id,
         "statement": good_stmt.to_dict(), "selection_score": 99},
    ]
    chosen, report = _historical_preflight(
        bank, {0, (1 << 21) - 1}, 2)
    assert [r["candidate_id"] for r in chosen] == [good_stmt.id]
    assert report["source_refutations"] == 1
    assert report["available_historical_graphs"] == 2
    assert report["new_graphs_used_for_selection"] == 0
    assert report["source_refutation_examples"][0][
        "source_counterexample"]["independent_witness_check"] == (
        "ACCEPTED_BOTH_GRAPH_ORACLES")


def test_known_universal_inequality_is_deferred_under_connected_assumption():
    known = AffineGraphConjecture.normalized(
        {"clique": 1, "chromatic": -1}, 0, "CONNECTED")
    assert _known_heuristic(known)
