"""AXIOM v0.6: evidence-preserving mathematical knowledge graph (finite graphs).

An auditable materialized view of independently replayed, COMPLETE v0.5 graph
campaigns. Order analogues are NAVIGATION links, never implications or proofs.
No status can be upgraded by the knowledge graph itself.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sqlite3
from typing import Any

from .graph_campaign import SCHEMA as GRAPH_SCHEMA, audit_graph_report
from .graph_claims import GraphStatement, digest, stable

SCHEMA = "axiom.knowledge_graph.v1"
MAX_REPORT_BYTES = 8_000_000
MAX_REPORTS = 64
CHECKER_ID = "checker:axiom.graph_checker.check_finite_certificate:v1"


def _id(kind: str, payload: Any) -> str:
    return kind + ":" + digest(payload)


def _validated_reports(reports: list[dict]) -> list[dict]:
    if not reports or len(reports) > MAX_REPORTS:
        raise ValueError("knowledge graph requires 1..64 source reports")
    by_campaign: dict[str, dict] = {}
    for report in reports:
        if not isinstance(report, dict) or report.get("schema") != GRAPH_SCHEMA:
            raise ValueError("unsupported report domain/schema")
        if not report.get("progress", {}).get("complete", False):
            raise ValueError("partial campaigns cannot be imported")
        audit_graph_report(report)
        cid = report["campaign_id"]
        if cid in by_campaign and stable(by_campaign[cid]) != stable(report):
            raise ValueError("conflicting snapshots for the same campaign ID")
        by_campaign[cid] = report
    return [by_campaign[key] for key in sorted(by_campaign)]


def materialize(reports: list[dict]) -> tuple[dict, dict]:
    """Return deterministic nodes/edges after COMPLETE source replay.

    This deliberately has no unsupported graph-theorem inference or probabilistic
    confidence aggregation. Each finding retains its original evidence status.
    """
    reports = _validated_reports(reports)
    nodes: dict[str, tuple[str, str]] = {}
    edges: dict[str, tuple[str, str, str, str]] = {}
    families: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
    by_statement: dict[str, set[str]] = defaultdict(set)

    def node(key: str, kind: str, payload: dict) -> None:
        record = (kind, stable(payload))
        if key in nodes and nodes[key] != record:
            raise ValueError("conflicting node identities")
        nodes[key] = record

    def edge(source: str, relation: str, target: str, attrs: dict | None = None) -> None:
        attributes = attrs or {}
        key = _id("edge", [source, relation, target, attributes])
        value = (source, relation, target, stable(attributes))
        if key in edges and edges[key] != value:
            raise ValueError("conflicting edge identities")
        edges[key] = value

    node(CHECKER_ID, "checker", {
        "checker": "axiom.graph_checker.check_finite_certificate",
        "method": "independent exhaustive enumeration",
        "max_order": 5, "formal_lean_verification": False,
        "trust": "Python reference checker plus shared declarative claim interpreter"})
    for report in reports:
        cid = report["campaign_id"]
        campaign_id = "campaign:" + cid
        node(campaign_id, "campaign", {
            "campaign_id": cid, "configuration": report["configuration"],
            "source_report_digest": digest(report),
            "progress": report["progress"], "counts": report["counts"]})
        for finding in report["findings"]:
            stmt = GraphStatement.from_dict(finding["statement"])
            sd = stmt.to_dict()
            sid = _id("statement", sd)
            fid = _id("finding", [cid, finding["candidate_id"]])
            family = _id("family", [stmt.template, stmt.k])
            node(sid, "statement", {
                "statement": sd, "domain": "finite_simple_graphs_fixed_exact_order",
                "originality": "NOT_ASSESSED"})
            node(family, "template_family", {
                "template": stmt.template, "k": stmt.k,
                "relationship": "same predicate template; logical entailment not established"})
            node(fid, "finding", {
                "candidate_id": finding["candidate_id"], "ordinal": finding["ordinal"],
                "campaign_id": cid, "origin": finding["origin"],
                "status": finding["status"], "history": finding["history"],
                "originality": finding["originality"], "scope_order": stmt.n})
            edge(fid, "RECORDED_IN", campaign_id)
            edge(fid, "INVESTIGATES", sid)
            edge(sid, "INSTANCE_OF", family)
            by_statement[sid].add(finding["status"])
            families[(stmt.template, stmt.k)].append((stmt.n, sid))
            # Store exact bounded search evidence irrespective of conclusion.
            search_id = _id("search", [sid, finding["search"]])
            node(search_id, "search", {
                "statement_id": sid, "search": finding["search"],
                "exhaustive_proof": False})
            edge(fid, "SEARCH_EVIDENCE", search_id)
            if finding["status"] == "REFUTED":
                witness = finding["search"]["counterexample"]
                witness_id = _id("counterexample", [sid, witness])
                node(witness_id, "counterexample", {
                    "statement_id": sid, "graph": witness,
                    "rechecked": "axiom.graph_checker.check_graph_witness"})
                edge(fid, "REFUTED_BY", witness_id)
            elif finding["status"] == "PROVED_IN_SUPPORTED_FRAGMENT":
                certificate = finding["proof"]["certificate"]
                proof_id = _id("finite_proof", [sid, certificate])
                node(proof_id, "finite_proof", {
                    "statement_id": sid, "certificate": certificate,
                    "scope": "all labelled simple graphs of exactly n<=5",
                    "formal_lean_verification": False})
                edge(fid, "SUPPORTED_BY_FINITE_PROOF", proof_id)
                edge(proof_id, "DEPENDS_ON_CHECKER", CHECKER_ID,
                     {"dependency_type": "trusted_python_checker",
                      "not_a_math_theorem_dependency": True})
            else:
                # An experiment has NO proof or refutation relationship.
                edge(fid, "EXPERIMENTALLY_TESTED_BY", search_id,
                     {"does_not_establish_truth": True})

    for sid, statuses in by_statement.items():
        if "REFUTED" in statuses and "PROVED_IN_SUPPORTED_FRAGMENT" in statuses:
            raise ValueError("one exact-order statement has both proof and refutation")
    for records in families.values():
        ordered = sorted(set(records))
        for (n1, sid1), (n2, sid2) in zip(ordered, ordered[1:]):
            if n1 == n2:
                raise ValueError("multiple identities for the same template and graph order")
            edge(sid1, "NEXT_ORDER_ANALOGUE", sid2, {
                "from_order": n1, "to_order": n2,
                "logical_implication": False,
                "universal_generalization": False})
    if any(source not in nodes or target not in nodes
           for source, _, target, _ in edges.values()):
        raise ValueError("orphan graph edge")
    return nodes, edges


def _open(path: str, *, existing: bool) -> sqlite3.Connection:
    target = Path(path)
    if existing and not target.is_file():
        raise ValueError("knowledge database does not exist")
    if not existing:
        target.parent.mkdir(parents=True, exist_ok=True)
    uri = f"file:{target.resolve().as_posix()}?mode={'rw' if existing else 'rwc'}"
    db = sqlite3.connect(uri, uri=True)
    db.execute("PRAGMA foreign_keys=ON")
    if not existing:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS kg_meta (
            k TEXT PRIMARY KEY, v TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS kg_reports (
            report_digest TEXT PRIMARY KEY, campaign_id TEXT NOT NULL UNIQUE,
            report_json TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS kg_nodes (
            node_id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS kg_edges (
            edge_id TEXT PRIMARY KEY, source TEXT NOT NULL REFERENCES kg_nodes(node_id),
            relation TEXT NOT NULL, target TEXT NOT NULL REFERENCES kg_nodes(node_id),
            attributes TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS kg_edges_from ON kg_edges(source);
          CREATE INDEX IF NOT EXISTS kg_edges_to ON kg_edges(target);
        """)
        db.execute("INSERT OR IGNORE INTO kg_meta VALUES ('schema', ?)", (SCHEMA,))
        db.commit()
    return db


def _load(db: sqlite3.Connection) -> list[dict]:
    meta = db.execute("SELECT v FROM kg_meta WHERE k='schema'").fetchone()
    if meta != (SCHEMA,):
        raise ValueError("unsupported knowledge schema")
    rows = db.execute("SELECT report_digest,campaign_id,report_json FROM kg_reports").fetchall()
    if not rows:
        return []
    reports = []
    for hash_value, cid, payload in rows:
        report = json.loads(payload)
        if (stable(report) != payload or digest(report) != hash_value
                or report.get("campaign_id") != cid):
            raise ValueError("tampered source report provenance")
        reports.append(report)
    return _validated_reports(reports)


def _assert_integrity(db: sqlite3.Connection) -> tuple[dict, dict]:
    if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise ValueError("SQLite integrity check failed")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("orphan foreign-key reference")
    reports = _load(db)
    if reports:
        expected_nodes, expected_edges = materialize(reports)
    else:
        expected_nodes, expected_edges = {}, {}
    observed_nodes = {k: (kind, payload) for k, kind, payload in
                      db.execute("SELECT node_id,kind,payload FROM kg_nodes")}
    observed_edges = {k: (src, rel, dst, attrs) for k, src, rel, dst, attrs in
                      db.execute("SELECT edge_id,source,relation,target,attributes FROM kg_edges")}
    if expected_nodes != observed_nodes or expected_edges != observed_edges:
        raise ValueError("knowledge graph differs from independently replayed source")
    return expected_nodes, expected_edges


def knowledge_summary(db_path: str) -> dict:
    with _open(db_path, existing=True) as db:
        nodes, edges = _assert_integrity(db)
    counts = {kind: sum(rec[0] == kind for rec in nodes.values()) for kind in
              ("campaign", "statement", "finding", "finite_proof",
               "counterexample", "search", "template_family")}
    return {"schema": SCHEMA, "audit": "ACCEPTED",
            "nodes": len(nodes), "edges": len(edges), "counts": counts,
            "graph_lean_formal_verification": "NOT_PERFORMED",
            "novelty": "NOT_ASSESSED"}


def build_knowledge_graph(db_path: str, report_paths: list[str]) -> dict:
    if not report_paths or len(report_paths) > MAX_REPORTS:
        raise ValueError("provide 1..64 report paths")
    incoming = []
    for file in report_paths:
        path = Path(file)
        if path.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("research report exceeds import size limit")
        incoming.append(json.loads(path.read_text(encoding="utf-8")))
    _validated_reports(incoming)  # Fail before any database modification.
    with _open(db_path, existing=False) as db:
        _assert_integrity(db)  # Fail closed on any previously corrupted graph.
        existing = _load(db)
        nodes, edges = materialize(existing + incoming)
        by_campaign = {r["campaign_id"]: r for r in existing}
        for r in incoming:
            cid = r["campaign_id"]
            if cid in by_campaign and stable(by_campaign[cid]) != stable(r):
                raise ValueError("immutable campaign snapshot collision")
            by_campaign[cid] = r
        with db:
            for cid, r in sorted(by_campaign.items()):
                db.execute("INSERT OR IGNORE INTO kg_reports VALUES (?,?,?)",
                           (digest(r), cid, stable(r)))
            db.execute("DELETE FROM kg_edges")
            db.execute("DELETE FROM kg_nodes")
            db.executemany("INSERT INTO kg_nodes VALUES (?,?,?)",
                           [(k, *nodes[k]) for k in sorted(nodes)])
            db.executemany("INSERT INTO kg_edges VALUES (?,?,?,?,?)",
                           [(k, *edges[k]) for k in sorted(edges)])
    return knowledge_summary(db_path)


def query_knowledge(db_path: str, *, template: str | None = None,
                    order: int | None = None, status: str | None = None,
                    limit: int = 20) -> list[dict]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("query limit must be between 1 and 100")
    if order is not None and (type(order) is not int or not 0 <= order <= 7):
        raise ValueError("graph order must be 0..7")
    allowed = {"REFUTED", "PROVED_IN_SUPPORTED_FRAGMENT", "EXPERIMENTALLY_SUPPORTED"}
    if status is not None and status not in allowed:
        raise ValueError("invalid evidence status")
    with _open(db_path, existing=True) as db:
        nodes, edges = _assert_integrity(db)
    collected = defaultdict(list)
    for src, rel, dst, _ in edges.values():
        if rel == "INVESTIGATES":
            collected[dst].append(nodes[src][1])
    result = []
    for sid, (kind, payload) in sorted(nodes.items()):
        if kind != "statement":
            continue
        data = json.loads(payload)["statement"]
        if (template is not None and data["template"] != template
                or order is not None and data["n"] != order):
            continue
        findings = [json.loads(x) for x in collected[sid]]
        statuses = sorted({f["status"] for f in findings})
        if status and status not in statuses:
            continue
        result.append({"statement_id": sid, "statement": data,
                       "statuses": statuses, "campaign_ids": sorted({
                           f["campaign_id"] for f in findings})})
        if len(result) >= limit:
            break
    return result


def knowledge_neighbors(db_path: str, node_id: str, limit: int = 100) -> dict:
    if not isinstance(node_id, str) or not node_id or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("invalid node ID or neighbor limit")
    with _open(db_path, existing=True) as db:
        nodes, edges = _assert_integrity(db)
    if node_id not in nodes:
        raise ValueError("unknown knowledge node")
    related = [{"edge_id": eid, "source": src, "relation": rel, "target": dst,
                "attributes": json.loads(attrs)}
               for eid, (src, rel, dst, attrs) in sorted(edges.items())
               if src == node_id or dst == node_id]
    return {"node_id": node_id, "kind": nodes[node_id][0],
            "payload": json.loads(nodes[node_id][1]),
            "total_relationships": len(related),
            "relationships": related[:limit]}
