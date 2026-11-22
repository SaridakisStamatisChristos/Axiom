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
