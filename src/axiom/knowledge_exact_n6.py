"""AXIOM v0.13: source-bound exact-n6 proof records and frontier reconciliation.

This overlay is separate from historical v0.6–v0.11 databases. Every read
rechecks original mathematical reports, source-bound historical Lean records,
bounded n=6/7 frontier experiments, and independently recomputes the entire
exact n=6 certificate campaign. Python exact-order proofs are NEVER promoted
to universal theorems or Lean FORMALLY_VERIFIED.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

from .graph_claims import digest, stable
from .graph_n6_exact import (
    SCHEMA as N6_SCHEMA, N as EXACT_ORDER, LABELED_GRAPHS,
    audit_n6, PROOF_SCOPE)
from .knowledge_graph import _open
from .knowledge_federation import _node_id
from .frontier_lineage import _audit as audit_frontier

SCHEMA = "axiom.knowledge_exact_n6.v1"
MAX_INPUT_BYTES = 8_000_000
MAX_BATCH = 16
EXACT_STATES = {"REFUTED", "PROVED_IN_SUPPORTED_FRAGMENT"}


def _tables(db: sqlite3.Connection) -> None:
    for statement in (
        """CREATE TABLE IF NOT EXISTS exact_n6_reports (
            campaign_id TEXT PRIMARY KEY, report_sha256 TEXT NOT NULL,
            report_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS exact_n6_statements (
            statement_id TEXT PRIMARY KEY, payload TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS exact_n6_findings (
            finding_id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES exact_n6_reports(campaign_id),
            statement_id TEXT NOT NULL REFERENCES exact_n6_statements(statement_id),
            status TEXT NOT NULL CHECK(status IN
              ('REFUTED','PROVED_IN_SUPPORTED_FRAGMENT')),
            source_finding_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS exact_n6_frontier_links (
            link_id TEXT PRIMARY KEY,
            exact_finding_id TEXT NOT NULL REFERENCES exact_n6_findings(finding_id),
            frontier_finding_id TEXT NOT NULL REFERENCES frontier_findings(finding_id),
            reconciliation_json TEXT NOT NULL)""",
        """CREATE INDEX IF NOT EXISTS exact_n6_findings_statement
            ON exact_n6_findings(statement_id)""",
    ):
        db.execute(statement)


def _build(reports: list[dict],
           frontier: tuple[dict, dict, dict]) -> tuple[dict, dict, dict]:
    frontier_statements, frontier_findings, _ = frontier
    if len(reports) > MAX_BATCH:
        raise ValueError("too many exact n6 campaigns")
    unique_reports: dict[str, dict] = {}
    for report in reports:
        if type(report) is not dict or report.get("schema") != N6_SCHEMA:
            raise ValueError("unknown exact six-vertex research report")
        cid = report.get("campaign_id")
        if type(cid) is not str or not cid:
            raise ValueError("missing exact n6 campaign identifier")
        if cid in unique_reports and stable(unique_reports[cid]) != stable(report):
            raise ValueError("conflicting exact n6 immutable campaign")
        unique_reports[cid] = report
    statements: dict[str, str] = {}
    findings: dict[str, tuple[str, str, str, str]] = {}
    links: dict[str, tuple[str, str, str]] = {}
    exact_by_statement: dict[str, tuple[str, str]] = {}
    frontier_by_statement: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fid, (_, sid, status, _) in frontier_findings.items():
        if sid not in frontier_statements:
            raise ValueError("orphan bounded frontier statement")
        frontier_by_statement[sid].append((fid, status))

    for cid, report in sorted(unique_reports.items()):
        audit_n6(report)  # Full independent 2^15 replay for every saved finding.
        if report.get("complete") is not True:
            raise ValueError("partial exact n6 campaign cannot enter knowledge")
        for finding in report["findings"]:
            subject = finding["statement"]
            if (subject["n"] != EXACT_ORDER or
                    finding["labelled_graphs_checked"] != LABELED_GRAPHS or
                    finding["proof_scope"] != PROOF_SCOPE or
                    finding["status"] not in EXACT_STATES or
                    finding["lean_formal_verification"] != "NOT_PERFORMED" or
                    finding["all_order_generalization"] != "NOT_PROVED"):
                raise ValueError("invalid scope/status for exact-n6 source")
            state = finding["status"]
            proof = finding["certificate"]
            counterexample = finding["counterexample"]
            if state == "PROVED_IN_SUPPORTED_FRAGMENT":
                if (type(proof) is not dict or proof["vacuous"] is not False or
                        counterexample is not None):
                    raise ValueError("exact n6 proof missing nonvacuous certificate")
            elif proof is not None or counterexample is None:
                raise ValueError("refutation must have original witness and no proof")
            sid = _node_id("statement", ["graph", subject])
            payload = stable({
                "domain": "graph", "statement": subject,
                "scope": PROOF_SCOPE, "labelled_graphs": LABELED_GRAPHS,
                "checker": "axiom.graph_n6_exact.check_n6_certificate",
                "formal_lean_verification": "NOT_PERFORMED",
                "all_order_generalization": "NOT_PROVED",
                "originality": "NOT_ASSESSED",
            })
            if sid in statements and statements[sid] != payload:
                raise ValueError("typed exact statement collision")
            statements[sid] = payload
            fingerprint = stable([state, proof, counterexample])
            if sid in exact_by_statement and exact_by_statement[sid] != (
                    state, fingerprint):
                raise ValueError("conflicting exhaustive evidence for same exact statement")
            exact_by_statement[sid] = (state, fingerprint)
            fid = _node_id("exact_n6_finding", [cid, digest(subject)])
            row = (cid, sid, state, stable(finding))
            if fid in findings and findings[fid] != row:
                raise ValueError("conflicting exact n6 finding")
            findings[fid] = row

            for frontier_fid, older_status in sorted(frontier_by_statement[sid]):
                if (state == "PROVED_IN_SUPPORTED_FRAGMENT" and
                        older_status == "REFUTED"):
                    raise ValueError(
                        "exact proof contradicts independently replayed counterexample")
                relationship = (
                    "EXACT_REFUTATION_SUPERSEDES_BOUNDED_SURVIVAL"
                    if state == "REFUTED" and
                    older_status == "EXPERIMENTALLY_SUPPORTED"
                    else "EXACT_RESULT_CONFIRMS_BOUNDED_OBSERVATION"
                    if state == "PROVED_IN_SUPPORTED_FRAGMENT" else
                    "EXACT_REFUTATION_AGREES_WITH_BOUNDED_REFUTATION")
                lid = _node_id(
                    "exact_n6_frontier_link", [fid, frontier_fid])
                links[lid] = (fid, frontier_fid, stable({
                    "relation": relationship,
                    "bounded_status_preserved": older_status,
                    "exact_order_status": state,
                    "bounded_observation_edited": False,
                    "cross_order_implication": False,
                    "formal_lean_verification": "NOT_PERFORMED",
                }))
    return statements, findings, links


def _audit(db: sqlite3.Connection) -> tuple[dict, dict, dict]:
    frontier = audit_frontier(db)  # Full original source/federation/formal/frontier replay.
    _tables(db)
    reports = []
    for cid, saved_digest, source in db.execute(
            "SELECT campaign_id,report_sha256,report_json FROM exact_n6_reports"):
        report = json.loads(source)
        if (type(report) is not dict or stable(report) != source or
                digest(report) != saved_digest or report.get("campaign_id") != cid):
            raise ValueError("exact n6 persisted source tampered")
        reports.append(report)
    expected = _build(reports, frontier)
    statements = dict(db.execute(
        "SELECT statement_id,payload FROM exact_n6_statements"))
    findings = {
        fid: (cid, sid, status, payload)
        for fid, cid, sid, status, payload in db.execute(
            "SELECT finding_id,campaign_id,statement_id,status,source_finding_json "
            "FROM exact_n6_findings")
    }
    links = {
        lid: (fid, frontier_fid, data)
        for lid, fid, frontier_fid, data in db.execute(
            "SELECT link_id,exact_finding_id,frontier_finding_id,"
            "reconciliation_json FROM exact_n6_frontier_links")
    }
    if (statements, findings, links) != expected:
        raise ValueError(
            "exact n6 knowledge materialization disagrees with independent source replay")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("orphan exact n6 or frontier source reference")
    return expected


def _summary(data: tuple[dict, dict, dict]) -> dict:
    statements, findings, links = data
    counts = Counter(status for _, _, status, _ in findings.values())
    recon = Counter(json.loads(raw)["relation"]
                    for _, _, raw in links.values())
    return {
        "schema": SCHEMA, "audit": "ACCEPTED",
        "exact_graph_order": EXACT_ORDER,
        "labelled_graphs_per_finding": LABELED_GRAPHS,
        "distinct_exact_order_statements": len(statements),
        "exact_finding_records": len(findings),
        "status_counts": dict(sorted(counts.items())),
        "frontier_evidence_correlations": len(links),
        "correlation_types": dict(sorted(recon.items())),
        "historical_evidence_overwritten": 0,
        "generalization_to_all_graph_orders": "NOT_PROVED",
        "formal_lean_verification": "NOT_PERFORMED",
        "originality": "NOT_ASSESSED",
    }


def exact_n6_summary(db_path: str) -> dict:
    with _open(db_path, existing=True) as db:
        data = _audit(db)
    return _summary(data)


def import_exact_n6(db_path: str, report_paths: list[str]) -> dict:
    if not 1 <= len(report_paths) <= MAX_BATCH:
        raise ValueError("exact n6 import requires 1..16 full research reports")
    incoming = []
    for filename in report_paths:
        path = Path(filename)
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("exact n6 source exceeds maximum size")
        report = json.loads(path.read_text(encoding="utf-8"))
        if type(report) is not dict:
            raise ValueError("invalid exact n6 JSON report")
        incoming.append(report)
    with _open(db_path, existing=True) as db:
        _tables(db)
        _audit(db)  # Reject damaged source, frontier, or exact materialization.
        snapshots = {
            cid: json.loads(payload)
            for cid, payload in db.execute(
                "SELECT campaign_id,report_json FROM exact_n6_reports")
        }
        for report in incoming:
            cid = report.get("campaign_id")
            if type(cid) is not str or not cid:
                raise ValueError("missing exact n6 campaign ID")
            if cid in snapshots and stable(snapshots[cid]) != stable(report):
                raise ValueError("conflicting immutable exact n6 campaign")
            snapshots[cid] = report
        frontier = audit_frontier(db)
        statements, findings, links = _build(list(snapshots.values()), frontier)
        with db:
            for report in sorted(snapshots.values(), key=lambda x: x["campaign_id"]):
                db.execute(
                    "INSERT OR IGNORE INTO exact_n6_reports VALUES (?,?,?)",
                    (report["campaign_id"], digest(report), stable(report)))
            db.execute("DELETE FROM exact_n6_frontier_links")
            db.execute("DELETE FROM exact_n6_findings")
            db.execute("DELETE FROM exact_n6_statements")
            db.executemany(
                "INSERT INTO exact_n6_statements VALUES (?,?)",
                sorted(statements.items()))
            db.executemany(
                "INSERT INTO exact_n6_findings VALUES (?,?,?,?,?)",
                [(fid, *row) for fid, row in sorted(findings.items())])
            db.executemany(
                "INSERT INTO exact_n6_frontier_links VALUES (?,?,?,?)",
                [(lid, *row) for lid, row in sorted(links.items())])
    return exact_n6_summary(db_path)


def query_exact_n6(db_path: str, *, status: str | None = None,
                   offset: int = 0, limit: int = 20) -> list[dict]:
    if status is not None and status not in EXACT_STATES:
        raise ValueError("invalid exact n6 status filter")
    if type(offset) is not int or not 0 <= offset <= 100_000:
        raise ValueError("invalid exact n6 query offset")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("exact n6 query limit must be 1..100")
    with _open(db_path, existing=True) as db:
        statements, findings, links = _audit(db)
    by_statement = defaultdict(list)
    by_finding = defaultdict(list)
    for _, (exact_fid, _, raw) in links.items():
        by_finding[exact_fid].append(json.loads(raw))
    for fid, (cid, sid, state, raw) in findings.items():
        by_statement[sid].append((fid, cid, state, json.loads(raw)))
    results = []
    for sid in sorted(statements):
        records = sorted(by_statement[sid])
        states = {r[2] for r in records}
        if len(states) != 1:
            raise ValueError("conflicting exact status on identical statement")
        state = next(iter(states))
        if status is not None and state != status:
            continue
        source = records[0][3]
        results.append({
            "statement_id": sid,
            "statement": source["statement"],
            "exact_order": EXACT_ORDER,
            "status": state,
            "proven_exact_order_only": state == "PROVED_IN_SUPPORTED_FRAGMENT",
            "source_campaigns": sorted({r[1] for r in records}),
            "certificate": source["certificate"],
            "counterexample": source["counterexample"],
            "bounded_frontier_correlations": [
                x for r in records for x in sorted(
                    by_finding[r[0]], key=stable)],
            "source_finding_records": len(records),
            "labelled_graphs_checked_per_finding": LABELED_GRAPHS,
            "all_order_generalization": "NOT_PROVED",
            "lean_formal_verification": "NOT_PERFORMED",
            "originality": "NOT_ASSESSED",
        })
    return results[offset:offset + limit]
