"""Check statement binding, bounded hint scheduling and replay."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_proof import HINT_ATTEMPT_SCHEMA, audit, hint_context, prove
from axiom.graph_proof_hints import MAX_HINT_BYTES, read_hints
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
CLAIM = AffineRelation.normalized({"matching": 5, "edges": -6}, 0).to_dict()


def hints_for(statement, plans, **options):
    context = hint_context(statement, **options)
    return {**context["response_template"], "plans": plans}


def test_hints_share_budgets_and_use_only_eligible_facts(tmp_path):
    limits = SearchLimits(max_lemmas=1)
    options = {"plan_limit": 2, "limits": limits}
    context = hint_context(CLAIM, **options)
    assert context["status"] == "PLAN_SEARCH_READY" and context["plan_slots"] == 2
    assert context["statement"] == CLAIM and context["statement_sha256"] == digest(CLAIM)
    assert "matching_le_edges" in {fact["theorem"] for fact in context["facts"]}
    assert all(fact["premise"] == "ALL" and fact["scope"] == "GLOBAL" for fact in context["facts"])
    hints = hints_for(CLAIM, [
        ["connected_edge_bound"], ["unknown_fact"],
        ["matching_le_edges", "components_le_order"], ["matching_le_edges"],
        ["matching_le_edges"], ["components_le_order"],
    ], **options)
    result = prove(CLAIM, proof_hints=hints, project_root=tmp_path, **options)
    info = result["proof_hints"]
    assert result["schema"] == HINT_ATTEMPT_SCHEMA and result["status"] == "LEAN_UNAVAILABLE"
    assert info["hint_indices"] == [None, 3]
    assert [r["reason"] for r in info["rejected"]] == [
        "FACT_UNAVAILABLE", "FACT_UNAVAILABLE", "LEMMA_LIMIT", "DUPLICATE", "PLAN_LIMIT",
    ]
    assert result["proof_plans"]["candidates"] == [[], ["matching_le_edges"]]
    assert audit(result)
    tampered = deepcopy(result)
    tampered["proof_hints"]["hint_indices"][1] = 0
    tampered["record_sha256"] = digest({k: v for k, v in tampered.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(tampered)


def test_context_respects_scope_and_earlier_results(tmp_path):
    claim = AffineRelation.normalized({"n": 1, "edges": -1, "clique": -1, "triangles": -1},
                                     0, "CONNECTED").to_dict()
    context = hint_context(claim, plan_limit=2, split_order=True)
    facts = {fact["theorem"]: fact for fact in context["facts"]}
    assert facts["order_clique_positive"]["scope"] == "POSITIVE_ORDER"
    assert facts["connected_edge_bound"]["premise"] == "CONNECTED"
    plain = hint_context(claim, plan_limit=2)
    assert "order_clique_positive" not in {fact["theorem"] for fact in plain["facts"]}

    witness = AffineRelation.normalized({"clique": 1}, 1).to_dict()
    context = hint_context(witness, plan_limit=2)
    assert context["status"] == "COUNTEREXAMPLE" and not context["facts"]
    hints = {**context["response_template"], "plans": [["clique_le_chromatic"]]}
    record = prove(witness, plan_limit=2, proof_hints=hints, project_root=tmp_path)
    assert record["counterexample"] and record["generated"] is None and audit(record)
    known = AffineRelation.normalized({"matching": 1, "edges": -1}, 0).to_dict()
    context = hint_context(known, plan_limit=2)
    assert context["status"] == "EXACT_DERIVATION_READY" and context["plan_slots"] == 0


def test_hint_envelope_rejects_stale_and_open_ended_input(tmp_path):
    valid = hints_for(CLAIM, [["matching_le_edges"]], plan_limit=2)
    for hint, error in (
        ({**valid, "statement_sha256": "0" * 64}, "statement digest"),
        ({**valid, "lean": "omega"}, "schema"),
        ({**valid, "plans": [["matching_le_edges\n  omega"]]}, "fact bundle"),
        ({**valid, "plans": [["matching_le_edges"] * 2]}, "fact bundle"),
        ({**valid, "plans": [["matching_le_edges"]] * 17}, "plan count"),
    ):
        with pytest.raises(ValueError, match=error):
            prove(CLAIM, plan_limit=2, proof_hints=hint, project_root=tmp_path)
    with pytest.raises(ValueError, match="positive proof plan limit"):
        prove(CLAIM, proof_hints=valid, project_root=tmp_path)

    path = tmp_path / "hints.json"
    path.write_text(json.dumps(valid), encoding="utf-8")
    assert read_hints(path) == valid
    for content, error in (
        ("null", "JSON object"),
        ('{"plans":[],"plans":[]}', "duplicate key"),
        (" " * (MAX_HINT_BYTES + 1), "16 KiB"),
    ):
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match=error):
            read_hints(path)


@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
def test_wrong_hint_backtracks_to_ranked_plan():
    hints = hints_for(CLAIM, [["components_le_order"]], plan_limit=3)
    result = prove(CLAIM, proof_hints=hints, plan_limit=3, project_root=ROOT)
    assert result["proof_plans"]["candidates"] == [[], ["components_le_order"], ["matching_le_edges"]]
    assert result["proof_hints"]["hint_indices"] == [None, 0, None]
    assert result["status"] == "FORMALLY_VERIFIED"
    assert result["proof_plans"]["accepted_index"] == 2 and audit(result)


@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
def test_hints_cannot_certify_a_false_goal_beyond_the_witness_budget():
    # The complete graph on six vertices has 15 edges and violates this bound.
    claim = AffineRelation.normalized({"edges": 1, "n": -2}, 0).to_dict()
    hints = hints_for(claim, [["matching_le_edges", "components_le_order"]], plan_limit=2)
    result = prove(claim, proof_hints=hints, plan_limit=2, project_root=ROOT)
    assert result["counterexample"] is None and result["kernel"]["lean_kernel_executed"]
    assert result["status"] == "LEAN_REJECTED" and result["proof_plans"]["accepted_index"] is None
    assert result["proof_hints"]["hint_indices"] == [None, 0] and audit(result)
