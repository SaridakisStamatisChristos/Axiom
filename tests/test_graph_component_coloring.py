"""Check the component facts through the proof and replay entry points."""
import os
from pathlib import Path

import pytest

from axiom.graph_lemma_retrieval import COMPONENT_INDEX, MATCHING_INDEX
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(("weights", "rhs", "premise", "adapter"), (
    ({"chromatic": 1, "components": 1, "n": -1}, 1, "ALL",
     "retrieved_chromatic_add_components_le_order_add_one"),
    ({"clique": 1, "components": 1, "n": -1}, 1, "ALL",
     "retrieved_chromatic_add_components_le_order_add_one"),
    ({"components": 1}, 1, "CONNECTED", "retrieved_connected_components_le_one"),
))
def test_component_bound_certifies_and_replays(weights, rhs, premise, adapter, tmp_path):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    baseline = prove(statement, retrieval_limit=5, retrieval_index=MATCHING_INDEX,
                     project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED" and audit(baseline)

    real = os.environ.get("AXIOM_REAL_LEAN") == "1"
    result = prove(statement, retrieval_limit=5, retrieval_index=COMPONENT_INDEX,
                   project_root=ROOT if real else tmp_path)
    assert result["status"] == ("FORMALLY_VERIFIED" if real else "LEAN_UNAVAILABLE"), result["kernel"]
    assert result["scope"] == "ALL_GRAPH_ORDERS"
    assert adapter in {lemma["theorem"] for side in result["derivation"]["directions"]
                       for lemma in side["lemmas"]}
    assert audit(result)


def test_connected_component_count_does_not_leak_to_arbitrary_graphs(tmp_path):
    statement = AffineRelation.normalized({"components": 1}, 1).to_dict()
    result = prove(statement, retrieval_limit=5, retrieval_index=COMPONENT_INDEX,
                   project_root=tmp_path)
    assert result["status"] == "COUNTEREXAMPLE"
    assert result["counterexample"]["graph"] == {"n": 2, "edges": []}
    assert result["generated"] is None and audit(result)
