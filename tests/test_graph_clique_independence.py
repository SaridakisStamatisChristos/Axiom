"""Check the joint clique and independence bound and its compositions."""
import os
from pathlib import Path

import pytest

from axiom.graph_lemma_retrieval import CLIQUE_INDEPENDENCE_INDEX, MATCHING_CARDINALITY_INDEX, retrieve
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
JOINT = {"clique": 1, "independence": 1, "n": -1}


@pytest.mark.parametrize(("weights", "rhs", "other_lemma"), (
    (JOINT, 1, None),
    ({**JOINT, "matching": 1, "edges": -1}, 1, "matching_le_edges"),
    ({**JOINT, "chromatic": 1, "maximum_degree": -1}, 2, "retrieved_chromatic_le_degree_add_one"),
))
def test_joint_bound_certifies_and_composes(weights, rhs, other_lemma, tmp_path):
    statement = AffineRelation.normalized(weights, rhs).to_dict()
    baseline = prove(statement, retrieval_limit=5, retrieval_index=MATCHING_CARDINALITY_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED" and audit(baseline)

    real = os.environ.get("AXIOM_REAL_LEAN") == "1"
    result = prove(statement, retrieval_limit=5, retrieval_index=CLIQUE_INDEPENDENCE_INDEX,
                   project_root=ROOT if real else tmp_path)
    assert result["status"] == ("FORMALLY_VERIFIED" if real else "LEAN_UNAVAILABLE"), result["kernel"]
    assert result["scope"] == "ALL_GRAPH_ORDERS"
    expected = {"retrieved_clique_add_independence_le_order_add_one"}
    if other_lemma is not None:
        expected.add(other_lemma)
    assert {lemma["theorem"] for side in result["derivation"]["directions"]
            for lemma in side["lemmas"]} == expected
    assert audit(result)


def test_joint_bound_is_tight(tmp_path):
    statement = AffineRelation.normalized(JOINT, 0).to_dict()
    result = prove(statement, retrieval_limit=5, retrieval_index=CLIQUE_INDEPENDENCE_INDEX,
                   project_root=tmp_path)
    assert result["status"] == "COUNTEREXAMPLE"
    assert result["counterexample"]["graph"] == {"n": 1, "edges": []}
    assert result["generated"] is None and audit(result)


def test_single_invariant_goal_preserves_retrieval_slots():
    claim = AffineRelation.normalized({"independence": 1, "n": -1}, 0)
    assert (retrieve(claim, 5, index=CLIQUE_INDEPENDENCE_INDEX)
            == retrieve(claim, 5, index=MATCHING_CARDINALITY_INDEX))
