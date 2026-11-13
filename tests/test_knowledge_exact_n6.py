"""AXIOM v0.13: fail-closed exact-n6 knowledge provenance and reconciliation."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.graph_n6_exact import research_n6, SUPPORTED_TEMPLATES, save_n6
from axiom.knowledge_graph import build_knowledge_graph, knowledge_summary
from axiom.knowledge_federation import federate, federation_summary
from axiom.frontier_lineage import import_frontier_lineage, frontier_lineage_summary
from axiom.graph_frontier import load_graph_sources, research_frontier
from axiom.knowledge_exact_n6 import (
    import_exact_n6, exact_n6_summary, query_exact_n6)

ROOT = Path(__file__).resolve().parents[1]
GRAPH_SOURCES = (
    ROOT / "research/graphs/v05_baseline_report.json",
    ROOT / "research/graphs/v05_scale_report.json",
)
OTHER_SOURCES = (
    ROOT / "research/v03_campaign_report.json",
    ROOT / "research/number_theory/v04_report.json",
    ROOT / "research/number_theory/v04_sequences.json",
)


@pytest.fixture(scope="module")
def lineage_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("v013-source")
    db = str(folder / "knowledge.sqlite3")
    build_knowledge_graph(db, list(map(str, GRAPH_SOURCES)))
    federate(db, list(map(str, OTHER_SOURCES)))
    original = load_graph_sources(list(map(str, GRAPH_SOURCES)))
    paths = []
    for order in (6, 7):
        path = folder / f"frontier-n{order}.json"
        report = research_frontier(original, target_order=order, seed=42,
                                   search_budget=64, max_candidates=10)
        path.write_text(json.dumps(report))
        paths.append(str(path))
    import_frontier_lineage(db, paths)
    return db


@pytest.fixture(scope="module")
def complete_exact_report(tmp_path_factory):
    folder = tmp_path_factory.mktemp("v013-exact")
    file = folder / "n6-exact.json"
    save_n6(research_n6(list(SUPPORTED_TEMPLATES)), str(file))
    return file


@pytest.fixture
def source_clone(tmp_path, lineage_db):
    file = str(tmp_path / "working.sqlite3")
    with sqlite3.connect(lineage_db) as src:
        with sqlite3.connect(file) as target:
            src.backup(target)
    return file


def test_exact_certificates_preserve_original_knowledge(source_clone, complete_exact_report):
    before = (knowledge_summary(source_clone),
              federation_summary(source_clone),
              frontier_lineage_summary(source_clone))
    result = import_exact_n6(source_clone, [str(complete_exact_report)])
    again = import_exact_n6(source_clone, [str(complete_exact_report)])
    assert result == again
    assert result["audit"] == "ACCEPTED"
    assert result["exact_graph_order"] == 6
    assert result["labelled_graphs_per_finding"] == 32768
    assert result["exact_finding_records"] == 9
    assert result["distinct_exact_order_statements"] == 9
    assert result["status_counts"] == {
        "PROVED_IN_SUPPORTED_FRAGMENT": 7, "REFUTED": 2}
    assert result["historical_evidence_overwritten"] == 0
    assert result["generalization_to_all_graph_orders"] == "NOT_PROVED"
    assert result["formal_lean_verification"] == "NOT_PERFORMED"
    assert (knowledge_summary(source_clone), federation_summary(source_clone),
            frontier_lineage_summary(source_clone)) == before
    with sqlite3.connect(source_clone) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_exact_query_and_pagination_retains_mathematical_scope(source_clone, complete_exact_report):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    positive = query_exact_n6(source_clone, status="PROVED_IN_SUPPORTED_FRAGMENT")
    negative = query_exact_n6(source_clone, status="REFUTED")
    assert len(positive) == 7 and len(negative) == 2
    assert all(r["proven_exact_order_only"] for r in positive)
    assert all(not r["proven_exact_order_only"] for r in negative)
    assert all(r["certificate"] is not None and r["counterexample"] is None
               for r in positive)
    assert all(r["certificate"] is None and r["counterexample"] is not None
               for r in negative)
    assert all(r["statement"]["n"] == 6 and
               r["lean_formal_verification"] == "NOT_PERFORMED" and
               r["all_order_generalization"] == "NOT_PROVED"
               for r in positive + negative)
    whole = query_exact_n6(source_clone, limit=100)
    assert query_exact_n6(source_clone, limit=2, offset=1) == whole[1:3]


def test_frontier_correlations_are_only_status_preserving(source_clone, complete_exact_report):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    report = exact_n6_summary(source_clone)
    assert report["frontier_evidence_correlations"] >= 0
    assert sum(report["correlation_types"].values()) == report[
        "frontier_evidence_correlations"]
    for entry in query_exact_n6(source_clone, limit=100):
        for link in entry["bounded_frontier_correlations"]:
            assert link["bounded_observation_edited"] is False
            assert link["cross_order_implication"] is False
            assert link["formal_lean_verification"] == "NOT_PERFORMED"
            assert link["exact_order_status"] == entry["status"]


def test_tampered_materialized_finding_rejected(source_clone, complete_exact_report):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    with sqlite3.connect(source_clone) as db:
        db.execute("UPDATE exact_n6_findings SET source_finding_json='{}' "
                   "WHERE finding_id=(SELECT finding_id FROM exact_n6_findings LIMIT 1)")
    with pytest.raises(ValueError, match="materialization disagrees"):
        exact_n6_summary(source_clone)
    with pytest.raises(ValueError):
        import_exact_n6(source_clone, [str(complete_exact_report)])


def test_delete_reconciliation_link_is_detected(source_clone, complete_exact_report):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    with sqlite3.connect(source_clone) as db:
        link = db.execute("SELECT link_id FROM exact_n6_frontier_links LIMIT 1").fetchone()
        if link:
            db.execute("DELETE FROM exact_n6_frontier_links WHERE link_id=?", link)
        else:
            db.execute("DELETE FROM exact_n6_findings WHERE finding_id="
                       "(SELECT finding_id FROM exact_n6_findings LIMIT 1)")
    with pytest.raises(ValueError, match="materialization disagrees"):
        exact_n6_summary(source_clone)


def test_forged_source_and_conflicting_immutable_campaign_rejected(source_clone, complete_exact_report, tmp_path):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    forged = json.loads(complete_exact_report.read_text())
    forged["findings"][0]["all_order_generalization"] = "PROVED"
    bad = tmp_path / "forged.json"
    bad.write_text(json.dumps(forged))
    with pytest.raises(ValueError, match="conflicting immutable"):
        import_exact_n6(source_clone, [str(bad)])
    forged["campaign_id"] = "forged-distinct-campaign"
    bad.write_text(json.dumps(forged))
    with pytest.raises(ValueError):
        import_exact_n6(source_clone, [str(bad)])
    assert exact_n6_summary(source_clone)["audit"] == "ACCEPTED"


def test_corrupted_original_frontier_source_fails_closed(source_clone, complete_exact_report):
    import_exact_n6(source_clone, [str(complete_exact_report)])
    with sqlite3.connect(source_clone) as db:
        db.execute("UPDATE frontier_reports SET report_sha256='0' WHERE "
                   "campaign_id=(SELECT campaign_id FROM frontier_reports LIMIT 1)")
    with pytest.raises(ValueError):
        exact_n6_summary(source_clone)


def test_inputs_and_cli_end_to_end(source_clone, complete_exact_report):
    for kwargs in ({"status": "FORMALLY_VERIFIED"}, {"limit": 0},
                   {"offset": True}, {"offset": -1}, {"limit": True}):
        with pytest.raises(ValueError):
            query_exact_n6(source_clone, **kwargs)
    with pytest.raises(ValueError):
        import_exact_n6(source_clone, [])
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    base = [sys.executable, "-m", "axiom"]

    def cli(*args):
        return subprocess.run(base + list(args), capture_output=True,
                              text=True, env=env)

    imported = cli("knowledge-exact-n6-import", "--db", source_clone,
                   str(complete_exact_report))
    assert imported.returncode == 0, imported.stderr
    assert json.loads(imported.stdout)["audit"] == "ACCEPTED"
    proof_query = cli("knowledge-exact-n6-query", "--db", source_clone,
                      "--status", "PROVED_IN_SUPPORTED_FRAGMENT", "--limit", "2")
    assert proof_query.returncode == 0, proof_query.stderr
    assert len(json.loads(proof_query.stdout)["statements"]) == 2
    audited = cli("knowledge-exact-n6-audit", "--db", source_clone)
    assert audited.returncode == 0, audited.stderr
    assert cli("knowledge-exact-n6-query", "--db", source_clone,
               "--status", "FORMALLY_VERIFIED").returncode != 0
