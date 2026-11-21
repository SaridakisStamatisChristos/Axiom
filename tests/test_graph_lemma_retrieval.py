"""Regression and held-out composition checks for the pinned retrieval path."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_lemma_retrieval import retrieve
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
