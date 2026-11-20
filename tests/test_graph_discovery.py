from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import sqlite3

import pytest

from axiom import graph_discovery as discovery
from axiom import graph_discovery_lean as handoff
from axiom.graph_affine import INVARIANTS
from axiom.graph_affine_lean_n3 import audit_n3_affine, build_n3_affine_source
from axiom.graph_checker import reference_properties
from axiom.graph_relations import AffineRelation, implies, known_fact


def claim(weights, bound, assumption="ALL", relation="<="):
    return AffineRelation.normalized(weights, bound, assumption, relation)


def test_exact_normalization_respects_integer_lattice_and_equality_orientation():
    assert claim({"edges": 2, "triangles": -2}, -1) == claim(
        {"edges": 1, "triangles": -1}, -1)
    original = claim({"edges": 1, "triangles": -1}, 2, relation="=")
    scaled = claim({"triangles": Fraction(3, 2), "edges": Fraction(-3, 2)}, -3,
                   relation="=")
    assert AffineRelation.from_dict(scaled.to_dict()).id == original.id
    assert original.id != claim({"edges": 1, "triangles": -1}, 2).id
    with pytest.raises(ValueError, match="nonintegral"):
        claim({"edges": 2, "triangles": -2}, 1, relation="=")


def test_symbolic_filter_checks_direction_scope_and_both_sides():
    assert known_fact(claim({"clique": 1, "chromatic": -1}, 0))
    assert known_fact(claim({"clique": 1, "chromatic": -1}, 0, "BIPARTITE", "="))
    assert not known_fact(claim({"clique": 1, "chromatic": -1}, 0, "ALL", "="))
    strong = claim({"edges": 1, "triangles": -1}, 3)
    weak = claim({"edges": 1, "triangles": -1}, 4, "BIPARTITE")
    assert implies(strong, weak)
    assert not implies(weak, strong)
    history = [(0, reference_properties(7, 0))]
    selected, _, reasons = discovery._select([(weak, (1,)), (strong, (0,))], history, 4)
    assert [entry[0] for entry in selected] == [strong]
    assert reasons["SYMBOLIC_DOMINATION"] == 1


def test_discovers_equalities_without_hardcoding_the_invariant_pair():
    training = {}
    for n in (5, 6, 7):
        training[n] = [{**dict.fromkeys(INVARIANTS, 0), "n": n, "edges": e,
                        "triangles": e, "connected": False, "bipartite": False,
                        "triangle_free": False} for e in (1, 2, 3)]
    bank, counts = discovery._discover(training)
    equality = claim({"edges": 1, "triangles": -1}, 0, relation="=")
    assert counts["EQUALITY_PROPOSED"] > 0
    assert any(candidate == equality for candidate, _ in bank)
    assert discovery._failed_side(equality, reference_properties(5, 1)) == equality.bound
    # Exercise the reverse half of the equality on a dense graph (35 triangles, 21 edges).
    opposite = discovery._failed_side(equality, reference_properties(7, (1 << 21) - 1))
    assert opposite == equality.inequalities()[1]


@pytest.fixture
def campaign_source(monkeypatch, tmp_path):
    source_db = tmp_path / "historical.sqlite3"
    source_db.touch()
    monkeypatch.setattr(discovery, "_source", lambda *_: (
        "source-fingerprint", set(range(64)), {"fixture": 1}, {"v18": "digest"}, {80}))
    return source_db, tmp_path / "ledger.sqlite3"


def test_ledger_reserves_unique_masks_concurrently_and_rejects_tampering(
        monkeypatch, campaign_source, tmp_path):
    db, ledger = campaign_source
    candidate = claim({"edges": -1, "triangles": -1}, 0)
    monkeypatch.setattr(discovery, "_discover", lambda _: ([(candidate, (1,))], {}))
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(
            lambda name: discovery.run_campaign(db, ledger, name, holdout_budget=8),
            ("first", "second")))
    assert len(discovery._pairs(first)) == len(discovery._pairs(second)) == 8
    assert discovery._pairs(first).isdisjoint(discovery._pairs(second))
    assert (7, 80) not in discovery._pairs(first) | discovery._pairs(second)
    assert discovery.run_campaign(db, ledger, "first", holdout_budget=8) == first
    with pytest.raises(ValueError, match="different parameters"):
        discovery.run_campaign(db, ledger, "first", holdout_budget=9)
    assert discovery.audit_campaign(db, ledger, "second") == second
    export = tmp_path / "tampered.json"
    export.write_text(json.dumps({**second, "candidate_count": 4000}))
    with pytest.raises(ValueError, match="exported campaign differs"):
        discovery.audit_campaign(db, ledger, "second", artifact=export)
    with sqlite3.connect(ledger) as connection:
        connection.execute("DELETE FROM checked_masks")
    with pytest.raises(ValueError, match="mask index"):
        discovery.audit_campaign(db, ledger, "second")


def test_zero_candidates_preserve_machine_readable_rejection(monkeypatch, campaign_source):
    db, ledger = campaign_source
    monkeypatch.setattr(discovery, "_discover", lambda _: ([], {"SYMBOLIC_REDUNDANCY": 3}))
    report = discovery.run_campaign(db, ledger, "empty")
    assert report["selection_status"] == "NO_CANDIDATE_PASSED_DISCOVERY_FILTERS"
    assert report["discovery_counts"]["SYMBOLIC_REDUNDANCY"] == 3
    assert report["trials"] == []
    assert handoff.dispatch_lean(db, ledger, "empty")["results"] == []


def test_lean_dispatch_binds_survivors_and_replays_refutation(monkeypatch):
    survivor = claim({"clique": 1, "components": 1}, 4, "CONNECTED")
    false = claim({"edges": -1, "triangles": 1}, -4)
    monkeypatch.setattr(handoff, "audit_campaign", lambda *_a, **_kw: {
        "trials": [{"statement": item.to_dict(), "status": "EXPERIMENTALLY_SURVIVING"}
                   for item in (survivor, false)]})

    def unavailable(statement, **kwargs):
        assert kwargs["extended"] is True
        assert statement == survivor.bound.to_dict()
        return {**build_n3_affine_source(statement, extended=True),
                "status": "LEAN_UNAVAILABLE", "accepted": False, "lean_kernel_executed": False}

    monkeypatch.setattr(handoff, "verify_n3_affine", unavailable)
    output = handoff.dispatch_lean("db", "ledger", "trial")
    success, refutation = output["results"]
    assert success["candidate_id"] == survivor.id
    assert success["status"] == "FIXED_ORDER_PROOF_PENDING"
    assert audit_n3_affine(success["proof_records"][0])
    assert "2 ≤ edgeCount mask.val →" in success["proof_records"][0]["source"]
    assert refutation["status"] == "REFUTED_BY_EXACT_ORDER_PRECHECK"
    assert refutation["counterexample"]["independent_witness_check"] == (
        "ACCEPTED_BOTH_GRAPH_ORACLES")
    assert output["universal_theorems_promoted"] == 0
