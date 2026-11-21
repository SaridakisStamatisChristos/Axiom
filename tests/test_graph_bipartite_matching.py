"""Certify and replay both directions of the bipartite cardinality equality."""
import os
from pathlib import Path

from axiom.graph_lemma_retrieval import MATCHING_INDEX, STRUCTURAL_INDEX
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"independence": 1, "matching": 1, "n": -1}
HALL_IMPORT = "import Mathlib.Combinatorics.Hall.Basic\n"


def test_bipartite_matching_equality_uses_both_directions(tmp_path):
    statement = AffineRelation.normalized(WEIGHTS, 0, "BIPARTITE", "=").to_dict()
    baseline = prove(statement, retrieval_limit=5, retrieval_index=STRUCTURAL_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED" and audit(baseline)

    real = os.environ.get("AXIOM_REAL_LEAN") == "1"
    result = prove(statement, retrieval_limit=5, retrieval_index=MATCHING_INDEX,
                   project_root=ROOT if real else tmp_path)
    assert result["status"] == ("FORMALLY_VERIFIED" if real else "LEAN_UNAVAILABLE"), result["kernel"]
    assert result["generated"]["source"].startswith(HALL_IMPORT)
    assert result["generated"]["source"].count(HALL_IMPORT) == 1
    assert {lemma["theorem"] for direction in result["derivation"]["directions"]
            for lemma in direction["lemmas"]} == {
        "retrieved_matching_add_independence_le_order",
        "retrieved_bipartite_order_le_matching_add_independence",
    }
    assert audit(result)


def test_matching_retrieval_preserves_premise_and_only_imports_used_modules(tmp_path):
    no_premise = AffineRelation.normalized(WEIGHTS, 0, "ALL", "=").to_dict()
    failure = prove(no_premise, retrieval_limit=5, retrieval_index=MATCHING_INDEX,
                    project_root=tmp_path)
    assert failure["status"] == "COUNTEREXAMPLE" and failure["generated"] is None
    assert audit(failure)

    triangles = AffineRelation.normalized({"triangles": 1}, 0, "BIPARTITE").to_dict()
    result = prove(triangles, retrieval_limit=32, retrieval_index=MATCHING_INDEX,
                   project_root=tmp_path)
    assert any("mathlib_imports" in entry for entry in result["retrieval"]["selected"])
    assert HALL_IMPORT not in result["generated"]["source"]
    assert audit(result)
