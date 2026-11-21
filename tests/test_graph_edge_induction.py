"""Check induction evidence, composition and failure boundaries."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from axiom.graph_affine_lean_n3 import run_affine_kernel
from axiom.graph_claims import digest
from axiom.graph_edge_induction import EDGE_INDUCTION_RULE
from axiom.graph_proof import INDUCTION_SCHEMA, audit, prove
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation
from axiom.graph_universal_lean import PINNED_MATHLIB_SHA

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "research/proof_engine/edge_induction_targets.json"
WEIGHTS = {"n": 1, "edges": -1, "independence": -1}


@pytest.mark.parametrize("_name,premise,weights,rhs,companion", json.loads(SUITE.read_text()))
def test_induction_extends_existing_search(tmp_path, _name, premise, weights, rhs, companion):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    options = dict(project_root=tmp_path, retrieval_limit=5, synthesis_limit=3, split_order=True)
    before = prove(statement, **options)
    after = prove(statement, induct_edges=True, **options)
    assert before["status"] == "SEARCH_EXHAUSTED"
    assert after["schema"] == INDUCTION_SCHEMA and after["status"] == "LEAN_UNAVAILABLE"
    induction = after["edge_induction"]
    assert induction["attempted"] and induction["initial_derivation"] == before["derivation"]
    assert induction["selected_fact"] == EDGE_INDUCTION_RULE.theorem
    used = {lemma["theorem"] for direction in after["derivation"]["directions"]
            for lemma in direction["lemmas"]}
    assert {companion, induction["selected_fact"]} <= used
    source = after["generated"]["source"]
    assert "using Nat.strong_induction_on generalizing G" in source
    assert source.index("private theorem " + induction["selected_fact"]) < source.index("theorem composite_")
    assert ("by_cases hz : n = 0" in source) == (companion == "order_clique_positive")
    assert audit(before) and audit(after)


def test_counterexample_precedes_induction(tmp_path):
    statement = AffineRelation.normalized(WEIGHTS, -1).to_dict()
    attempt = prove(statement, induct_edges=True, project_root=tmp_path)
    assert attempt["status"] == "COUNTEREXAMPLE"
    assert attempt["counterexample"]["exact_order"] == 0
    assert attempt["counterexample"]["labelled_edge_mask"] == 0
    assert not attempt["edge_induction"]["attempted"] and attempt["generated"] is None
    assert audit(attempt)


def test_shared_budget_and_exhausted_search(tmp_path):
    statement = AffineRelation.normalized(WEIGHTS, 0).to_dict()
    before = prove(statement, project_root=tmp_path)
    max_nodes = before["derivation"]["nodes"]
    for extra in (0, 1):
        limits = SearchLimits(max_nodes=max_nodes + extra)
        result = prove(statement, induct_edges=True, limits=limits, project_root=tmp_path)
        assert result["reason"] == "NODE_BUDGET_EXHAUSTED"
        assert result["derivation"]["nodes"] == limits.max_nodes
        assert result["edge_induction"]["attempted"] == bool(extra)
        assert result["generated"] is None and audit(result)

    # This is true through order five, but refuted by the complete graph on six vertices.
    outside_bank = AffineRelation.normalized({"n": -2, "edges": 1}, 0).to_dict()
    result = prove(outside_bank, induct_edges=True, project_root=tmp_path)
    assert result["status"] == "SEARCH_EXHAUSTED" and result["edge_induction"]["attempted"]
    assert result["edge_induction"]["selected_fact"] is None and result["generated"] is None
    assert audit(result)


def test_induction_skips_existing_derivations_and_rejects_tampering(tmp_path):
    easy = AffineRelation.normalized({"components": 1, "n": -1}, 0).to_dict()
    before = prove(easy, project_root=tmp_path)
    after = prove(easy, induct_edges=True, project_root=tmp_path)
    assert after["generated"] == before["generated"] and not after["edge_induction"]["attempted"]
    assert audit(after)

    statement = AffineRelation.normalized(WEIGHTS, 0).to_dict()
    attempt = prove(statement, induct_edges=True, project_root=tmp_path)
    tampered = deepcopy(attempt)
    tampered["edge_induction"]["selected_fact"] = None
    tampered["record_sha256"] = digest({k: v for k, v in tampered.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(tampered)
    with pytest.raises(ValueError, match="invalid edge induction option"):
        prove(statement, induct_edges=1, project_root=tmp_path)


@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
def test_lean_rejects_induction_applied_to_stronger_false_goal(tmp_path):
    statement = AffineRelation.normalized(WEIGHTS, 0).to_dict()
    prepared = prove(statement, induct_edges=True, project_root=tmp_path)["generated"]
    helpers, theorem = prepared["source"].split("\ntheorem composite_", 1)
    changed = theorem.replace("≤ (0 : Int) := by", "≤ (-1 : Int) := by", 1)
    assert changed != theorem
    source = helpers + "\ntheorem composite_" + changed
    result = run_affine_kernel(
        {**prepared, "source": source, "source_sha256": sha256(source.encode()).hexdigest()},
        ROOT, 180, "FORMALLY_VERIFIED", expected_mathlib_revision=PINNED_MATHLIB_SHA,
        retain_logs=True,
    )
    assert result["lean_kernel_executed"] and result["checker_exit_code"] != 0
    assert not result["accepted"] and "omega" in result["stdout"]
