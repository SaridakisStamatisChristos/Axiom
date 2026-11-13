"""AXIOM v0.11: immutable source-bound bounded graph experiment lineage."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.graph_claims import stable
from axiom.graph_frontier import load_graph_sources, research_frontier
from axiom.knowledge_graph import build_knowledge_graph, knowledge_summary
from axiom.knowledge_federation import federate, federation_summary
from axiom.formal_provenance import formal_summary
from axiom.frontier_lineage import (
    import_frontier_lineage, frontier_lineage_summary, query_frontier_lineage)

ROOT = Path(__file__).resolve().parents[1]
GRAPH_REPORTS = (
    ROOT / "research/graphs/v05_baseline_report.json",
    ROOT / "research/graphs/v05_scale_report.json",
)
DOMAINS = (
    ROOT / "research/v03_campaign_report.json",
    ROOT / "research/number_theory/v04_report.json",
    ROOT / "research/number_theory/v04_sequences.json",
)


@pytest.fixture(scope="module")
def source_db(tmp_path_factory):
    location = tmp_path_factory.mktemp("frontier-source")
    database = str(location / "source.sqlite3")
    build_knowledge_graph(database, list(map(str, GRAPH_REPORTS)))
    federate(database, list(map(str, DOMAINS)))
    return database


@pytest.fixture(scope="module")
def frontier_reports(tmp_path_factory):
    location = tmp_path_factory.mktemp("frontier-evidence")
    originals = load_graph_sources(list(map(str, GRAPH_REPORTS)))
    paths = []
    for order in (6, 7):
        output = location / f"n{order}.json"
        report = research_frontier(
            originals, target_order=order, seed=42,
            search_budget=64, max_candidates=10)
        output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        paths.append(output)
    return paths


@pytest.fixture
def clone_db(tmp_path, source_db):
    destination = str(tmp_path / "frontier.sqlite3")
    with sqlite3.connect(source_db) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)
    return destination


def test_full_source_replay_and_idempotent_persistence(clone_db, frontier_reports):
    before = knowledge_summary(clone_db)
    federated = federation_summary(clone_db)
    first = import_frontier_lineage(clone_db, list(map(str, frontier_reports)))
    second = import_frontier_lineage(clone_db, list(map(str, frontier_reports)))
    assert first == second
    assert first["audit"] == "ACCEPTED"
    assert first["finding_records"] > 0
    assert first["source_proof_motivation_links"] >= first["finding_records"]
    assert first["proofs_at_target_order"] == 0
    assert first["knowledge_federation_status_upgrades"] == 0
    assert first["novelty"] == "NOT_ASSESSED"
    assert first["statement_orders"].keys() == {"6", "7"} or (
        set(first["statement_orders"]) == {6, 7})
    assert knowledge_summary(clone_db) == before
    assert federation_summary(clone_db) == federated
    assert formal_summary(clone_db)["knowledge_graph_status_upgrades"] == 0
    with sqlite3.connect(clone_db) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_query_retains_explicit_sample_only_status(clone_db, frontier_reports):
    import_frontier_lineage(clone_db, list(map(str, frontier_reports)))
    all_six = query_frontier_lineage(clone_db, order=6, limit=100)
    all_seven = query_frontier_lineage(clone_db, order=7, limit=100)
    assert all_six and all_seven
    assert all(r["statement"]["n"] == 6 for r in all_six)
    assert all(r["statement"]["n"] == 7 for r in all_seven)
    assert all(r["proofs_at_exact_order"] == 0 and
               r["cross_order_entailment"] is False for r in all_six + all_seven)
    assert all(set(r["statuses"]) <= {
        "REFUTED", "EXPERIMENTALLY_SUPPORTED"} for r in all_six + all_seven)
    assert query_frontier_lineage(clone_db, order=6, limit=1, offset=1) == all_six[1:2]


def test_corrupted_materialized_finding_fails_closed(clone_db, frontier_reports):
    import_frontier_lineage(clone_db, [str(frontier_reports[0])])
    with sqlite3.connect(clone_db) as db:
        db.execute("UPDATE frontier_findings SET evidence_json='{}' WHERE "
                   "finding_id=(SELECT finding_id FROM frontier_findings LIMIT 1)")
    with pytest.raises(ValueError, match="disagrees"):
        frontier_lineage_summary(clone_db)
    with pytest.raises(ValueError):
        import_frontier_lineage(clone_db, [str(frontier_reports[1])])


def test_tampered_motivation_and_missing_links_rejected(clone_db, frontier_reports):
    import_frontier_lineage(clone_db, [str(frontier_reports[0])])
    with sqlite3.connect(clone_db) as db:
        db.execute("DELETE FROM frontier_motivations WHERE "
                   "link_id=(SELECT link_id FROM frontier_motivations LIMIT 1)")
    with pytest.raises(ValueError, match="disagrees"):
        frontier_lineage_summary(clone_db)


def test_conflicting_immutable_campaign_rejected(clone_db, frontier_reports, tmp_path):
    import_frontier_lineage(clone_db, [str(frontier_reports[0])])
    old = json.loads(frontier_reports[0].read_text())
    forged = copy.deepcopy(old)
    forged["findings"][0]["status"] = "PROVED_IN_SUPPORTED_FRAGMENT"
    out = tmp_path / "forged.json"
    out.write_text(json.dumps(forged))
    with pytest.raises(ValueError, match="conflicting immutable"):
        import_frontier_lineage(clone_db, [str(out)])
    assert frontier_lineage_summary(clone_db)["audit"] == "ACCEPTED"


def test_external_report_and_original_source_corruption_rejected(clone_db, frontier_reports, tmp_path):
    experiment = json.loads(frontier_reports[0].read_text())
    experiment["source_reports"][0]["report_sha256"] = "0" * 64
    invalid = tmp_path / "wrong_origins.json"
    invalid.write_text(json.dumps(experiment))
    with pytest.raises(ValueError):
        import_frontier_lineage(clone_db, [str(invalid)])
    with sqlite3.connect(clone_db) as db:
        db.execute("UPDATE kg_reports SET report_digest='0' WHERE "
                   "campaign_id=(SELECT campaign_id FROM kg_reports LIMIT 1)")
    with pytest.raises(ValueError):
        frontier_lineage_summary(clone_db)


def test_reject_unsupported_inputs_and_invalid_queries(clone_db, frontier_reports, tmp_path):
    with pytest.raises(ValueError):
        import_frontier_lineage(clone_db, [])
    for kwargs in (
        {"order": 5}, {"order": True}, {"status": "FORMALLY_VERIFIED"},
        {"limit": 0}, {"limit": True}, {"offset": -1}, {"offset": True}):
        with pytest.raises(ValueError):
            query_frontier_lineage(clone_db, **kwargs)
    bad = tmp_path / "partial.json"
    data = json.loads(frontier_reports[0].read_text())
    data["complete"] = False
    bad.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        import_frontier_lineage(clone_db, [str(bad)])


def test_cli_import_query_audit_and_rejection(clone_db, frontier_reports):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    base = [sys.executable, "-m", "axiom"]
    def cli(*items):
        return subprocess.run(base + list(items), capture_output=True, text=True, env=env)
    imported = cli("knowledge-frontier-import", "--db", clone_db,
                   *(str(p) for p in frontier_reports))
    assert imported.returncode == 0, imported.stderr
    assert json.loads(imported.stdout)["audit"] == "ACCEPTED"
    query = cli("knowledge-frontier-query", "--db", clone_db, "--order", "6",
                "--limit", "2")
    assert query.returncode == 0, query.stderr
    assert len(json.loads(query.stdout)["statements"]) == 2
    audit = cli("knowledge-frontier-audit", "--db", clone_db)
    assert audit.returncode == 0, audit.stderr
    assert cli("knowledge-frontier-query", "--db", clone_db,
               "--status", "FORMALLY_VERIFIED").returncode != 0
