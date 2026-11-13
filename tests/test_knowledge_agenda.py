"""AXIOM v0.10: auditable research agenda with no evidence-state promotion."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from axiom.knowledge_graph import build_knowledge_graph
from axiom.knowledge_federation import federate
from axiom.formal_provenance import import_formal
from axiom.knowledge_agenda import research_agenda, write_agenda, audit_agenda

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
def source_db(tmp_path_factory):
    location = tmp_path_factory.mktemp("research-agenda")
    db = str(location / "source.sqlite3")
    build_knowledge_graph(db, list(map(str, GRAPHS)))
    federate(db, list(map(str, DOMAINS)))
    return db


@pytest.fixture
def db_path(source_db, tmp_path):
    copied = str(tmp_path / "agenda.sqlite3")
    with sqlite3.connect(source_db) as src:
        with sqlite3.connect(copied) as dst:
            src.backup(dst)
    return copied


def test_deterministic_priorities_and_refutation_exclusion(db_path):
    a = research_agenda(db_path, limit=100)
    b = research_agenda(db_path, limit=100)
    assert a == b
    assert a["source_audit"] == "ACCEPTED"
    assert a["proof_status_upgrades"] == 0
    assert a["novelty"] == "NOT_ASSESSED"
    assert a["refuted_statements_excluded"] > 0
    assert a["eligible_action_count"] > 0
    assert a["returned_count"] <= 100
    assert all("REFUTED" not in t["evidence_statuses"] for t in a["tasks"])
    assert all(t["claims_a_new_theorem"] is False and
               t["cross_scope_entailment"] is False for t in a["tasks"])
    assert all(t["mathematical_novelty"] == "NOT_ASSESSED" for t in a["tasks"])
    assert a["tasks"] == sorted(a["tasks"], key=lambda t: (
        t["priority"], t["domain"], t["statement_id"]))


def test_pagination_exposes_every_ranked_task_once(db_path):
    first = research_agenda(db_path, limit=10, offset=0)
    second = research_agenda(db_path, limit=10, offset=10)
    assert first["page_offset"] == 0
    assert first["next_offset"] == 10
    assert second["page_offset"] == 10
    assert first["eligible_action_count"] == second["eligible_action_count"]
    assert {x["task_id"] for x in first["tasks"]}.isdisjoint(
        x["task_id"] for x in second["tasks"])
    final = research_agenda(db_path, limit=10,
                            offset=first["eligible_action_count"])
    assert final["tasks"] == []
    assert final["next_offset"] is None


def test_domain_scope_does_not_infer_cross_order_theorems(db_path):
    graph = research_agenda(db_path, domain="graph", limit=100)
    assert graph["statements_examined"] > 0
    assert graph["tasks"]
    assert all(t["domain"] == "graph" for t in graph["tasks"])
    assert all(t["action"] in {
        "FALSIFY_WITH_INDEPENDENT_SEARCH", "FORMALIZE_EXACT_SCOPE"}
        for t in graph["tasks"])
    assert all(t["source_bound_offline_lean_record_ids"] == []
               for t in graph["tasks"])
    assert all(t["statement"]["n"] <= 7 for t in graph["tasks"])


def test_saved_agenda_has_strict_independent_replay(db_path, tmp_path):
    output = tmp_path / "agenda.json"
    report = write_agenda(db_path, str(output), domain="number_theory", limit=10)
    assert report == research_agenda(db_path, domain="number_theory", limit=10)
    assert audit_agenda(db_path, str(output))["audit"] == "ACCEPTED"
    changed = json.loads(output.read_text())
    changed["proof_status_upgrades"] = 1
    output.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="differs"):
        audit_agenda(db_path, str(output))
    changed = report.copy()
    changed["source_fingerprint"] = "0" * 64
    output.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="differs"):
        audit_agenda(db_path, str(output))


def test_offline_lean_index_is_not_execution_attestation(db_path, tmp_path):
    algebra = tmp_path / "algebra.ndjson"
    nt = tmp_path / "number.ndjson"
    algebra.write_text("\n".join(
        (ROOT / "research/v03_formal_results.ndjson").read_text().splitlines()[:2]) + "\n")
    nt.write_text("\n".join(
        (ROOT / "research/number_theory/v04_formal_results.ndjson").read_text().splitlines()[:2]) + "\n")
    before = research_agenda(db_path, limit=15)
    import_formal(db_path, algebra_ndjson=str(algebra), number_index=str(nt),
                  number_records_dir=str(ROOT / "research/lean_verified/number_theory"))
    after = research_agenda(db_path, limit=100)
    assert after["source_fingerprint"] != before["source_fingerprint"]
    assert after["proof_status_upgrades"] == 0
    # Formal rechecks may follow more than 100 falsification/formalization
    # tasks. Pagination must make the complete agenda reachable.
    replay_start = (after["action_counts"].get("FALSIFY_WITH_INDEPENDENT_SEARCH", 0)
                    + after["action_counts"].get("FORMALIZE_SUPPORTED_FRAGMENT", 0))
    replay_page = research_agenda(db_path, offset=replay_start, limit=100)
    replays = [t for t in replay_page["tasks"]
               if t["action"] == "REEXECUTE_PINNED_LEAN"]
    assert replays
    assert all(t["source_bound_offline_lean_record_ids"] for t in replays)
    assert all("PROVED_IN_SUPPORTED_FRAGMENT" in t["evidence_statuses"]
               for t in replays)
    assert after["historical_lean_execution_attestation"] == (
        "NOT_ESTABLISHED_BY_OFFLINE_AUDIT")


def test_reject_database_tampering_before_task_scheduling(db_path):
    research_agenda(db_path, limit=5)
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE federation_nodes SET payload='{}' WHERE "
                   "node_id=(SELECT node_id FROM federation_nodes LIMIT 1)")
    with pytest.raises(ValueError):
        research_agenda(db_path, limit=5)


def test_invalid_limits_domains_and_manifest_fail_closed(db_path, tmp_path):
    for kw in [{"limit": 0}, {"limit": True}, {"limit": 101},
               {"offset": -1}, {"offset": True}, {"offset": 100001},
               {"domain": "fiction"}, {"domain": 17}]:
        with pytest.raises((ValueError, TypeError)):
            research_agenda(db_path, **kw)
    outfile = tmp_path / "invalid.json"
    outfile.write_text(json.dumps({"schema": "wrong", "configuration": {}}))
    with pytest.raises(ValueError):
        audit_agenda(db_path, str(outfile))


def test_cli_produces_and_audits_research_tasks(db_path, tmp_path):
    output = tmp_path / "tasks.json"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    cmd = [sys.executable, "-m", "axiom"]

    def execute(*args):
        return subprocess.run(cmd + list(args), text=True,
                              capture_output=True, env=env)

    produced = execute("knowledge-plan", "--db", db_path, "--domain", "graph",
                       "--limit", "5", "--output", str(output))
    assert produced.returncode == 0, produced.stderr
    assert json.loads(produced.stdout)["returned_count"] == 5
    audited = execute("knowledge-plan-audit", "--db", db_path, str(output))
    assert audited.returncode == 0, audited.stderr
    assert json.loads(audited.stdout)["audit"] == "ACCEPTED"
    invalid = execute("knowledge-plan", "--db", db_path, "--limit", "-1")
    assert invalid.returncode != 0
    bad = json.loads(output.read_text())
    bad["tasks"][0]["claims_a_new_theorem"] = True
    output.write_text(json.dumps(bad))
    assert execute("knowledge-plan-audit", "--db", db_path, str(output)).returncode != 0
