"""AXIOM v0.19: truthful premise-aware, disjoint, bounded graph cohorts."""
import pytest

from axiom.graph_affine import applicable
from axiom.graph_checker import reference_properties
from axiom.graph_stratified import (
    _candidate_mask, _configuration, sample_stratum,
)


def test_bipartite_cohort_is_nonvacuous_and_deterministic():
    identity = "affine-graph:bipartite-example"
    prior = {0, 1, 2, 3}
    first, meta = sample_stratum(
        identity, "BIPARTITE", 43, 24, prior, max_proposals=600)
    second, same = sample_stratum(
        identity, "BIPARTITE", 43, 24, prior, max_proposals=600)
    assert len(first) == len(set(first)) == 24
    assert first == second
    assert meta == same
    assert not prior.intersection(first)
    assert meta["accepted_premise_satisfying_graphs"] == 24
    assert meta["uniform_over_eligible_graphs"] is False
    for mask in first:
        assert applicable("BIPARTITE", reference_properties(7, mask))


def test_strata_accept_only_matching_antecedents_and_do_not_overlap():
    prior = {0, 1, 2, 3}
    visited = set(prior)
    for assumption in ("ALL", "CONNECTED", "BIPARTITE", "TRIANGLE_FREE"):
        masks, summary = sample_stratum(
            "affine-graph:fixture-" + assumption, assumption,
            43, 12, visited, max_proposals=20000)
        assert len(masks) == 12
        assert len(set(masks)) == 12
        assert not visited.intersection(masks)
        assert summary["accepted_premise_satisfying_graphs"] == 12
        for mask in masks:
            assert applicable(assumption, reference_properties(7, mask))
        visited.update(masks)
    assert len(visited) == 52


def test_budget_exhaustion_does_not_falsely_report_survival():
    masks, evidence = sample_stratum(
        "affine-graph:fixture", "BIPARTITE", 1234,
        10, set(), max_proposals=10)
    assert len(masks) <= 10
    assert evidence["requested_graphs"] == 10
    assert evidence["accepted_premise_satisfying_graphs"] == len(masks)
    assert evidence["exhaustive"] is False
    assert evidence["formal_lean_verified"] is False


def test_stratification_rejects_bool_and_invalid_graph_masks():
    for bad in ({-1}, {True}, {1 << 21}):
        with pytest.raises(ValueError):
            sample_stratum("affine-graph:fixture", "ALL", 42, 4, bad)
    for kwargs in (
        {"seed": True}, {"budget": 0}, {"budget": 257},
        {"max_proposals": 0}, {"max_proposals": 50001},
    ):
        cfg = {"seed": 42, "budget": 4, "max_proposals": 100}
        cfg.update(kwargs)
        with pytest.raises(ValueError):
            _configuration(**cfg)


def test_same_stratum_seed_changes_candidate_walk():
    a, _ = sample_stratum(
        "affine-graph:fixture", "CONNECTED", 1, 8, set())
    b, _ = sample_stratum(
        "affine-graph:fixture", "CONNECTED", 2, 8, set())
    assert a != b
