"""AXIOM v0.14 — deterministic graph research plan from reconciled evidence.

The planner NEVER edits historical research or promotes bounded observations.
Every plan is derived only after full independent replay of the original
graph/federation/formal, n=6/7 bounded frontier and exact n=6 source auditors.

Evidence identity is the exact typed graph statement (including graph order),
NOT the shared template family. Proof of an n=6 instance says nothing about
n=7, and a stored offline Lean record is never an execution attestation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import tempfile

from .graph_claims import GraphStatement, digest, stable
from .knowledge_graph import _open
from .knowledge_federation import _node_id
from .knowledge_exact_n6 import _audit as audit_exact_n6
from .knowledge_agenda import _source_fingerprint as base_fingerprint

SCHEMA = "axiom.graph_research_agenda.v1"
POLICY = "exact_statement_refutations_first_n6_verified_exhaustion_v1"
STATUSES = {"REFUTED", "EXPERIMENTALLY_SUPPORTED",
            "PROVED_IN_SUPPORTED_FRAGMENT", "UNRESOLVED"}
ACTIONS = {
    "EXTEND_BOUNDED_FALSIFICATION": 1,
    "FALSIFY_WITH_INDEPENDENT_SEARCH": 2,
    "FORMALIZE_EXACT_N6_IN_LEAN": 3,
    "FORMALIZE_LOCAL_FINITE_PROOF_IN_LEAN": 4,
}


def _arguments(order: int | None, limit: int, offset: int) -> None:
    if order is not None and (type(order) is not int or order not in range(8)):
        raise ValueError("graph order filter must be an integer from 0 through 7")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("graph agenda limit must be 1..100")
    if type(offset) is not int or not 0 <= offset <= 100_000:
        raise ValueError("graph agenda offset must be 0..100000")


def _fingerprint(db) -> str:
    return digest({
        "v010": base_fingerprint(db),
        "v011_frontier": sorted(db.execute(
            "SELECT campaign_id,report_sha256 FROM frontier_reports").fetchall()),
        "v013_exact_n6": sorted(db.execute(
            "SELECT campaign_id,report_sha256 FROM exact_n6_reports").fetchall()),
    })


def _add(groups: dict, statement: dict, layer: str, state: str,
         source_id: str, finding_id: str, certificate: dict | None = None,
         local_proof_ids: list[str] | None = None, sampled: int = 0) -> None:
    stmt = GraphStatement.from_dict(statement)
    if state not in STATUSES or layer not in ("original", "frontier", "exact_n6"):
        raise ValueError("invalid graph evidence state or source layer")
    if layer == "exact_n6" and stmt.n != 6:
        raise ValueError("exact proof evidence cannot cross graph orders")
    if type(sampled) is not int or sampled < 0:
        raise ValueError("invalid graph evidence search coverage")
    sid = _node_id("statement", ["graph", stmt.to_dict()])
    record = groups.setdefault(sid, {
        "statement": stmt.to_dict(),
        "states": defaultdict(set),
        "sources": defaultdict(set),
        "findings": defaultdict(set),
        "certificates": set(),
        "local_proofs": set(),
        "sampled": 0,
    })
    if record["statement"] != stmt.to_dict():
        raise ValueError("graph statement identity collision")
    record["states"][layer].add(state)
    record["sources"][layer].add(source_id)
    record["findings"][layer].add(finding_id)
    if certificate is not None:
        record["certificates"].add(digest(certificate))
    if local_proof_ids:
        record["local_proofs"].update(local_proof_ids)
    if sampled > record["sampled"]:
        record["sampled"] = sampled


def _materialized_plan(db, exact) -> tuple[list[dict], int, int]:
    """Operate on materialized rows ONLY after audit_exact_n6 has validated them."""
    exact_statements, exact_findings, _ = exact
    groups = {}
    federation_nodes = {
        key: (kind, json.loads(payload))
        for key, kind, payload in db.execute(
            "SELECT node_id,kind,payload FROM federation_nodes")
    }
    investigations = defaultdict(set)
    local_proof_links = defaultdict(set)
    for src, relation, dst in db.execute(
            "SELECT source,relation,target FROM federation_edges"):
        if relation == "INVESTIGATES":
            investigations[dst].add(src)
        elif relation == "LOCALLY_CERTIFIED_BY":
            local_proof_links[src].add(dst)

    for sid, (kind, node) in sorted(federation_nodes.items()):
        if kind != "statement" or node["domain"] != "graph":
            continue
        finding_ids = sorted(investigations[sid])
        if not finding_ids:
            raise ValueError("original graph statement without findings")
        for fid in finding_ids:
            fkind, finding = federation_nodes[fid]
            if fkind != "finding" or finding["domain"] != "graph":
                raise ValueError("invalid original graph research link")
            local_ids = local_proof_links.get(fid, set())
            status = finding["status"]
            if ((status == "PROVED_IN_SUPPORTED_FRAGMENT") != bool(local_ids)):
                raise ValueError("original graph proof status missing source certificate")
            statement = node["statement"]
            graph = GraphStatement.from_dict(statement)
            if status == "PROVED_IN_SUPPORTED_FRAGMENT" and graph.n > 5:
                raise ValueError("original certificate used outside verified n<=5 domain")
            _add(groups, statement, "original", status,
                 finding["source_id"], fid,
                 local_proof_ids=sorted(local_ids))

    frontier_statements = {
        sid: json.loads(payload)
        for sid, payload in db.execute(
            "SELECT statement_id,payload FROM frontier_statements")
    }
    for fid, cid, sid, status, evidence in db.execute(
            "SELECT finding_id,campaign_id,statement_id,status,evidence_json "
            "FROM frontier_findings"):
        statement = frontier_statements[sid]["statement"]
        data = json.loads(evidence)
        if status != data["status"] or data["statement"] != statement:
            raise ValueError("bounded finding mismatch")
        _add(groups, statement, "frontier", status, cid, fid,
             sampled=data["search"]["structures_checked"])

    for fid, (cid, sid, status, evidence) in sorted(exact_findings.items()):
        if sid not in exact_statements:
            raise ValueError("orphan exact graph proof")
        data = json.loads(evidence)
        record = json.loads(exact_statements[sid])
        if status != data["status"] or record["statement"] != data["statement"]:
            raise ValueError("exact graph finding mismatch")
        cert = data["certificate"]
        _add(groups, data["statement"], "exact_n6", status, cid, fid,
             certificate=cert, sampled=data["labelled_graphs_checked"])

    tasks = []
    refuted = 0
    examined = len(groups)
    for sid in sorted(groups):
        rec = groups[sid]
        stmt = rec["statement"]
        statuses = {k: sorted(v) for k, v in sorted(rec["states"].items())}
        all_states = {state for values in statuses.values() for state in values}
        if "REFUTED" in all_states:
            if ("PROVED_IN_SUPPORTED_FRAGMENT" in all_states):
                raise ValueError("contradictory full proof and verified counterexample")
            refuted += 1
            continue
        exact_proven = ("PROVED_IN_SUPPORTED_FRAGMENT" in
                        rec["states"].get("exact_n6", set()))
        original_proven = ("PROVED_IN_SUPPORTED_FRAGMENT" in
                           rec["states"].get("original", set()))
        if exact_proven:
            if stmt["n"] != 6 or "REFUTED" in all_states:
                raise ValueError("exact n6 proof beyond supported scope")
            action = "FORMALIZE_EXACT_N6_IN_LEAN"
            rationale = ("Re-express and independently kernel-check the exact "
                         "six-vertex exhaustive certificate in Lean; the "
                         "Python certificate is NOT a Lean proof.")
        elif original_proven:
            if stmt["n"] > 5:
                raise ValueError("original certificate outside supported finite order")
            action = "FORMALIZE_LOCAL_FINITE_PROOF_IN_LEAN"
            rationale = ("Formalize the original finite-order graph certificate "
                         "without extending its proof to other graph orders.")
        elif "frontier" in rec["states"]:
            action = "EXTEND_BOUNDED_FALSIFICATION"
            rationale = ("Investigate this still-unresolved exact-order statement "
                         "with independently checked, larger nonduplicate graph "
                         "samples; bounded survival is not proof.")
        else:
            if all_states - {"EXPERIMENTALLY_SUPPORTED", "UNRESOLVED"}:
                raise ValueError("unrecognized original graph research state")
            action = "FALSIFY_WITH_INDEPENDENT_SEARCH"
            rationale = ("Run an independent falsification campaign on the exact "
                         "typed graph order; no certificate is yet available.")
        if action not in ACTIONS:
            raise ValueError("unknown graph research action")
        tasks.append({
            "task_id": "graph-agenda:" + digest([SCHEMA, sid, action]),
            "priority": ACTIONS[action],
            "action": action,
            "domain": "graph",
            "statement_id": sid,
            "statement": stmt,
            "evidence_by_layer": statuses,
            "source_campaigns_by_layer": {
                k: sorted(v) for k, v in sorted(rec["sources"].items())},
            "originating_findings_by_layer": {
                k: sorted(v) for k, v in sorted(rec["findings"].items())},
            "exact_certificate_sha256": sorted(rec["certificates"]),
            "original_local_proof_ids": sorted(rec["local_proofs"]),
            "maximum_labelled_graphs_checked_in_source": rec["sampled"],
            "rationale": rationale,
            "claim_is_new_theorem": False,
            "all_order_generalization": "NOT_PROVED",
            "lean_formal_verification": "NOT_PERFORMED_BY_PLAN",
            "mathematical_novelty": "NOT_ASSESSED",
        })
    tasks.sort(key=lambda t: (
        t["priority"], t["statement"]["n"], t["statement_id"]))
    return tasks, examined, refuted


def graph_research_plan(db_path: str, *, order: int | None = None,
                        limit: int = 30, offset: int = 0) -> dict:
    _arguments(order, limit, offset)
    with _open(db_path, existing=True) as db:
        exact = audit_exact_n6(db)  # All underlying mathematical layers rechecked.
        if not exact[1]:
            raise ValueError("exact n6 research is not imported: import first")
        tasks, examined, excluded = _materialized_plan(db, exact)
        fingerprint = _fingerprint(db)
    visible = [task for task in tasks
               if order is None or task["statement"]["n"] == order]
    counts = Counter(t["action"] for t in visible)
    page = visible[offset:offset + limit]
    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "configuration": {"order": order, "limit": limit, "offset": offset},
        "source_fingerprint": fingerprint,
        "source_audit": "ACCEPTED",
        "all_orders_statements_examined": examined,
        "all_orders_refuted_excluded": excluded,
        "eligible_action_count": len(visible),
        "action_counts": dict(sorted(counts.items())),
        "returned_count": len(page),
        "page_offset": offset,
        "next_offset": offset + limit if offset + limit < len(visible) else None,
        "tasks": page,
        "proof_status_upgrades": 0,
        "historical_evidence_overwritten": 0,
        "cross_order_inference": False,
        "novelty": "NOT_ASSESSED",
    }


def write_graph_plan(db_path: str, output: str, *, order: int | None = None,
                     limit: int = 30, offset: int = 0) -> dict:
    report = graph_research_plan(db_path, order=order, limit=limit, offset=offset)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".axiom-graph-plan-", suffix=".tmp", delete=False) as stream:
            name = stream.name
            stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        os.replace(name, path)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)
    return report


def audit_graph_plan(db_path: str, report_path: str) -> dict:
    path = Path(report_path)
    if path.stat().st_size > 5_000_000:
        raise ValueError("graph agenda report exceeds maximum file size")
    report = json.loads(path.read_text(encoding="utf-8"))
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unknown graph agenda schema")
    cfg = report.get("configuration")
    if type(cfg) is not dict or set(cfg) != {"order", "limit", "offset"}:
        raise ValueError("malformed graph agenda parameters")
    expected = graph_research_plan(
        db_path, order=cfg["order"], limit=cfg["limit"], offset=cfg["offset"])
    if stable(report) != stable(expected):
        raise ValueError("graph agenda differs from full mathematical replay")
    return {
        "schema": SCHEMA, "audit": "ACCEPTED",
        "source_fingerprint": expected["source_fingerprint"],
        "eligible_actions": expected["eligible_action_count"],
        "refuted_excluded": expected["all_orders_refuted_excluded"],
        "proof_status_upgrades": 0,
        "cross_order_inference": False,
        "novelty": "NOT_ASSESSED",
    }
