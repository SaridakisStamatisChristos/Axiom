"""Check affine projection arithmetic, proof ancestry and budget boundaries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from axiom.graph_affine import VARIABLES
from axiom.graph_claims import digest
from axiom.graph_lemma_synthesis import synthesize
from axiom.graph_proof import SYNTHESIS_SCHEMA, audit, prove
from axiom.graph_proof_search import LemmaSpec, SearchLimits
from axiom.graph_relations import AffineRelation, _vector

SUITE = Path(__file__).resolve().parents[1] / "research/proof_engine/synthesis_targets.json"


@pytest.mark.parametrize("_name,premise,weights,rhs,pivot", json.loads(SUITE.read_text()))
def test_projection_extends_retrieval_and_archives_dependencies(tmp_path, _name, premise, weights, rhs, pivot):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    fixed = prove(statement, retrieval_limit=5, project_root=tmp_path)
    found = prove(statement, retrieval_limit=5, synthesis_limit=3, project_root=tmp_path)
    assert fixed["status"] == "SEARCH_EXHAUSTED"
    assert found["schema"] == SYNTHESIS_SCHEMA
    assert found["status"] == "LEAN_UNAVAILABLE"
    assert found["synthesis"]["initial_derivation"] == fixed["derivation"]
    lemmas = found["derivation"]["directions"][0]["lemmas"]
    assert len(lemmas) == 3
    step = next(s for s in found["synthesis"]["selected"] if s["pivot"] == pivot)
    assert step["lemma"]["theorem"] in {lemma["theorem"] for lemma in lemmas}
    source = found["generated"]["source"]
    for parent in step["parents"]:
        theorem = parent["lemma"]["theorem"]
        if theorem.startswith("retrieved_"):
            assert source.index("private theorem " + theorem) < source.index("private theorem " + step["lemma"]["theorem"])
    assert audit(fixed) and audit(found)


def test_projection_gcd_rounding_premises_and_order():
    left = LemmaSpec("left", "ALL", _vector((("n", 2), ("clique", 2))), 1)
    right = LemmaSpec("right", "CONNECTED", _vector((("n", -3), ("edges", 2))), -2)
    target = {"clique": 3, "edges": 2}
    assert not synthesize(AffineRelation.normalized(target, -1), (left, right), 2)
    claim = AffineRelation.normalized(target, -1, "CONNECTED")
    steps = synthesize(claim, (left, right), 1)
    assert steps == synthesize(claim, (right, left), 1)
    step, = steps
    assert step.lemma.vector == _vector(target.items()) and step.lemma.rhs == -1
    assert step.lemma.premise == "CONNECTED" and step.pivot == "n" and step.divisor == 2
    assert step.parents == ((left, 3), (right, 2))
    pivot_index = VARIABLES.index(step.pivot)
    assert sum(parent.vector[pivot_index] * scale for parent, scale in step.parents) == 0


def test_projection_budget_and_tampering(tmp_path):
    statement = AffineRelation.normalized({"edges": -1}, 0, "CONNECTED").to_dict()
    limits = SearchLimits(max_lemmas=1)
    baseline = prove(statement, limits=limits, project_root=tmp_path)
    assert baseline["status"] == "SEARCH_EXHAUSTED"
    result = prove(statement, limits=limits, synthesis_limit=1, project_root=tmp_path)
    assert result["derivation"]["derived"] and audit(result)
    exhausted = prove(statement, limits=SearchLimits(max_lemmas=1, max_nodes=1),
                      synthesis_limit=1, project_root=tmp_path)
    assert exhausted["reason"] == "NODE_BUDGET_EXHAUSTED"
    assert not exhausted["synthesis"]["attempted"] and audit(exhausted)
    bad = deepcopy(result)
    bad["synthesis"]["selected"][0]["parents"][0]["coefficient"] += 1
    bad["record_sha256"] = digest({key: val for key, val in bad.items() if key != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(bad)


def test_projection_skips_counterexamples_and_validates_limit(tmp_path):
    statement = AffineRelation.normalized({"chromatic": 1}, 2).to_dict()
    witness = prove(statement, retrieval_limit=5, synthesis_limit=3, project_root=tmp_path)
    assert witness["status"] == "COUNTEREXAMPLE"
    assert not witness["synthesis"]["attempted"] and not witness["retrieval"]["attempted"]
    assert audit(witness)
    for invalid in (True, -1, 33):
        with pytest.raises(ValueError, match="invalid lemma synthesis limit"):
            prove(statement, synthesis_limit=invalid)
