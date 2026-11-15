"""Source-bound, evidence-separated adaptive graph candidate tests."""
import copy
import json

import pytest

from axiom.graph_adaptive import (
    _config, _elementary, _candidate_bank, _historical, _pool_candidates,
    _pilot, research_discovery, save_discovery, audit_discovery,
)
from axiom.graph_claims import GraphStatement, digest


def test_parameterized_triviality_is_deprioritized_but_not_proved():
    assert _elementary(GraphStatement(7, "bipartite_independence_at_least_k", -3))
    assert _elementary(GraphStatement(7, "bipartite_independence_at_least_k", 4))
    assert not _elementary(GraphStatement(7, "bipartite_independence_at_least_k", 5))
    assert not _elementary(GraphStatement(7, "alpha_plus_clique_bound"))


def test_complete_reproducible_typed_candidate_bank():
    pool = _pool_candidates()
    assert len(pool) == len({item.canonical_key() for item in pool})
    assert all(item.n == 7 for item in pool)
    assert any(item.template == "alpha_plus_clique_bound" for item in pool)
    assert any(item.template == "edges_le_n_plus_k" and item.k == 7 for item in pool)


def test_source_pilot_finds_independent_checked_witness():
    from axiom.graph_checker import reference_properties
    stmt = GraphStatement(7, "edges_le_vertices")
    mask = (1 << 21) - 1
    pilot = _pilot(stmt, [mask], {mask: reference_properties(7, mask)})
    assert pilot["sampled_old_graphs"] == 1
    assert pilot["antecedent_satisfied"] == 1
    assert pilot["preexisting_witness"] is not None
    assert pilot["dual_oracle_witness_verified"] is True


def test_candidate_preflight_never_promotes_elementary_bound():
    full = (1 << 21) - 1
    cfg = _config(42, 1, 8, 3)
    bank = _candidate_bank({full}, set(), set(), cfg)
    by = {(c["statement"]["template"], c["statement"]["k"]): c
          for c in bank["candidates"]}
    trivial = by["bipartite_independence_at_least_k", -3]
    assert trivial["disposition"] == "DEFER_ELEMENTARY_TO_FORMALIZATION"
    assert trivial["not_a_proof"] is True
    assert bank["theorems_proved"] == 0
    assert by["edges_le_vertices", 0]["disposition"] == "REFUTED_BY_PREEXISTING_GRAPH"


@pytest.mark.parametrize("updates", [
    {"seed": -1}, {"source_probe": 0}, {"source_probe": 257},
    {"experiment_budget": 0}, {"task_limit": 13}, {"task_limit": True}
])
def test_invalid_config(updates):
    args = dict(seed=42, source_probe=32, experiment_budget=32, task_limit=3)
    args.update(updates)
    with pytest.raises(ValueError):
        _config(**args)
