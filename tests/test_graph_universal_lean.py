from copy import deepcopy

import pytest

from axiom import graph_universal_lean as universal
from axiom.graph_relations import AffineRelation
from axiom.lean_backend import LeanBackendError


def relation(weights, upper, assumption="ALL", operator="<="):
    return AffineRelation.normalized(weights, upper, assumption, operator)


def trial(claim, status="EXPERIMENTALLY_SURVIVING", witness=None):
    return {"candidate_id": claim.id, "statement": claim.to_dict(),
            "status": status, "counterexample": witness}


@pytest.mark.parametrize(("weights", "bound", "premise", "lemma"), [
    ({"clique": 1, "triangles": -1}, 2, "ALL", "clique_le_triangles_add_two"),
    ({"clique": 1, "chromatic": -1}, 0, "ALL", "clique_le_chromatic"),
    ({"edges": -1, "components": -1, "n": 1}, 0, "CONNECTED", "connected_component_edge_bound"),
    ({"maximum_degree": 1, "independence": -1}, 0, "TRIANGLE_FREE", "triangle_free_degree_bound"),
    ({"matching": 1, "edges": -1}, 0, "ALL", "matching_le_edges"),
])
def test_exact_universal_goal_and_scope(weights, bound, premise, lemma):
    claim = relation(weights, bound, premise)
    record = universal.build_universal_source(claim.to_dict())
    assert record["matched_lemmas"] == [lemma]
    assert "(n : Nat) (G : SimpleGraph (Fin n))" in record["source"]
    assert "Fin 8" not in record["source"]
    assert record["statement"] == claim.to_dict()
    assert "sorry" not in record["source"]


def test_matcher_preserves_scope_direction_and_both_sides_of_equality():
    assert universal.build_universal_source(
        relation({"clique": 1, "triangles": -1}, 1).to_dict()) is None
    assert universal.build_universal_source(
        relation({"edges": -1, "components": -1, "n": 1}, 0).to_dict()) is None
    assert universal.build_universal_source(
        relation({"clique": 1, "chromatic": -1}, 0, operator="=").to_dict()) is None
    assert universal.build_universal_source(
        relation({"clique": 1, "triangles": -1}, 3).to_dict()) is not None


def test_dispatch_replays_source_scope_and_rejects_counterexample_tampering(monkeypatch):
    supported = trial(relation({"clique": 1, "triangles": -1}, 2))
    unsupported = trial(relation({"chromatic": 1, "clique": -1}, 1))
    witness = {"exact_order": 7, "labelled_edge_mask": 1}
    refuted = trial(relation({"edges": 1, "triangles": -1}, 0), "REFUTED", witness)
    monkeypatch.setattr(universal, "audit_campaign", lambda *a, **k: {
        "trials": [supported, unsupported, refuted]})

    calls = []

    def unavailable(generated, *args, **kwargs):
        calls.append(generated)
        return {**generated, "accepted": False, "status": "LEAN_UNAVAILABLE",
                "offline_audit_is_execution_attestation": False}

    monkeypatch.setattr(universal, "run_affine_kernel", unavailable)
    report = universal.dispatch_universal("db", "ledger", "campaign")
    assert len(calls) == 1
    assert [result["handoff"] for result in report["results"]] == [
        "PENDING_LEAN_UNAVAILABLE", "PENDING_UNSUPPORTED_RELATION", "REFUTED_WITH_WITNESS"]
    assert universal.audit_dispatch("db", "ledger", "campaign", report) == report

    forged = deepcopy(report)
    forged["results"][2]["counterexample"]["labelled_edge_mask"] = 2
    with pytest.raises(ValueError, match="differs from replay"):
        universal.audit_dispatch("db", "ledger", "campaign", forged)
    forged = deepcopy(report)
    forged["results"][0]["proof"]["source"] += "\n-- Tampered\n"
    with pytest.raises(LeanBackendError, match="altered"):
        universal.audit_dispatch("db", "ledger", "campaign", forged)
    forged = deepcopy(report)
    forged["results"][0]["proof"].update(accepted=True, status="FORMALLY_VERIFIED")
    with pytest.raises(LeanBackendError, match="invalid successful"):
        universal.audit_dispatch("db", "ledger", "campaign", forged)
