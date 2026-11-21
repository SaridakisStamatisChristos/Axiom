"""Kernel and replay checks for the opt-in structural retrieval index."""
from copy import deepcopy
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_lemma_retrieval import INDEX_VERSION, STRUCTURAL_INDEX
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("ALL", {"chromatic": 1, "maximum_degree": -1}, 1, "chromatic_le_degree_add_one"),
    ("ALL", {"matching": 1, "independence": 1, "n": -1}, 0, "matching_add_independence_le_order"),
    ("BIPARTITE", {"chromatic": 1, "clique": -1}, 0, "bipartite_chromatic_le_clique"),
    ("BIPARTITE", {"triangles": 1}, 0, "bipartite_triangles_zero"),
    ("TRIANGLE_FREE", {"triangles": 1}, 0, "triangle_free_triangles_zero"),
]


@pytest.mark.parametrize("premise,weights,rhs,adapter", CASES)
def test_structural_adapter_is_selected_and_checked(tmp_path, premise, weights, rhs, adapter):
    claim = AffineRelation.normalized(weights, rhs, premise).to_dict()
    legacy = prove(claim, retrieval_limit=5, project_root=tmp_path)
    assert legacy["retrieval"]["index"] == INDEX_VERSION
    assert legacy["status"] == "SEARCH_EXHAUSTED" and audit(legacy)
    root = ROOT if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    result = prove(claim, retrieval_limit=5, retrieval_index=STRUCTURAL_INDEX, project_root=root)
    assert result["retrieval"]["index"] == STRUCTURAL_INDEX
    assert result["retrieval"]["index_sha256"] != legacy["retrieval"]["index_sha256"]
    lemma, = result["derivation"]["directions"][0]["lemmas"]
    assert lemma["theorem"] == "retrieved_" + adapter and audit(result)
    if root == ROOT:
        assert result["status"] == "FORMALLY_VERIFIED", result["kernel"]["stdout"]
    else:
        assert result["status"] == "LEAN_UNAVAILABLE"


def test_index_is_bound_to_replay_and_respects_assumptions(tmp_path):
    claim = AffineRelation.normalized({"triangles": 1}, 0, "BIPARTITE").to_dict()
    result = prove(claim, retrieval_limit=5, retrieval_index=STRUCTURAL_INDEX, project_root=tmp_path)
    assert "retrieved_triangle_free_triangles_zero" not in {
        row["adapter"] for row in result["retrieval"]["selected"]
    }
    forged = deepcopy(result)
    forged["retrieval"]["index"] = INDEX_VERSION
    forged["record_sha256"] = digest({k: v for k, v in forged.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="unexpected kernel evidence"):
        audit(forged)

    forged = deepcopy(result)
    forged["retrieval"]["index_sha256"] = "0" * 64
    forged["record_sha256"] = digest({k: v for k, v in forged.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(forged)
    with pytest.raises(ValueError, match="positive retrieval limit"):
        prove(claim, retrieval_index=STRUCTURAL_INDEX, project_root=tmp_path)
    with pytest.raises(ValueError, match="unknown Mathlib retrieval index"):
        prove(claim, retrieval_limit=5, retrieval_index="unknown", project_root=tmp_path)

    # The reverse matching/independence inequality fails on the three-vertex clique.
    reverse = AffineRelation.normalized({"matching": -1, "independence": -1, "n": 1}, 0).to_dict()
    result = prove(reverse, retrieval_limit=5, retrieval_index=STRUCTURAL_INDEX, project_root=tmp_path)
    assert result["status"] == "COUNTEREXAMPLE" and not result["retrieval"]["attempted"] and audit(result)
