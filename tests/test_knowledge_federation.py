"""Adversarial evidence and typed source federation regression."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.graph_campaign import run_graph_campaign
from axiom.research import run_campaign
from axiom.number_theory_campaign import run_nt_campaign
from axiom.recurrences import sequence_campaign
from axiom.knowledge_graph import build_knowledge_graph, knowledge_summary
from axiom.knowledge_federation import federate, federation_summary, query_federation


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    root = tmp_path_factory.mktemp("federated")
    graph = root / "graph.json"
    algebra = root / "algebra.json"
    number = root / "number.json"
    recurrence = root / "recurrence.json"
    run_graph_campaign(str(root / "graph.sqlite3"), seed=42, candidates=65,
                       max_order=6, search_budget=55, report_path=str(graph))
    run_campaign(str(root / "algebra.sqlite3"), seed=42, candidates=55,
                 domain="mixed", lower=-8, upper=8, max_evals=100,
                 report_path=str(algebra))
    run_nt_campaign(str(root / "number.sqlite3"), seed=42, candidates=55,
                    lower=-8, upper=8, max_evals=100, report_path=str(number))
    recurrence.write_text(json.dumps(sequence_campaign(42, 7)), encoding="utf-8")
    return graph, algebra, number, recurrence


def make_db(tmp_path, sources):
    path = str(tmp_path / "knowledge.sqlite3")
    build_knowledge_graph(path, [str(sources[0])])
    return path


def test_four_domains_and_repeatable_import(tmp_path, sources):
    db = make_db(tmp_path, sources)
    files = [str(x) for x in sources[1:]]
    first = federate(db, files)
    assert first == federate(db, files)
    assert first["audit"] == "ACCEPTED"
    assert first["distinct_statements_by_domain"].keys() == {
        "graph", "algebra", "number_theory", "recurrence"}
    assert first["distinct_statements_by_domain"]["recurrence"] == 7
    assert first["counts"]["local_proof"] > 0
    assert first["counts"]["counterexample"] > 0
    assert first["lean_verification_in_federation"] == "NOT_IMPORTED"
    assert knowledge_summary(db)["audit"] == "ACCEPTED"  # original v0.6 untouched
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_domain_separation_and_epistemic_labels(tmp_path, sources):
    db = make_db(tmp_path, sources)
    federate(db, [str(x) for x in sources[1:]])
    graph = query_federation(db, domain="graph", limit=100)
    number = query_federation(db, domain="number_theory", limit=100)
    assert graph and number
    assert all(f["domain"] == "graph" for f in graph)
    assert all(f["domain"] == "number_theory" for f in number)
    assert set(f["statement_id"] for f in graph).isdisjoint(
        f["statement_id"] for f in number)
    for finding in graph + number:
        assert "FORMALLY_VERIFIED" not in finding["statuses"]
    recurrence = query_federation(db, domain="recurrence", limit=100)
    assert len(recurrence) == 7
    assert all(f["statuses"] == ["PROVED_IN_SUPPORTED_FRAGMENT"] for f in recurrence)
    assert query_federation(db, domain="algebra", status="REFUTED", limit=10)


def test_tampered_federation_link_is_rejected(tmp_path, sources):
    db = make_db(tmp_path, sources)
    federate(db, [str(sources[1])])
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE federation_edges SET relation='FAKE_FORMAL_PROOF' "
                     "WHERE edge_id=(SELECT edge_id FROM federation_edges LIMIT 1)")
    with pytest.raises(ValueError, match="does not match"):
        federation_summary(db)
    with pytest.raises(ValueError):
        federate(db, [str(sources[2])])


def test_deleting_derived_nodes_does_not_silently_repair(tmp_path, sources):
    db = make_db(tmp_path, sources)
    federate(db, [str(sources[1])])
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM federation_edges")
        conn.execute("DELETE FROM federation_nodes")
    with pytest.raises(ValueError):
        federate(db, [str(sources[2])])


def test_tampered_persisted_source_is_rejected(tmp_path, sources):
    db = make_db(tmp_path, sources)
    federate(db, [str(sources[2])])
    with sqlite3.connect(db) as conn:
        record = conn.execute("SELECT source_id, report_json FROM federation_sources").fetchone()
        altered = json.loads(record[1])
        altered["findings"][0]["status"] = "FORMALLY_VERIFIED"
        conn.execute("UPDATE federation_sources SET report_json=? WHERE source_id=?",
                     (json.dumps(altered), record[0]))
    with pytest.raises(ValueError):
        federation_summary(db)


def test_partial_campaign_and_invalid_query_fail_closed(tmp_path, sources):
    db = make_db(tmp_path, sources)
    partial = json.loads(sources[1].read_text())
    partial["progress"]["complete"] = False
    file = tmp_path / "partial.json"
    file.write_text(json.dumps(partial))
    with pytest.raises(ValueError, match="partial"):
        federate(db, [str(file)])
    assert knowledge_summary(db)["audit"] == "ACCEPTED"
    with pytest.raises(ValueError, match="unknown"):
        query_federation(db, domain="fictional")
    with pytest.raises(ValueError):
        query_federation(db, status="FORMALLY_VERIFIED")


def test_immutable_snapshot_collision(tmp_path, sources):
    db = make_db(tmp_path, sources)
    federate(db, [str(sources[2])])
    altered = copy.deepcopy(json.loads(sources[2].read_text()))
    altered["measurement"]["execution_seconds"] += 0.5
    changed = tmp_path / "same_campaign_new_measurement.json"
    changed.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="conflicting immutable"):
        federate(db, [str(changed)])
    assert federation_summary(db)["audit"] == "ACCEPTED"


def test_cli_cross_domain_roundtrip(tmp_path, sources):
    db = make_db(tmp_path, sources)
    base = [sys.executable, "-m", "axiom"]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))
    def call(*args):
        return subprocess.run(base + list(args), capture_output=True, text=True, env=env)
    built = call("knowledge-federate", "--db", db, str(sources[1]), str(sources[2]),
                 str(sources[3]))
    assert built.returncode == 0, built.stderr
    assert json.loads(built.stdout)["counts"]["source"] == 4
    audited = call("knowledge-federation-audit", "--db", db)
    assert audited.returncode == 0, audited.stderr
    queried = call("knowledge-cross-query", "--db", db,
                   "--domain", "recurrence", "--limit", "20")
    assert queried.returncode == 0, queried.stderr
    assert len(json.loads(queried.stdout)["statements"]) == 7
    denied = call("knowledge-cross-query", "--db", db, "--status", "FORMALLY_VERIFIED")
    assert denied.returncode != 0
