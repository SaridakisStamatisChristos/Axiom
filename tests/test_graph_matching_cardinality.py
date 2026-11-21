"""Exercise the matching cardinality adapter and its compositions."""
import os
from pathlib import Path

import pytest

from axiom.graph_lemma_retrieval import COMPONENT_INDEPENDENCE_INDEX, MATCHING_CARDINALITY_INDEX, retrieve
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
CARDINALITY = {"matching": 2, "n": -1}


@pytest.mark.parametrize(("weights", "rhs", "premise", "other_lemma"), (
    (CARDINALITY, 0, "ALL", None),
    ({**CARDINALITY, "chromatic": 1, "maximum_degree": -1}, 1, "ALL",
     "retrieved_chromatic_le_degree_add_one"),
    ({**CARDINALITY, "triangles": 1}, 0, "TRIANGLE_FREE", "retrieved_triangle_free_triangles_zero"),
))
def test_matching_cardinality_certifies_and_composes(weights, rhs, premise, other_lemma, tmp_path):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    baseline = prove(statement, retrieval_limit=5, retrieval_index=COMPONENT_INDEPENDENCE_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED" and audit(baseline)

    real = os.environ.get("AXIOM_REAL_LEAN") == "1"
    result = prove(statement, retrieval_limit=5, retrieval_index=MATCHING_CARDINALITY_INDEX,
                   project_root=ROOT if real else tmp_path)
    assert result["status"] == ("FORMALLY_VERIFIED" if real else "LEAN_UNAVAILABLE"), result["kernel"]
    assert result["scope"] == "ALL_GRAPH_ORDERS"
    expected = {"retrieved_twice_matching_le_order"}
    if other_lemma is not None:
        expected.add(other_lemma)
    assert {lemma["theorem"] for side in result["derivation"]["directions"]
            for lemma in side["lemmas"]} == expected
    assert audit(result)


def test_matching_cardinality_can_be_tight(tmp_path):
    statement = AffineRelation.normalized(CARDINALITY, -1, "CONNECTED").to_dict()
    result = prove(statement, retrieval_limit=5, retrieval_index=MATCHING_CARDINALITY_INDEX,
                   project_root=tmp_path)
    assert result["status"] == "COUNTEREXAMPLE"
    assert result["counterexample"]["graph"] == {"n": 2, "edges": [[0, 1]]}
    assert result["generated"] is None and audit(result)


def test_single_matching_coefficient_preserves_retrieval_slots():
    claim = AffineRelation.normalized({"components": 1, "matching": 1, "n": -1}, 0)
    assert (retrieve(claim, 5, index=MATCHING_CARDINALITY_INDEX)
            == retrieve(claim, 5, index=COMPONENT_INDEPENDENCE_INDEX))
