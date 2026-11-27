"""Regression and held-out composition checks for the pinned retrieval path."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_lemma_retrieval import (
    CERTIFICATE_INDEX, CLIQUE_BOUNDS_INDEX, CLIQUE_INDEPENDENCE_INDEX, DECOMPOSITION_INDEX,
    SCHEDULED_INDEX, retrieve,
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



def test_scheduled_rounding_has_auditable_separate_budget(tmp_path):
    claim = AffineRelation.normalized({"clique": 1, "edges": -1, "n": 1}, 3, "CONNECTED")
    project = PROJECT if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    record = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=SCHEDULED_INDEX,
                   plan_limit=16, project_root=project, timeout=25)
    expected = "FORMALLY_VERIFIED" if project == PROJECT else "LEAN_UNAVAILABLE"
    assert record["status"] == expected, record["kernel"]
    direction, = record["derivation"]["directions"]
    assert direction["target_scale"] == 2
    schedule = record["retrieval"]["schedule"]
    assert 0 < schedule["direct_nodes"] <= schedule["direct_node_limit"]
    assert 0 < schedule["rounding_nodes"] <= schedule["rounding_node_limit"]
    assert schedule["rounding_nodes"] + schedule["direct_nodes"] == record["derivation"]["nodes"]
    assert sum(schedule[key] for key in ("direct_node_limit", "rounding_node_limit", "reserved_plan_slots")) == 10_000
    assert audit(record)
    altered = deepcopy(record)
    altered["retrieval"]["schedule"]["rounding_nodes"] += 1
    altered["record_sha256"] = digest({k: v for k, v in altered.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(altered)


def test_scheduled_direct_cutoff_leaves_tactic_slots(tmp_path):
    claim = AffineRelation.normalized({"clique": 1, "edges": -1, "n": 1}, 3, "CONNECTED")
    record = prove(claim.to_dict(), retrieval_limit=5, retrieval_index=SCHEDULED_INDEX,
                   plan_limit=16, limits=SearchLimits(max_nodes=3), project_root=tmp_path)
    assert record["retrieval"]["schedule"] == {
        "direct_node_limit": 1, "direct_nodes": 1, "direct_budget_exhausted": True,
        "rounding_node_limit": 0, "rounding_nodes": 0, "reserved_plan_slots": 2,
    }
    assert 0 < len(record["proof_plans"]["candidates"]) <= 2
    assert audit(record)


@pytest.mark.parametrize("premise,terms,rhs,required", [
    ("TRIANGLE_FREE", {"chromatic": 1, "clique": 1, "maximum_degree": -1}, 3,
     "retrieved_triangle_free_clique_le_two"),
    ("BIPARTITE", {"clique": 1, "components": 1, "matching": 1, "n": -2, "triangles": -1}, 0,
     "retrieved_matching_add_components_le_order"),
])
def test_inventory_certificate_recovers_omitted_facts(tmp_path, premise, terms, rhs, required):
    claim = AffineRelation.normalized(terms, rhs, premise).to_dict()
    profile = dict(retrieval_limit=5, synthesis_limit=3, split_order=True, induct_edges=True,
                   plan_limit=16, timeout=45)
    baseline = prove(claim, **profile, retrieval_index=SCHEDULED_INDEX, project_root=tmp_path)
    assert not baseline["derivation"]["derived"]
    project = PROJECT if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    attempt = prove(claim, **profile, retrieval_index=CERTIFICATE_INDEX, project_root=project)
    expected = "FORMALLY_VERIFIED" if project == PROJECT else "LEAN_UNAVAILABLE"
    assert attempt["status"] == expected, attempt["kernel"]
    retrieval = attempt["retrieval"]
    fallback = retrieval["certificate_fallback"]
    schedule = retrieval["schedule"]
    assert retrieval["selected"] == baseline["retrieval"]["selected"]
    assert attempt["derivation"]["derived"] and not attempt["proof_plans"]["candidates"]
    assert any(entry["adapter"] == required for entry in fallback["selected"])
    assert 0 < fallback["nodes"] <= schedule["direct_node_limit"] - schedule["direct_nodes"]
    assert attempt["derivation"]["nodes"] == (
        schedule["direct_nodes"] + schedule["rounding_nodes"] + fallback["nodes"]
    )
    assert audit(attempt)

    fallback["nodes"] -= 1
    attempt["record_sha256"] = digest({k: v for k, v in attempt.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(attempt)
