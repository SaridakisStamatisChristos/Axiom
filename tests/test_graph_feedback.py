from hashlib import sha256
from itertools import combinations
import sqlite3

import pytest

from axiom import graph_feedback as feedback
from axiom.graph_claims import digest, stable
from axiom.graph_corpus import _initialize, file_digest
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_relations import AffineRelation


def _corpus(path, split, family, order, *, complete=True):
    graph = ExplicitGraph(order, tuple(combinations(range(order), 2)) if complete else ())
    line = graph.graph6()
    identity = sha256(line.encode("ascii")).hexdigest()
    with sqlite3.connect(path) as db:
        _initialize(db)
        db.execute("INSERT INTO sources VALUES (?,?,1,'',0)",
                   (family, stable({"split": split, "family": family})))
        db.execute("INSERT INTO graphs VALUES (?,?,?,?,?,?,?,?)",
                   (identity, line, split, order, len(graph.edges), order - 1 if complete else 0,
                    len(tuple(combinations(range(order), 3))) if complete else 0, 1 if complete else order))
        db.execute("INSERT INTO provenance VALUES (?,?)", (family, identity))
    return path


def test_feedback_uses_both_witness_sources_and_replays_before_and_after_final(tmp_path, monkeypatch):
    development = _corpus(tmp_path / "dev.sqlite", "development", "dev-cliques", 8)
    _corpus(development, "development", "dev-edgeless", 10, complete=False)
    final = _corpus(tmp_path / "final.sqlite", "final", "final-cliques", 11)
    ledger = tmp_path / "ledger.sqlite"
    corpus_claim, active_claim, final_claim = (
        AffineRelation.normalized({"clique": 1}, upper, "CONNECTED") for upper in (7, 9, 10)
    )
    known = AffineRelation.normalized({"edges": -1}, 0)

    def generate(training, novelty):
        assert novelty.classify(known)
        if 8 in training:
            assert training[8][0]["clique"] == 8
            assert training[10][0]["clique"] == 10
            assert 11 not in training
            return [(final_claim, ())], {}
        return [(claim, ()) for claim in (corpus_claim, active_claim, final_claim)], {}

    monkeypatch.setattr(feedback, "_discover", generate)
    panel = feedback._panel
    opened = []

    def track(path, split, config):
        opened.append((path, split))
        return panel(path, split, config)

    monkeypatch.setattr(feedback, "_panel", track)
    opts = {"final_sha256": file_digest(final)}
    report = feedback.run_campaign(development, ledger, "paired", **opts)
    assert opened == [(development, "development")]
    first, second = report["rounds"]
    assert [entry["stage"] for entry in first["feedback_added"]] == ["corpus", "active"]
    assert first["next_training_sha256"] == second["training_sha256"]
    assert set(second["training_counts"]) - set(first["training_counts"]) == {"8", "10"}
    assert first["trials"][0]["active"] is None
    assert first["trials"][1]["active"]["witness"]["graph"]["n"] == 10
    assert first["trials"][1]["corpus"]["coverage_by_order"].keys() == {"8", "10"}
    assert report["frozen_candidates"] == [final_claim.to_dict()]

    control = feedback.run_campaign(development, ledger, "control", feedback=False, **opts)
    assert control["rounds"][0]["trials"] == control["rounds"][1]["trials"]
    assert not control["rounds"][0]["feedback_added"]
    assert feedback.audit_campaign(development, ledger, "paired") == report
    with pytest.raises(ValueError, match="different parameters"):
        feedback.run_campaign(development, ledger, "paired", rounds=3, **opts)
    final_report = feedback.evaluate_final(final, ledger, "paired")
    assert final_report["trials"][0]["screen"]["witness"]["graph"]["n"] == 11
    assert feedback.evaluate_final(final, ledger, "paired") == final_report
    assert feedback.audit_campaign(development, ledger, "paired") == report

    with sqlite3.connect(ledger) as db:
        report["rounds"][0]["feedback_added"].clear()
        db.execute("UPDATE feedback_campaigns SET report=?, sha256=? WHERE name=?",
                   (stable(report), digest(report), "paired"))
    with pytest.raises(ValueError, match="deterministic replay"):
        feedback.audit_campaign(development, ledger, "paired")


@pytest.mark.parametrize(
    "family,order,committed,error",
    [
        ("dev-cliques", 11, True, "also registered"),
        ("final-cliques", 10, True, "above the development cutoff"),
        ("final-cliques", 11, False, "matching the sealed commitment"),
    ],
)
def test_final_requires_disjoint_families_orders_and_a_precommitted_file(
        tmp_path, monkeypatch, family, order, committed, error):
    development = _corpus(tmp_path / "dev.sqlite", "development", "dev-cliques", 8)
    final = _corpus(tmp_path / "final.sqlite", "final", family, order)
    ledger = tmp_path / "ledger.sqlite"
    monkeypatch.setattr(feedback, "_discover", lambda *_: ([], {}))
    monkeypatch.setattr(feedback, "_base_training", lambda _: ({}, {}))
    with pytest.raises(ValueError, match="dedicated development"):
        feedback.run_campaign(final, ledger, "mixed")
    commitment = file_digest(final) if committed else "0" * 64
    feedback.run_campaign(development, ledger, "sealed", final_sha256=commitment)
    with pytest.raises(ValueError, match=error):
        feedback.evaluate_final(final, ledger, "sealed")
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT final_report FROM feedback_campaigns").fetchone() == (None,)


def test_frontier_tests_fresh_claims_and_retains_survivors(tmp_path, monkeypatch):
    development = _corpus(tmp_path / "dev.sqlite", "development", "dev-cliques", 8)
    ledger = tmp_path / "ledger.sqlite"
    claims = [
        AffineRelation.normalized({"chromatic": 1}, 3, "TRIANGLE_FREE"),
        AffineRelation.normalized({"clique": 1}, 11),
        AffineRelation.normalized({"chromatic": 1}, 11),
    ]
    monkeypatch.setattr(feedback, "_discover", lambda *_: ([(c, ()) for c in claims], {}))
    monkeypatch.setattr(feedback, "_base_training", lambda _: ({}, {}))
    report = feedback.run_campaign(development, ledger, "frontier", rounds=3, candidates=1,
                                   profile=feedback.FRONTIER_PROFILE, feedback=False,
                                   development_order=11, active_budget=4)
    assert [r["trials"][0]["candidate_id"] for r in report["rounds"]] == [c.id for c in claims]
    witness = report["rounds"][0]["trials"][0]["active"]["witness"]
    assert witness["graph"]["n"] == 11
    assert witness["checked_properties"]["triangle_free"]
    assert witness["checked_properties"]["chromatic"] == 4
    assert report["frozen_candidates"] == [c.to_dict() for c in claims[1:]]
    assert feedback.audit_campaign(development, ledger, "frontier") == report


def test_frontier_removes_an_earlier_survivor_if_a_later_graph_refutes_it(
        tmp_path, monkeypatch):
    development = _corpus(tmp_path / "dev.sqlite", "development", "dev-edgeless", 8, complete=False)
    ledger = tmp_path / "ledger.sqlite"
    second = AffineRelation.normalized({"chromatic": 1}, 3, "TRIANGLE_FREE")
    first = AffineRelation.normalized({"chromatic": 1}, 3, "CONNECTED")
    monkeypatch.setattr(feedback, "_discover", lambda *_: ([(first, ()), (second, ())], {}))
    monkeypatch.setattr(feedback, "_base_training", lambda _: ({}, {}))
    search = feedback.search
    monkeypatch.setattr(feedback, "search",
                        lambda claim, *args, **kwargs: {"witness": None} if claim == first
                        else search(claim, *args, **kwargs))
    report = feedback.run_campaign(development, ledger, "cross", candidates=1,
                                   profile=feedback.FRONTIER_PROFILE, development_order=11)
    assert report["rounds"][0]["carried_survivors"] == 1
    cross, = report["rounds"][1]["cross_refutations"]
    assert cross["candidate_id"] == first.id and cross["source_candidate_id"] == second.id
    assert feedback.replay_witness(first, cross["witness"])
    assert report["frozen_candidates"] == []


def test_component_frontier_refutes_and_replays_odd_cycle_union(tmp_path, monkeypatch):
    development = _corpus(tmp_path / "dev.sqlite", "development", "dev-edgeless", 8, complete=False)
    ledger = tmp_path / "ledger.sqlite"
    claim = AffineRelation.normalized({"n": 1, "independence": -1, "matching": -1}, 1, "TRIANGLE_FREE")
    monkeypatch.setattr(feedback, "_discover", lambda *_: ([(claim, ())], {}))
    monkeypatch.setattr(feedback, "_base_training", lambda _: ({}, {}))
    options = dict(rounds=2, candidates=1, development_order=10, active_budget=1)
    legacy = feedback.run_campaign(development, ledger, "legacy", profile=feedback.FRONTIER_PROFILE, **options)
    assert legacy["frozen_candidates"] == [claim.to_dict()]
    assert feedback.audit_campaign(development, ledger, "legacy") == legacy
    report = feedback.run_campaign(development, ledger, "components",
                                   profile=feedback.COMPONENT_FRONTIER_PROFILE, **options)
    first, second = report["rounds"]
    trial, = first["trials"]
    assert trial["corpus"]["witness"] is None
    assert trial["outcome"] == "REFUTED"
    witness = trial["active"]["witness"]
    assert feedback.replay_witness(claim, witness)
    props = witness["checked_properties"]
    assert (props["n"], props["components"], props["independence"], props["matching"]) == (10, 2, 4, 4)
    assert len(first["feedback_added"]) == 1
    assert "10" not in first["training_counts"] and second["training_counts"]["10"] == 1
    assert report["frozen_candidates"] == []
    assert feedback.audit_campaign(development, ledger, "components") == report



def test_component_frontier_keeps_the_mycielski_seed_for_chromatic_claim():
    claim = AffineRelation.normalized({"chromatic": 1}, 3, "TRIANGLE_FREE")
    seeds = feedback.frontier_seeds(11, claim.bound.assumption, component_claim=claim)
    report = feedback.search(claim, seeds, budget=1, profile="guided-v3", max_order=11)
    assert report["witness"]["graph"]["n"] == 11
