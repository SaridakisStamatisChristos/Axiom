"""AXIOM v0.6 knowledge provenance and adversarial regression tests."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.graph_campaign import run_graph_campaign
from axiom.knowledge_graph import (build_knowledge_graph, knowledge_summary,
                                   knowledge_neighbors, query_knowledge)


@pytest.fixture
def campaign_files(tmp_path):
    reports = []
    for seed in (42, 73):
        path = tmp_path / f"campaign_{seed}.json"
        run_graph_campaign(str(tmp_path / f"campaign_{seed}.sqlite3"),
                           seed=seed, candidates=80, max_order=6,
                           search_budget=70, report_path=str(path))
        reports.append(path)
    return reports


def test_merged_evidence_and_idempotent_import(tmp_path, campaign_files):
    db = str(tmp_path / "knowledge.sqlite3")
    first = build_knowledge_graph(db, [str(x) for x in campaign_files])
    second = build_knowledge_graph(db, [str(x) for x in campaign_files])
    assert first == second
    assert first["audit"] == "ACCEPTED"
    assert first["counts"]["campaign"] == 2
    assert first["counts"]["finite_proof"] > 0
    assert first["counts"]["counterexample"] > 0
    assert first["counts"]["statement"] <= first["counts"]["finding"]
    assert first["graph_lean_formal_verification"] == "NOT_PERFORMED"
    shared = query_knowledge(db, template="handshake", order=5)
    assert len(shared) == 1
    assert shared[0]["statuses"] == ["PROVED_IN_SUPPORTED_FRAGMENT"]
    assert len(shared[0]["campaign_ids"]) == 2


def test_no_universal_proof_inference(tmp_path, campaign_files):
    db = str(tmp_path / "knowledge.sqlite3")
    build_knowledge_graph(db, [str(x) for x in campaign_files])
    with sqlite3.connect(db) as conn:
        proofs = conn.execute(
            "SELECT node_id,payload FROM kg_nodes WHERE kind='finite_proof'").fetchall()
        assert proofs
        for node_id, raw in proofs[:3]:
            evidence = json.loads(raw)
            assert evidence["certificate"]["order"] <= 5
            assert not evidence["formal_lean_verification"]
            neighbors = knowledge_neighbors(db, node_id)
            assert any(e["relation"] == "DEPENDS_ON_CHECKER" for e in
                       neighbors["relationships"])
        analogues = conn.execute(
            "SELECT attributes FROM kg_edges WHERE relation='NEXT_ORDER_ANALOGUE'").fetchall()
        assert analogues
        assert all(not json.loads(x[0])["logical_implication"] for x in analogues)
    assert query_knowledge(db, order=7) == []  # campaign max order 6


def test_tampered_edge_rejected(tmp_path, campaign_files):
    db = str(tmp_path / "knowledge.sqlite3")
    build_knowledge_graph(db, [str(campaign_files[0])])
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE kg_edges SET relation='CLAIMED_UNIVERSAL_PROOF' WHERE edge_id="
                     "(SELECT edge_id FROM kg_edges LIMIT 1)")
    with pytest.raises(ValueError, match="differs"):
        knowledge_summary(db)
    with pytest.raises(ValueError):
        build_knowledge_graph(db, [str(campaign_files[1])])


def test_tampered_source_report_rejected(tmp_path, campaign_files):
    db = str(tmp_path / "knowledge.sqlite3")
    build_knowledge_graph(db, [str(campaign_files[0])])
    with sqlite3.connect(db) as conn:
        doc = json.loads(conn.execute("SELECT report_json FROM kg_reports").fetchone()[0])
        doc["findings"][0]["status"] = "FORMALLY_VERIFIED"
        conn.execute("UPDATE kg_reports SET report_json=?", (json.dumps(doc),))
    with pytest.raises(ValueError):
        knowledge_summary(db)


def test_import_refuses_partial_and_conflicting_sources(tmp_path, campaign_files):
    first = json.loads(campaign_files[0].read_text())
    partial = copy.deepcopy(first)
    partial["progress"]["complete"] = False
    partial_path = tmp_path / "partial.json"
    partial_path.write_text(json.dumps(partial))
    db = str(tmp_path / "knowledge.sqlite3")
    with pytest.raises(ValueError, match="partial"):
        build_knowledge_graph(db, [str(partial_path)])
    assert not Path(db).exists()

    build_knowledge_graph(db, [str(campaign_files[0])])
    changed = copy.deepcopy(first)
    changed["measurement"]["elapsed_seconds"] += 1
    changed_path = tmp_path / "conflict.json"
    changed_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="snapshot"):
        build_knowledge_graph(db, [str(changed_path)])
    assert knowledge_summary(db)["counts"]["campaign"] == 1


def test_cli_build_audit_query_and_missing_node(tmp_path, campaign_files):
    base = [sys.executable, "-m", "axiom"]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))
    db = str(tmp_path / "via_cli.sqlite3")

    def invoke(*args):
        return subprocess.run(base + list(args), capture_output=True, text=True, env=env)

    built = invoke("knowledge-build", "--db", db, str(campaign_files[0]))
    assert built.returncode == 0, built.stderr
    assert json.loads(built.stdout)["counts"]["campaign"] == 1
    audited = invoke("knowledge-audit", "--db", db)
    assert audited.returncode == 0, audited.stderr
    searched = invoke("knowledge-query", "--db", db, "--template", "handshake",
                      "--order", "5")
    assert searched.returncode == 0, searched.stderr
    assert len(json.loads(searched.stdout)["statements"]) == 1
    wrong = invoke("knowledge-neighbors", "fake-node", "--db", db)
    assert wrong.returncode != 0 and "REJECTED" in wrong.stderr
