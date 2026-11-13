"""AXIOM v0.7: fail-closed, typed mathematical evidence federation.

Materialized overlay in the existing v0.6 SQLite knowledge database. Existing
kg_nodes/kg_edges and historical source reports remain completely unchanged.
Replays every source with its domain-specific auditor on every integrity check.
This index *never* upgrades local evidence to Lean FORMALLY_VERIFIED.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sqlite3
from typing import Any

from .graph_claims import digest, stable
from .knowledge_graph import _open, _assert_integrity, _load as _graph_reports

SCHEMA = "axiom.knowledge_federation.v1"
MAX_BYTES = 8_000_000
MAX_IMPORTS = 32
DOMAINS = {
    "axiom.graph.campaign.v1": "graph",
    "axiom.v0.2.report": "algebra",
    "axiom.number_theory.report.v1": "number_theory",
    "axiom.recurrence.campaign.v1": "recurrence",
}
CHECKERS = {
    "graph": "axiom.graph_checker.check_finite_certificate",
    "algebra": "axiom.certificate_checker.check_certificate",
    "number_theory": "axiom.number_theory_checker.check_nt_certificate",
    "recurrence": "axiom.recurrence_checker.check_recurrence_certificate",
}


def _source_id(report: dict) -> str:
    domain = DOMAINS[report["schema"]]
    return domain + ":" + (digest(report)[:24] if domain == "recurrence"
                           else report["campaign_id"])


def _validate(report: dict) -> str:
    if type(report) is not dict or report.get("schema") not in DOMAINS:
        raise ValueError("unsupported mathematical report schema")
    domain = DOMAINS[report["schema"]]
    if domain != "recurrence" and report.get("progress", {}).get("complete") is not True:
        raise ValueError("partial mathematical campaigns cannot enter federation")
    if domain == "graph":
        from .graph_campaign import audit_graph_report
        audit_graph_report(report)
    elif domain == "algebra":
        from .evidence import audit_report
        audit_report(report)
    elif domain == "number_theory":
        from .number_theory_campaign import audit_nt_report
        audit_nt_report(report)
    else:
        from .recurrences import audit_sequence_campaign
        audit_sequence_campaign(report)
    return domain


def _registry(reports: list[dict]) -> dict[str, dict]:
    if len(reports) > MAX_IMPORTS + 64:
        raise ValueError("too many federated report sources")
    result = {}
    for r in reports:
        _validate(r)
        key = _source_id(r)
        if key in result and stable(result[key]) != stable(r):
            raise ValueError("conflicting immutable campaign/source snapshot")
        result[key] = r
    return result


def _node_id(kind: str, data: Any) -> str:
    return kind + ":" + digest(data)


def _build(reports: list[dict]) -> tuple[dict, dict]:
    registry = _registry(reports)
    nodes: dict[str, tuple[str, str]] = {}
    edges: dict[str, tuple[str, str, str, str]] = {}
    statuses: dict[str, set[str]] = {}

    def node(key: str, kind: str, data: dict) -> None:
        record = (kind, stable(data))
        if key in nodes and nodes[key] != record:
            raise ValueError("node identity collision")
        nodes[key] = record

    def edge(src: str, rel: str, dst: str) -> None:
        key = _node_id("link", [src, rel, dst])
        edges[key] = (src, rel, dst, "{}")

    for sid, report in sorted(registry.items()):
        domain = DOMAINS[report["schema"]]
        domain_id = "domain:" + domain
        source_id = "source:" + sid
        node(domain_id, "domain", {
            "name": domain, "schema": report["schema"],
            "independent_statement_semantics": True})
        node(source_id, "source", {
            "source_id": sid, "domain": domain, "report_sha256": digest(report),
            "report_schema": report["schema"], "audited_by": {
                "graph": "axiom.graph_campaign.audit_graph_report",
                "algebra": "axiom.evidence.audit_report",
                "number_theory": "axiom.number_theory_campaign.audit_nt_report",
                "recurrence": "axiom.recurrences.audit_sequence_campaign",
            }[domain]})
        edge(source_id, "BELONGS_TO_DOMAIN", domain_id)
        checker_id = "checker:" + domain
        node(checker_id, "checker", {
            "domain": domain, "name": CHECKERS[domain],
            "verified_by": "domain-specific Python checker",
            "lean_formal_verification": False})
        for finding in report["findings"]:
            if domain == "recurrence":
                certificate = finding["certificate"]
                subject = {
                    "specification": finding["specification"],
                    "preperiod": certificate["preperiod"],
                    "period": certificate["period"],
                    "scope": "eventual modular ordered-pair periodicity"}
                candidate = digest([finding["ordinal"], subject])
            else:
                subject = finding["statement"]
                candidate = finding["candidate_id"]
                certificate = finding["proof"]["certificate"] if finding["proof"] else None
            statement_id = _node_id("statement", [domain, subject])
            finding_id = _node_id("finding", [sid, candidate])
            state = finding["status"]
            if state not in {"REFUTED", "PROVED_IN_SUPPORTED_FRAGMENT",
                             "EXPERIMENTALLY_SUPPORTED", "UNRESOLVED"}:
                raise ValueError("unsupported evidence state in federation")
            statuses.setdefault(statement_id, set()).add(state)
            node(statement_id, "statement", {
                "domain": domain, "statement": subject,
                "identity_scope": "same domain and exact typed statement",
                "originality": "NOT_ASSESSED"})
            node(finding_id, "finding", {
                "domain": domain, "source_id": sid, "candidate_id": candidate,
                "ordinal": finding["ordinal"], "status": state,
                "originality": "NOT_ASSESSED",
                "formal_lean_status": "NOT_IMPORTED"})
            edge(finding_id, "RECORDED_IN", source_id)
            edge(finding_id, "INVESTIGATES", statement_id)
            edge(statement_id, "BELONGS_TO_DOMAIN", domain_id)
            if domain != "recurrence":
                evidence = finding["search"]
                search_id = _node_id("search", [domain, subject, evidence])
                node(search_id, "search", {
                    "domain": domain, "search": evidence,
                    "independently_audited_as_part_of_source": True,
                    "not_a_proof": True})
                edge(finding_id, "SEARCH_EVIDENCE", search_id)
                witness = evidence.get("counterexample")
                if state == "REFUTED":
                    if witness is None:
                        raise ValueError("refutation without counterexample")
                    witness_id = _node_id("counterexample", [domain, subject, witness])
                    node(witness_id, "counterexample", {
                        "domain": domain, "witness": witness,
                        "checked_by_original_domain_auditor": True})
                    edge(finding_id, "REFUTED_BY", witness_id)
                elif witness is not None:
                    raise ValueError("non-refutation has a falsifying witness")
            if state == "PROVED_IN_SUPPORTED_FRAGMENT":
                if not isinstance(certificate, dict):
                    raise ValueError("local proof missing certificate")
                proof_id = _node_id("local_proof", [domain, subject, certificate])
                node(proof_id, "local_proof", {
                    "domain": domain, "certificate": certificate,
                    "scope": ("exact fixed graph order" if domain == "graph" else
                              "eventual modular recurrence state" if domain == "recurrence" else
                              "supported integer-polynomial fragment"),
                    "lean_formal_verification": False})
                edge(finding_id, "LOCALLY_CERTIFIED_BY", proof_id)
                edge(proof_id, "DEPENDS_ON_PYTHON_CHECKER", checker_id)
            elif certificate is not None:
                raise ValueError("non-proved finding contains proof")
            elif state == "EXPERIMENTALLY_SUPPORTED":
                edge(finding_id, "OBSERVATION_ONLY", statement_id)
    if any("REFUTED" in set_ and "PROVED_IN_SUPPORTED_FRAGMENT" in set_
           for set_ in statuses.values()):
        raise ValueError("contradictory exact-domain evidence status")
    if any(a not in nodes or b not in nodes for a, _, b, _ in edges.values()):
        raise ValueError("orphan federated relationship")
    return nodes, edges


def _tables(db: sqlite3.Connection) -> None:
    db.executescript("""
      CREATE TABLE IF NOT EXISTS federation_sources (
        source_id TEXT PRIMARY KEY, report_digest TEXT NOT NULL, report_json TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS federation_nodes (
        node_id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS federation_edges (
        edge_id TEXT PRIMARY KEY,
        source TEXT NOT NULL REFERENCES federation_nodes(node_id),
        relation TEXT NOT NULL,
        target TEXT NOT NULL REFERENCES federation_nodes(node_id),
        attrs TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS federation_edge_from ON federation_edges(source);
    """)


def _sources(db: sqlite3.Connection) -> list[dict]:
    _tables(db)
    result = []
    for sid, saved_digest, payload in db.execute(
            "SELECT source_id,report_digest,report_json FROM federation_sources"):
        report = json.loads(payload)
        if (stable(report) != payload or digest(report) != saved_digest
                or _source_id(report) != sid or DOMAINS[report["schema"]] == "graph"):
            raise ValueError("tampered or invalid federated source report")
        result.append(report)
    return result


def _audit(db: sqlite3.Connection) -> tuple[dict, dict]:
    _assert_integrity(db)  # Always verify the original v0.6 graph in full.
    reports = _graph_reports(db) + _sources(db)
    nodes, edges = _build(reports)
    actual_nodes = {k: (kind, payload) for k, kind, payload in db.execute(
        "SELECT node_id,kind,payload FROM federation_nodes")}
    actual_edges = {k: (a, rel, b, attrs) for k, a, rel, b, attrs in db.execute(
        "SELECT edge_id,source,relation,target,attrs FROM federation_edges")}
    if nodes != actual_nodes or edges != actual_edges:
        raise ValueError("federation does not match replayed source evidence")
    return nodes, edges


def federation_summary(db_path: str) -> dict:
    with _open(db_path, existing=True) as db:
        nodes, edges = _audit(db)
    kinds = Counter(k for k, _ in nodes.values())
    per_domain = Counter(json.loads(data)["domain"] for kind, data in nodes.values()
                         if kind == "statement")
    return {
        "schema": SCHEMA, "audit": "ACCEPTED",
        "nodes": len(nodes), "edges": len(edges),
        "counts": dict(sorted(kinds.items())),
        "distinct_statements_by_domain": dict(sorted(per_domain.items())),
        "lean_verification_in_federation": "NOT_IMPORTED",
        "historical_lean_evidence": "preserved separately, not inferred",
        "novelty": "NOT_ASSESSED"}


def federate(db_path: str, paths: list[str]) -> dict:
    if not paths or len(paths) > MAX_IMPORTS:
        raise ValueError("import requires 1..32 complete source reports")
    incoming = []
    for raw in paths:
        path = Path(raw)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("source report exceeds permitted size")
        obj = json.loads(path.read_text(encoding="utf-8"))
        if _validate(obj) == "graph":
            raise ValueError("graph reports belong in knowledge-build, not federation import")
        incoming.append(obj)
    with _open(db_path, existing=True) as db:
        _tables(db)
        # Audit existing graph and any previously federated material before mutation.
        _audit(db) if db.execute("SELECT COUNT(*) FROM federation_nodes").fetchone()[0] else _assert_integrity(db)
        old = _sources(db)
        registry = _registry(old + incoming)
        full = _graph_reports(db) + list(registry.values())
        nodes, edges = _build(full)
        with db:
            for sid, report in registry.items():
                payload = stable(report)
                present = db.execute(
                    "SELECT report_json FROM federation_sources WHERE source_id=?", (sid,)).fetchone()
                if present is not None and present[0] != payload:
                    raise ValueError("immutable federation source collision")
                db.execute("INSERT OR IGNORE INTO federation_sources VALUES (?,?,?)",
                           (sid, digest(report), payload))
            db.execute("DELETE FROM federation_edges")
            db.execute("DELETE FROM federation_nodes")
            db.executemany("INSERT INTO federation_nodes VALUES (?,?,?)",
                           [(key, *nodes[key]) for key in sorted(nodes)])
            db.executemany("INSERT INTO federation_edges VALUES (?,?,?,?,?)",
                           [(key, *edges[key]) for key in sorted(edges)])
    return federation_summary(db_path)


def query_federation(db_path: str, *, domain: str | None = None,
                     status: str | None = None, limit: int = 20) -> list[dict]:
    if domain is not None and domain not in set(DOMAINS.values()):
        raise ValueError("unknown mathematical domain")
    if status is not None and status not in {
        "PROVED_IN_SUPPORTED_FRAGMENT", "REFUTED", "EXPERIMENTALLY_SUPPORTED", "UNRESOLVED"}:
        raise ValueError("unknown evidence status")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("invalid query limit")
    with _open(db_path, existing=True) as db:
        nodes, edges = _audit(db)
    links: dict[str, list[str]] = {}
    for src, relation, dst, _ in edges.values():
        if relation == "INVESTIGATES":
            links.setdefault(dst, []).append(src)
    results = []
    for key in sorted(nodes):
        kind, payload = nodes[key]
        if kind != "statement":
            continue
        data = json.loads(payload)
        if domain is not None and data["domain"] != domain:
            continue
        related = [json.loads(nodes[ref][1]) for ref in links.get(key, [])]
        state_set = sorted({finding["status"] for finding in related})
        if status and status not in state_set:
            continue
        results.append({
            "statement_id": key, "domain": data["domain"],
            "statement": data["statement"], "statuses": state_set,
            "source_ids": sorted({f["source_id"] for f in related})})
        if len(results) >= limit:
            break
    return results
