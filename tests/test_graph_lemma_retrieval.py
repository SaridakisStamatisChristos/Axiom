"""Regression and held-out composition checks for the pinned retrieval path."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_lemma_retrieval import (
    CLIQUE_BOUNDS_INDEX, CLIQUE_INDEPENDENCE_INDEX, DECOMPOSITION_INDEX, retrieve,
)
from axiom.graph_proof import RETRIEVAL_SCHEMA, SCHEMA, audit, prove
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation

PROJECT = Path(__file__).resolve().parents[1]
HELD_OUT = json.loads((PROJECT / "research/proof_engine/retrieval_targets.json").read_text())


@pytest.mark.parametrize("_name,premise,weights,rhs,adapter", HELD_OUT)
def test_fallback_extends_composition_and_replays(tmp_path, _name, premise, weights, rhs, adapter):
    claim = AffineRelation.normalized(weights, rhs, premise).to_dict()
    original = prove(claim, project_root=tmp_path)
    assert original["schema"] == SCHEMA and original["status"] == "SEARCH_EXHAUSTED"
    result = prove(claim, retrieval_limit=1, project_root=tmp_path)
    assert result["schema"] == RETRIEVAL_SCHEMA
    assert result["status"] == "LEAN_UNAVAILABLE"
    assert result["retrieval"]["initial_derivation"] == original["derivation"]
    assert result["derivation"]["derived"]
    used = result["derivation"]["directions"][0]["lemmas"]
    assert len(used) == 2
    assert any(x["theorem"] == "retrieved_" + adapter for x in used)
    assert audit(original) and audit(result)


@pytest.mark.parametrize("_name,premise,weights,rhs,adapter", HELD_OUT)
@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
def test_held_out_goal_passes_real_lean(_name, premise, weights, rhs, adapter):
    claim = AffineRelation.normalized(weights, rhs, premise).to_dict()
    result = prove(claim, retrieval_limit=1, project_root=PROJECT)
    assert result["status"] == "FORMALLY_VERIFIED", result["kernel"]
    assert result["kernel"]["lean_kernel_executed"] is True
    assert audit(result)


def test_applicability_witness_precedence_and_shared_budget(tmp_path):
    claim = AffineRelation.normalized({"chromatic": 1}, 2)
    assert all(item.lemma.premise == "ALL" for item in retrieve(claim, 32))
    refuted = prove(claim.to_dict(), retrieval_limit=32, project_root=tmp_path)
    assert refuted["status"] == "COUNTEREXAMPLE"
    assert not refuted["retrieval"]["attempted"]

    target = AffineRelation.normalized({"clique": 1, "n": -1}, 0).to_dict()
    primary = prove(target, project_root=tmp_path)["derivation"]["nodes"]
    exhausted = prove(target, limits=SearchLimits(max_nodes=primary + 1),
                      retrieval_limit=1, project_root=tmp_path)
    assert exhausted["retrieval"]["attempted"]
    assert exhausted["status"] == "SEARCH_EXHAUSTED"
    assert exhausted["reason"] == "NODE_BUDGET_EXHAUSTED"
    assert exhausted["derivation"]["nodes"] == primary + 1
    assert audit(exhausted)

    existing = AffineRelation.normalized({"clique": 1, "chromatic": -1}, 0).to_dict()
    ordinary = prove(existing, project_root=tmp_path)
    enabled = prove(existing, retrieval_limit=1, project_root=tmp_path)
    assert not enabled["retrieval"]["attempted"]
    assert enabled["generated"] == ordinary["generated"]


def test_retrieval_metadata_is_replayed_after_rehash(tmp_path):
    goal = AffineRelation.normalized({"clique": 1, "n": -1}, 0).to_dict()
    result = prove(goal, retrieval_limit=1, project_root=tmp_path)
    damaged = deepcopy(result)
    damaged["retrieval"]["selected"][0]["mathlib_declarations"] = ["Unrelated.theorem"]
    damaged["record_sha256"] = digest({k: v for k, v in damaged.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(damaged)
    for bad_limit in (-1, 33, True):
        with pytest.raises(ValueError, match="retrieval limit"):
            prove(goal, retrieval_limit=bad_limit)


@pytest.mark.parametrize("premise", ["ALL", "CONNECTED"])
@pytest.mark.parametrize("terms,rhs,adapter", [
    ({"clique": 2, "triangles": -1}, 5, "twice_clique_le_triangles_add_five"),
    ({"chromatic": 2, "clique": -1, "n": -1}, 0, "twice_chromatic_le_clique_add_order"),
])
def test_clique_bounds_close_both_scopes(tmp_path, premise, terms, rhs, adapter):
    claim = AffineRelation.normalized(terms, rhs, premise)
    baseline = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=CLIQUE_INDEPENDENCE_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED"
    project_root = PROJECT if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    result = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=CLIQUE_BOUNDS_INDEX,
                   project_root=project_root, timeout=25)
    expected = "FORMALLY_VERIFIED" if project_root == PROJECT else "LEAN_UNAVAILABLE"
    assert result["status"] == expected, result["kernel"]
    selected = result["derivation"]["directions"][0]["lemmas"]
    assert [term["theorem"] for term in selected] == ["retrieved_" + adapter]
    assert audit(result)


@pytest.mark.parametrize("premise,terms,rhs,scale,adapter", [
    ("TRIANGLE_FREE", {"chromatic": 1, "matching": -1}, 1, None,
     "triangle_free_chromatic_le_matching_add_one"),
    ("TRIANGLE_FREE", {"chromatic": 1, "matching": -1, "clique": 1, "n": -1}, 2, None,
     "triangle_free_chromatic_le_matching_add_one"),
    ("CONNECTED", {"chromatic": 2, "edges": -1, "n": 1}, 6, None,
     "connected_twice_chromatic_le_edges_sub_order_add_six"),
    ("CONNECTED", {"clique": 2, "edges": -1, "n": 1}, 6, None,
     "connected_twice_chromatic_le_edges_sub_order_add_six"),
    ("CONNECTED", {"clique": 1, "edges": -1, "n": 1}, 3, 2,
     "connected_twice_chromatic_le_edges_sub_order_add_six"),
])
def test_decomposition_retrieval_and_integer_rounding(tmp_path, premise, terms, rhs, scale, adapter):
    claim = AffineRelation.normalized(terms, rhs, premise)
    baseline = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=CLIQUE_BOUNDS_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED"

    project_root = PROJECT if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    result = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=DECOMPOSITION_INDEX,
                   project_root=project_root, timeout=25)
    expected = "FORMALLY_VERIFIED" if project_root == PROJECT else "LEAN_UNAVAILABLE"
    assert result["status"] == expected, result["kernel"]
    direction, = result["derivation"]["directions"]
    assert direction.get("target_scale") == scale
    assert any(row["theorem"] == "retrieved_" + adapter for row in direction["lemmas"])
    assert audit(result)
    if scale:
        damaged = deepcopy(result)
        damaged["derivation"]["directions"][0]["target_scale"] += 1
        damaged["record_sha256"] = digest({k: v for k, v in damaged.items() if k != "record_sha256"})
        with pytest.raises(ValueError, match="deterministic replay"):
            audit(damaged)


@pytest.mark.parametrize("premise,terms,rhs,adapter", [
    ("ALL", {"chromatic": 1, "matching": -1}, 1, "triangle_free_chromatic_le_matching_add_one"),
    ("ALL", {"chromatic": 2, "edges": -1, "n": 1}, 6, "connected_twice_chromatic_le_edges_sub_order_add_six"),
])
def test_decomposition_retrieval_keeps_lemmas_in_scope(premise, terms, rhs, adapter):
    claim = AffineRelation.normalized(terms, rhs, premise)
    assert all(item.lemma.theorem != "retrieved_" + adapter
               for item in retrieve(claim, 32, index=DECOMPOSITION_INDEX))
