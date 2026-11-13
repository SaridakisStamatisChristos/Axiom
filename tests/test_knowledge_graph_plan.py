"""AXIOM v0.14: no repeated disproved graphs; exact-scope evidence gates."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.graph_claims import GraphStatement
from axiom.graph_frontier import load_graph_sources, research_frontier
from axiom.graph_n6_exact import research_n6, save_n6
from axiom.knowledge_graph import build_knowledge_graph
from axiom.knowledge_federation import federate
from axiom.frontier_lineage import import_frontier_lineage
from axiom.knowledge_exact_n6 import import_exact_n6
from axiom.knowledge_graph_plan import (
    SCHEMA, graph_research_plan, write_graph_plan, audit_graph_plan)

ROOT = Path(__file__).resolve().parents[1]
GRAPHS = (
    ROOT / "research/graphs/v05_baseline_report.json",
    ROOT / "research/graphs/v05_scale_report.json",
)
DOMAINS = (
    ROOT / "research/v03_campaign_report.json",
    ROOT / "research/number_theory/v04_report.json",
    ROOT / "research/number_theory/v04_sequences.json",
)


@pytest.fixture(scope="module")
def prepared_db(tmp_path_factory):
    root = tmp_path_factory.mktemp("graph-plan")
    db = str(root / "knowledge.sqlite3")
    build_knowledge_graph(db, list(map(str, GRAPHS)))
    federate(db, list(map(str, DOMAINS)))
    graph_reports = load_graph_sources(list(map(str, GRAPHS)))
    paths = []
    for order in (6, 7):
        report = research_frontier(
            graph_reports, target_order=order, seed=42,
            search_budget=64, max_candidates=10)
        filename = root / f"frontier-{order}.json"
        filename.write_text(json.dumps(report))
        paths.append(str(filename))
    import_frontier_lineage(db, paths)
    exact = root / "exact.json"
    save_n6(research_n6(["handshake", "edges_le_vertices"]), str(exact))
    import_exact_n6(db, [str(exact)])
    return db


@pytest.fixture(scope="module")
def plan(prepared_db):
    return graph_research_plan(prepared_db, limit=100)


@pytest.fixture(scope="module")
def all_ranked_tasks(prepared_db):
    # Inspect all tasks on one trusted full source replay rather than
    # repeatedly re-auditing the complete graph/Lean provenance on pages.
    from axiom.knowledge_graph import _open
    from axiom.knowledge_exact_n6 import _audit as audit_exact
    from axiom.knowledge_graph_plan import _materialized_plan
    with _open(prepared_db, existing=True) as db:
        source = audit_exact(db)
        all_tasks, _, _ = _materialized_plan(db, source)
    return all_tasks


def test_evidence_priority_and_source_fingerprint(plan):
    assert plan["schema"] == SCHEMA
    assert plan["source_audit"] == "ACCEPTED"
    assert plan["eligible_action_count"] > 0
    assert plan["all_orders_refuted_excluded"] > 0
    assert plan["proof_status_upgrades"] == 0
    assert plan["historical_evidence_overwritten"] == 0
    assert plan["cross_order_inference"] is False
    assert plan["novelty"] == "NOT_ASSESSED"
    assert len(plan["source_fingerprint"]) == 64
    assert plan["tasks"] == sorted(plan["tasks"], key=lambda t: (
        t["priority"], t["statement"]["n"], t["statement_id"]))
    assert all(t["claim_is_new_theorem"] is False for t in plan["tasks"])
    assert all(t["all_order_generalization"] == "NOT_PROVED"
               and t["lean_formal_verification"] == "NOT_PERFORMED_BY_PLAN"
               for t in all_ranked_tasks)


def test_known_finite_n6_proof_only_gets_formalization_task(all_ranked_tasks):
    exact = [t for t in all_ranked_tasks if t["statement"]["n"] == 6
             and t["statement"]["template"] == "handshake"]
    assert len(exact) == 1
    task = exact[0]
    assert task["action"] == "FORMALIZE_EXACT_N6_IN_LEAN"
    assert task["priority"] == 3
    assert task["evidence_by_layer"]["exact_n6"] == [
        "PROVED_IN_SUPPORTED_FRAGMENT"]
    assert task["maximum_labelled_graphs_checked_in_source"] == 32768
    assert task["exact_certificate_sha256"]
    # The same mathematical identity on n=5 is an independent proof task,
    # never inferred from n=6. This guards against cross-order promotions.
    five = [t for t in all_ranked_tasks if t["statement"]["n"] == 5
            and t["statement"]["template"] == "handshake"]
    assert five and all(t["action"] == "FORMALIZE_LOCAL_FINITE_PROOF_IN_LEAN"
                        for t in five)


def test_exact_refutation_never_reproposed_for_search(all_ranked_tasks):
    assert not any(
        t["statement"]["n"] == 6 and
        t["statement"]["template"] == "edges_le_vertices"
        for t in plan["tasks"])


def test_unresolved_frontier_still_requires_independent_search(all_ranked_tasks):
    pending = [t for t in all_ranked_tasks
               if t["action"] == "EXTEND_BOUNDED_FALSIFICATION"]
    assert pending
    assert all("frontier" in t["evidence_by_layer"] for t in pending)
    assert all("PROVED_IN_SUPPORTED_FRAGMENT" not in
               t["evidence_by_layer"].get("exact_n6", [])
               for t in pending)
    assert any(t["statement"]["n"] == 7 for t in pending)


def test_invalid_params_and_untrusted_report_path(prepared_db, plan, tmp_path):
    for kw in (
        {"order": 8}, {"order": True}, {"order": "6"},
        {"limit": 0}, {"limit": True}, {"limit": 101},
        {"offset": -1}, {"offset": True}, {"offset": 100001},
    ):
        with pytest.raises((ValueError, TypeError)):
            graph_research_plan(prepared_db, **kw)
    fake = tmp_path / "fake.json"
    fake.write_text(json.dumps({
        "schema": "forged-graph-agenda", "configuration": {}}))
    with pytest.raises(ValueError):
        audit_graph_plan(prepared_db, str(fake))


def test_cli_persists_independently_auditable_exact_scope_plan(prepared_db, tmp_path):
    output = tmp_path / "plan.json"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    def run(*args):
        return subprocess.run([sys.executable, "-m", "axiom", *args],
                              text=True, capture_output=True, env=env)
    result = run("knowledge-graph-plan", "--db", prepared_db, "--order", "6",
                 "--limit", "5", "--output", str(output))
    assert result.returncode == 0, result.stderr
    data = json.loads(output.read_text())
    assert data["configuration"] == {"order": 6, "limit": 5, "offset": 0}
    assert data["proof_status_upgrades"] == 0
    assert data["all_orders_refuted_excluded"] > 0
    accepted = run("knowledge-graph-plan-audit", "--db", prepared_db, str(output))
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(accepted.stdout)["audit"] == "ACCEPTED"


def test_tampered_exact_proof_source_blocks_research(prepared_db, tmp_path):
    db = str(tmp_path / "tampered.sqlite3")
    with sqlite3.connect(prepared_db) as original:
        with sqlite3.connect(db) as copied:
            original.backup(copied)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE exact_n6_reports SET report_sha256='0' "
                     "WHERE campaign_id=(SELECT campaign_id FROM "
                     "exact_n6_reports LIMIT 1)")
    with pytest.raises(ValueError):
        graph_research_plan(db, limit=5)


def test_saved_plan_adversarial_status_tampering_rejected(monkeypatch, plan, prepared_db, tmp_path):
    # This unit test checks exact JSON equality after trusted replay, while
    # the CLI and CI workflows separately execute the costly full replay.
    import axiom.knowledge_graph_plan as module
    forged = copy.deepcopy(plan)
    assert forged["tasks"]
    forged["tasks"][0]["all_order_generalization"] = "PROVED_FOR_ALL_N"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(forged))
    monkeypatch.setattr(module, "graph_research_plan",
                        lambda db_path, **kwargs: plan)
    with pytest.raises(ValueError, match="full mathematical replay"):
        module.audit_graph_plan(prepared_db, str(path))


def test_database_has_no_missing_source_references(prepared_db, plan):
    with sqlite3.connect(prepared_db) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert len(plan["source_fingerprint"]) == 64
