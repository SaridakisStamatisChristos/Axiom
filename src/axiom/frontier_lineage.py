"""AXIOM v0.11: fail-closed integration of bounded graph-frontier evidence.

The v0.9 reports are executed experiments on graphs with exactly n=6 or 7.
They are NOT exhaustive finite proofs and never overwrite v0.6/v0.7 claims.
Every audit reruns the original frontier algorithm against complete, immutable
v0.5 graph campaigns and reconstructs the complete SQLite overlay.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3

from .graph_claims import digest, stable
from .graph_frontier import SCHEMA as FRONTIER_SCHEMA, audit_frontier
from .knowledge_graph import _open, _load as load_graph_sources
from .knowledge_federation import _node_id
from .formal_provenance import _audit as audit_formal

SCHEMA = "axiom.frontier_lineage.v1"
MAX_INPUT_BYTES = 8_000_000
MAX_BATCH = 32
EXPERIMENTAL = {"REFUTED", "EXPERIMENTALLY_SUPPORTED"}


def _tables(db: sqlite3.Connection) -> None:
    # Do not use executescript: sqlite3 executescript implicitly commits,
    # breaking the integrity of surrounding import transactions.
    ddls = (
        """CREATE TABLE IF NOT EXISTS frontier_reports (
            campaign_id TEXT PRIMARY KEY,
            report_sha256 TEXT NOT NULL,
            report_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS frontier_statements (
            statement_id TEXT PRIMARY KEY, payload TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS frontier_findings (
            finding_id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES frontier_reports(campaign_id),
            statement_id TEXT NOT NULL REFERENCES frontier_statements(statement_id),
            status TEXT NOT NULL CHECK (status IN
                ('REFUTED', 'EXPERIMENTALLY_SUPPORTED')),
            evidence_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS frontier_motivations (
            link_id TEXT PRIMARY KEY,
            finding_id TEXT NOT NULL REFERENCES frontier_findings(finding_id),
            source_finding_id TEXT NOT NULL REFERENCES federation_nodes(node_id),
            proof_reference_json TEXT NOT NULL)""",
        """CREATE INDEX IF NOT EXISTS frontier_findings_statement
            ON frontier_findings(statement_id)""",
    )
    for ddl in ddls:
        db.execute(ddl)


def _sources(db: sqlite3.Connection) -> tuple[list[dict], dict]:
    # Checks original graph, four-domain federation and complete historical
    # Lean source linkage. No source status is upgraded in this pass.
    audit_formal(db)
    graph_reports = load_graph_sources(db)
    nodes = {
        node_id: (kind, json.loads(payload))
        for node_id, kind, payload in db.execute(
            "SELECT node_id,kind,payload FROM federation_nodes")
    }
    if not graph_reports:
        raise ValueError("frontier import requires original v0.5 graph campaigns")
    return graph_reports, nodes


def _expected(reports: list[dict], graph_sources: list[dict],
              source_nodes: dict) -> tuple[dict, dict, dict]:
    """Reconstruct exact typed targets, finding records and source proof edges."""
    source_by_campaign = {
        report["campaign_id"]: report for report in graph_sources
    }
    original_findings = {
        (cid, f["candidate_id"]): f
        for cid, source in source_by_campaign.items()
        for f in source["findings"]
    }
    statements: dict[str, str] = {}
    findings: dict[str, tuple[str, str, str, str]] = {}
    motivations: dict[str, tuple[str, str, str]] = {}
    for report in sorted(reports, key=lambda r: r["campaign_id"]):
        if report.get("schema") != FRONTIER_SCHEMA or report.get("complete") is not True:
            raise ValueError("unknown or partial graph frontier report")
        audit_frontier(report, graph_sources)  # Full deterministic source/experiment replay.
        cid = report["campaign_id"]
        for item in report["findings"]:
            statement = item["statement"]
            if (statement.get("n") not in (6, 7) or
                    statement["n"] != report["configuration"]["target_order"] or
                    item["status"] not in EXPERIMENTAL or item["proof"] is not None or
                    item["formal_lean_verification"] != "NOT_PERFORMED"):
                raise ValueError("frontier experiment cannot be treated as proof")
            statement_id = _node_id("statement", ["graph", statement])
            statements[statement_id] = stable({
                "domain": "graph", "statement": statement,
                "scope": "exact graph order; only bounded evidence imported",
                "proof_at_target_order": False,
                "lean_formal_verification": "NOT_PERFORMED",
                "originality": "NOT_ASSESSED",
            })
            finding_id = _node_id("frontier_finding", [cid, item["candidate_id"]])
            recorded = (cid, statement_id, item["status"], stable(item))
            if finding_id in findings and findings[finding_id] != recorded:
                raise ValueError("frontier finding ID collision")
            findings[finding_id] = recorded
            for proof in item["source_proofs"]:
                source_cid = proof["campaign_id"]
                key = (source_cid, proof["candidate_id"])
                original = original_findings.get(key)
                if (original is None or
                        original["status"] != "PROVED_IN_SUPPORTED_FRAGMENT" or
                        original["statement"]["n"] != 5 or
                        original["proof"]["certificate"]["vacuous"] is not False or
                        digest(original["proof"]["certificate"]) !=
                            proof["proof_certificate_sha256"]):
                    raise ValueError("frontier motivation has no genuine n=5 proof")
                source_id = _node_id(
                    "finding", ["graph:" + source_cid, proof["candidate_id"]])
                if (source_id not in source_nodes or
                        source_nodes[source_id][0] != "finding" or
                        source_nodes[source_id][1]["status"] !=
                            "PROVED_IN_SUPPORTED_FRAGMENT"):
                    raise ValueError("frontier motivation is not federated")
                link_id = _node_id("frontier_motivation",
                                   [finding_id, source_id])
                motivations[link_id] = (
                    finding_id, source_id, stable({
                        "source_proof": proof,
                        "logical_implication": False,
                        "motivates_experiment_only": True,
                    }))
    return statements, findings, motivations


def _audit(db: sqlite3.Connection) -> tuple[dict, dict, dict]:
    graphs, nodes = _sources(db)
    _tables(db)
    saved: dict[str, dict] = {}
    for cid, sha256, payload in db.execute(
            "SELECT campaign_id,report_sha256,report_json FROM frontier_reports"):
        report = json.loads(payload)
        if (stable(report) != payload or digest(report) != sha256 or
                report.get("campaign_id") != cid):
            raise ValueError("frontier original report corrupted")
        saved[cid] = report
    expected = _expected(list(saved.values()), graphs, nodes)
    statements = dict(db.execute(
        "SELECT statement_id,payload FROM frontier_statements"))
    findings = {
        fid: (cid, sid, status, payload)
        for fid, cid, sid, status, payload in db.execute(
            "SELECT finding_id,campaign_id,statement_id,status,evidence_json "
            "FROM frontier_findings")
    }
    motives = {
        link_id: (finding_id, source_id, payload)
        for link_id, finding_id, source_id, payload in db.execute(
            "SELECT link_id,finding_id,source_finding_id,proof_reference_json "
            "FROM frontier_motivations")
    }
    if expected != (statements, findings, motives):
        raise ValueError("frontier materialization disagrees with full source replay")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("frontier has orphan source evidence references")
    return expected


def _summary(tables: tuple[dict, dict, dict]) -> dict:
    statements, findings, motives = tables
    statuses = Counter(row[2] for row in findings.values())
    orders = Counter(json.loads(item)["statement"]["n"]
                     for item in statements.values())
    return {
        "schema": SCHEMA,
        "audit": "ACCEPTED",
        "distinct_exact_order_statements": len(statements),
        "finding_records": len(findings),
        "source_proof_motivation_links": len(motives),
        "status_counts": dict(sorted(statuses.items())),
        "statement_orders": dict(sorted(orders.items())),
        "proofs_at_target_order": 0,
        "external_lean_execution_attestation": "NOT_PERFORMED",
        "knowledge_federation_status_upgrades": 0,
        "novelty": "NOT_ASSESSED",
    }


def frontier_lineage_summary(db_path: str) -> dict:
    with _open(db_path, existing=True) as db:
        tables = _audit(db)
    return _summary(tables)


def import_frontier_lineage(db_path: str, report_paths: list[str]) -> dict:
    if not 1 <= len(report_paths) <= MAX_BATCH:
        raise ValueError("frontier import requires 1..32 experimental reports")
    incoming: list[dict] = []
    for filename in report_paths:
        path = Path(filename)
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("frontier input report exceeds allowed size")
        report = json.loads(path.read_text(encoding="utf-8"))
        if type(report) is not dict:
            raise ValueError("frontier report must be a JSON object")
        incoming.append(report)
    with _open(db_path, existing=True) as db:
        _tables(db)
        _audit(db)  # Refuse to repair a corrupted existing frontier index.
        graphs, nodes = _sources(db)
        all_reports = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                "SELECT campaign_id,report_json FROM frontier_reports")
        }
        for report in incoming:
            cid = report.get("campaign_id")
            if type(cid) is not str or not cid:
                raise ValueError("missing typed frontier campaign ID")
            if cid in all_reports and stable(all_reports[cid]) != stable(report):
                raise ValueError("conflicting immutable graph-frontier experiment")
            all_reports[cid] = report
        reports = sorted(all_reports.values(), key=lambda r: r["campaign_id"])
        statements, findings, motivations = _expected(reports, graphs, nodes)
        with db:
            for report in reports:
                db.execute("INSERT OR IGNORE INTO frontier_reports VALUES (?,?,?)",
                           (report["campaign_id"], digest(report), stable(report)))
            db.execute("DELETE FROM frontier_motivations")
            db.execute("DELETE FROM frontier_findings")
            db.execute("DELETE FROM frontier_statements")
            db.executemany(
                "INSERT INTO frontier_statements VALUES (?,?)",
                sorted(statements.items()))
            db.executemany(
                "INSERT INTO frontier_findings VALUES (?,?,?,?,?)",
                [(fid, *row) for fid, row in sorted(findings.items())])
            db.executemany(
                "INSERT INTO frontier_motivations VALUES (?,?,?,?)",
                [(lid, *row) for lid, row in sorted(motivations.items())])
    return frontier_lineage_summary(db_path)


def query_frontier_lineage(db_path: str, *, order: int | None = None,
                          status: str | None = None,
                          offset: int = 0, limit: int = 20) -> list[dict]:
    if order is not None and (type(order) is not int or order not in (6, 7)):
        raise ValueError("frontier order must be 6 or 7")
    if status is not None and status not in EXPERIMENTAL:
        raise ValueError("unsupported frontier evidence state")
    if type(offset) is not int or not 0 <= offset <= 100_000:
        raise ValueError("invalid frontier offset")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("frontier limit must be 1..100")
    with _open(db_path, existing=True) as db:
        statements, findings, motivations = _audit(db)
    grouped = defaultdict(list)
    for fid, (cid, sid, state, payload) in findings.items():
        grouped[sid].append((fid, cid, state, json.loads(payload)))
    results = []
    for sid in sorted(statements):
        subject = json.loads(statements[sid])["statement"]
        if order is not None and subject["n"] != order:
            continue
        related = sorted(grouped[sid])
        statuses = sorted({state for _, _, state, _ in related})
        if status is not None and status not in statuses:
            continue
        refutations = [
            {"campaign_id": cid, "counterexample": entry["search"]["counterexample"]}
            for _, cid, state, entry in related if state == "REFUTED"
        ]
        results.append({
            "statement_id": sid,
            "statement": subject,
            "statuses": statuses,
            "refuted_at_exact_order": bool(refutations),
            "counterexamples": refutations,
            "campaign_ids": sorted({cid for _, cid, _, _ in related}),
            "max_structures_checked": max(
                entry["search"]["structures_checked"]
                for _, _, _, entry in related),
            "proofs_at_exact_order": 0,
            "cross_order_entailment": False,
            "novelty": "NOT_ASSESSED",
        })
    return results[offset:offset + limit]
