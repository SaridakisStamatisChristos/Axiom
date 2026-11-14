"""AXIOM v0.15 source-replayed graph research executor.

Plans are recommendations. This executor only dispatches supported Lean work;
unsupported and experimental tasks remain pending, not silently promoted.
Results are external JSON artifacts, never updates of source evidence tables.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from .graph_claims import digest
from .graph_lean import (
    SUPPORTED, audit_graph_lean_record, save_record, verify_graph_with_lean,
)
from .knowledge_graph import _open
from .knowledge_graph_plan import graph_research_plan

SCHEMA = "axiom.graph_research_executor.v1"


def execute_graph_research(db_path: str, output_dir: str, *,
                           project_root: str = ".", max_proofs: int = 3,
                           timeout_seconds: int = 180) -> dict:
    """Run at most N source-bound exact n6 Lean tasks from the audited agenda."""
    if type(max_proofs) is not int or not 1 <= max_proofs <= 7:
        raise ValueError("max_proofs must be an integer in 1..7")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise ValueError("timeout_seconds must be in 1..1200")
    # Entire source replay is performed by the exact-n6 graph planner on each
    # page, preserving all graph, federation, frontier and proof evidence.
    plan = graph_research_plan(db_path, order=6, limit=100)
    all_tasks = list(plan["tasks"])
    while plan["next_offset"] is not None:
        plan = graph_research_plan(
            db_path, order=6, limit=100, offset=plan["next_offset"])
        all_tasks.extend(plan["tasks"])
    candidates = [t for t in all_tasks
                  if t["action"] == "FORMALIZE_EXACT_N6_IN_LEAN"]
    # Reconcile stored materialized finding to its original full certificate
    # AFTER the independent mathematical source audit.
    source_by_statement = {}
    with _open(db_path, existing=True) as connection:
        records = connection.execute(
            "SELECT finding_id,source_finding_json FROM exact_n6_findings "
            "WHERE status='PROVED_IN_SUPPORTED_FRAGMENT' "
            "ORDER BY finding_id").fetchall()
    for fid, payload in records:
        finding = json.loads(payload)
        statement, cert = finding["statement"], finding["certificate"]
        if cert is None:
            raise ValueError("source-replayed exact proof has no certificate")
        sid = digest(statement)
        source_by_statement.setdefault(sid, []).append((fid, statement, cert))
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    executed, pending = [], []
    for task in candidates:
        template = task["statement"]["template"]
        if template not in SUPPORTED:
            pending.append({
                "task_id": task["task_id"], "template": template,
                "reason": "LEAN_FORMALIZATION_NOT_IMPLEMENTED",
                "original_proof_status_unchanged": True,
            })
            continue
        if len(executed) >= max_proofs:
            pending.append({
                "task_id": task["task_id"], "template": template,
                "reason": "EXECUTION_BUDGET_EXHAUSTED",
                "original_proof_status_unchanged": True,
            })
            continue
        matching = source_by_statement.get(digest(task["statement"]), [])
        if not matching:
            raise ValueError("scheduled exact proof has no exact source finding")
        accepted = [(fid, stmt, cert) for fid, stmt, cert in matching
                    if digest(cert) in task["exact_certificate_sha256"]
                    and stmt == task["statement"]]
        if not accepted:
            raise ValueError("task source certificate differs from audited finding")
        fid, stmt, cert = accepted[0]
        record = verify_graph_with_lean(
            stmt, cert, project_root=project_root, timeout_seconds=timeout_seconds)
        audit_graph_lean_record(record)
        filename = f"{digest([task['task_id'], fid])[:32]}.json"
        save_record(record, destination / filename)
        executed.append({
            "task_id": task["task_id"], "source_finding_id": fid,
            "statement_id": task["statement_id"], "template": template,
            "evidence_file": filename,
            "source_sha256": record["source_sha256"],
            "status": record["status"], "accepted": record["accepted"],
            "original_proof_status_unchanged": True,
        })
    report = {
        "schema": SCHEMA,
        "source_fingerprint": plan["source_fingerprint"],
        "exact_graph_order": 6,
        "all_order_generalization": "NOT_PROVED",
        "source_evidence_modified": False,
        "selected_action": "FORMALIZE_EXACT_N6_IN_LEAN",
        "candidate_count": len(candidates),
        "attempted": len(executed),
        "formally_verified": sum(item["accepted"] for item in executed),
        "pending": pending,
        "results": executed,
    }
    save_record(report, destination / "summary.json")
    return report


def audit_executor_report(db_path: str, output_dir: str) -> dict:
    """Recheck source identities and archived records; not an execution attestation."""
    folder = Path(output_dir)
    report = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unknown graph executor report")
    plan = graph_research_plan(db_path, order=6, limit=100)
    if (report["source_fingerprint"] != plan["source_fingerprint"] or
            report["exact_graph_order"] != 6 or
            report["source_evidence_modified"] is not False or
            report["all_order_generalization"] != "NOT_PROVED"):
        raise ValueError("graph research executor fingerprint or scope mismatch")
    seen = set()
    for item in report["results"]:
        if item["task_id"] in seen or item["original_proof_status_unchanged"] is not True:
            raise ValueError("duplicate or invalid execution task")
        seen.add(item["task_id"])
        evidence = json.loads((folder / item["evidence_file"]).read_text(encoding="utf-8"))
        audit_graph_lean_record(evidence)
        if (item["template"] != evidence["statement"]["template"] or
                item["source_sha256"] != evidence["source_sha256"] or
                item["accepted"] is not evidence["accepted"] or
                item["status"] != evidence["status"]):
            raise ValueError("archived execution record altered")
    if (report["attempted"] != len(report["results"]) or
            report["formally_verified"] != sum(t["accepted"] for t in report["results"])):
        raise ValueError("executor outcome counters altered")
    return {
        "audit": "SOURCE_RECORDS_REPLAYED",
        "execution_independently_attested": False,
        "attempted": report["attempted"],
        "formally_verified_recorded": report["formally_verified"],
    }
