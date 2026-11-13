"""AXIOM v0.10: deterministic, evidence-gated mathematical research agenda.

A task is a proposal for the NEXT falsification or verification action, not a
mathematical discovery. Every input is independently replayed through the
original v0.6 graph, v0.7 federation, and v0.8 formal lineage auditors.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import tempfile

from .graph_claims import digest, stable
from .knowledge_graph import _open
from .formal_provenance import _audit as _audit_formal

SCHEMA = "axiom.research_agenda.v1"
POLICY = "refutation_first_exact_scope_no_offline_formal_promotion_v1"
DOMAINS = frozenset({"graph", "algebra", "number_theory", "recurrence"})
ACTIONS = frozenset({
    "FALSIFY_WITH_INDEPENDENT_SEARCH",
    "FORMALIZE_SUPPORTED_FRAGMENT",
    "REEXECUTE_PINNED_LEAN",
    "FORMALIZE_EXACT_SCOPE",
})


def _arguments(domain: str | None, limit: int, offset: int) -> None:
    if domain is not None and domain not in DOMAINS:
        raise ValueError("unsupported research domain")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("agenda limit must be 1..100")
    if type(offset) is not int or not 0 <= offset <= 100_000:
        raise ValueError("agenda offset must be 0..100000")


def _source_fingerprint(db) -> str:
    # The three sets are integrity checked before a fingerprint can be used.
    reports = sorted(db.execute(
        "SELECT campaign_id,report_digest FROM kg_reports").fetchall())
    federation = sorted(db.execute(
        "SELECT source_id,report_digest FROM federation_sources").fetchall())
    formal = sorted(db.execute(
        "SELECT source_id,batch_digest FROM formal_batches").fetchall())
    return digest({"graph": reports, "federation": federation, "formal": formal})


def research_agenda(db_path: str, *, domain: str | None = None,
                    limit: int = 30, offset: int = 0) -> dict:
    """Plan auditable action proposals from already established evidence.

    REFUTED statements are excluded; tests never imply proof. A preserved
    Lean JSON record creates a *reexecution* task, not a FORMALLY_VERIFIED
    database status. Graph proof scopes never expand across graph orders.
    """
    _arguments(domain, limit, offset)
    with _open(db_path, existing=True) as db:
        formal = _audit_formal(db)  # Already independently replays v0.6 and v0.7.
        nodes = {key: (kind, payload) for key, kind, payload in db.execute(
            "SELECT node_id,kind,payload FROM federation_nodes")}
        edges = {key: (src, rel, dst, attrs)
                 for key, src, rel, dst, attrs in db.execute(
                     "SELECT edge_id,source,relation,target,attrs FROM federation_edges")}
        fingerprint = _source_fingerprint(db)

    investigations = defaultdict(set)
    proof_links = defaultdict(set)
    for src, rel, dst, _ in edges.values():
        if rel == "INVESTIGATES":
            investigations[dst].add(src)
        if rel == "LOCALLY_CERTIFIED_BY":
            proof_links[src].add(dst)

    offline_records = defaultdict(set)
    for record_id, record in formal.items():
        evidence = json.loads(record[-1])
        if (evidence.get("status") != "SOURCE_BOUND_OFFLINE_ONLY" or
                evidence.get("external_execution_attestation") !=
                    "NOT_ESTABLISHED_BY_OFFLINE_AUDIT"):
            raise ValueError("formal record incorrectly claims external attestation")
        offline_records[record[2]].add(record_id)

    tasks = []
    excluded_refuted = 0
    examined = 0
    for statement_id in sorted(nodes):
        kind, payload = nodes[statement_id]
        if kind != "statement":
            continue
        data = json.loads(payload)
        area = data["domain"]
        if domain is not None and area != domain:
            continue
        examined += 1
        findings = [json.loads(nodes[fid][1])
                    for fid in sorted(investigations.get(statement_id, []))]
        if not findings:
            raise ValueError("statement without originating research findings")
        statuses = sorted({finding["status"] for finding in findings})
        if "REFUTED" in statuses:
            excluded_refuted += 1
            continue
        proofs = sorted({pid for fid in investigations[statement_id]
                         for pid in proof_links.get(fid, set())})
        formal_ids = sorted(offline_records.get(statement_id, set()))
        if "PROVED_IN_SUPPORTED_FRAGMENT" in statuses:
            if not proofs:
                raise ValueError("local proof status lacks source-bound certificate")
            if formal_ids:
                if area not in {"algebra", "number_theory"}:
                    raise ValueError("unsupported domain has Lean offline records")
                action, priority = "REEXECUTE_PINNED_LEAN", 3
                rationale = ("Recheck historical source-bound formal source in "
                             "the pinned Lean kernel; offline records do not "
                             "attest execution by themselves")
            elif area in {"algebra", "number_theory"}:
                action, priority = "FORMALIZE_SUPPORTED_FRAGMENT", 2
                rationale = ("Create and kernel-check a proof for this exact "
                             "supported integer-polynomial statement, without "
                             "extending its claimed theorem fragment")
            else:
                action, priority = "FORMALIZE_EXACT_SCOPE", 4
                rationale = ("Develop a formal checker for this exact fixed-order "
                             "graph or modular-recurrence certificate; do not "
                             "generalize the statement")
        elif set(statuses) <= {"EXPERIMENTALLY_SUPPORTED", "UNRESOLVED"}:
            if proofs or formal_ids:
                raise ValueError("unproved statement unexpectedly has proof evidence")
            action, priority = "FALSIFY_WITH_INDEPENDENT_SEARCH", 1
            rationale = ("Seek a minimized independently verified counterexample "
                         "using a new disclosed search budget; survival is not proof")
        else:
            raise ValueError("unrecognized source evidence status")
        if action not in ACTIONS:
            raise ValueError("unknown research agenda action")
        tasks.append({
            "task_id": "agenda:" + digest([SCHEMA, statement_id, action]),
            "priority": priority,
            "action": action,
            "domain": area,
            "statement_id": statement_id,
            "statement": data["statement"],
            "evidence_statuses": statuses,
            "originating_sources": sorted({
                finding["source_id"] for finding in findings}),
            "originating_findings": sorted(investigations[statement_id]),
            "local_proof_ids": proofs,
            "source_bound_offline_lean_record_ids": formal_ids,
            "rationale": rationale,
            "claims_a_new_theorem": False,
            "cross_scope_entailment": False,
            "mathematical_novelty": "NOT_ASSESSED",
        })

    tasks.sort(key=lambda t: (t["priority"], t["domain"], t["statement_id"]))
    counts = Counter(t["action"] for t in tasks)
    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "configuration": {"domain": domain, "limit": limit, "offset": offset},
        "source_fingerprint": fingerprint,
        "source_audit": "ACCEPTED",
        "statements_examined": examined,
        "refuted_statements_excluded": excluded_refuted,
        "eligible_action_count": len(tasks),
        "action_counts": dict(sorted(counts.items())),
        "returned_count": len(tasks[offset:offset + limit]),
        "page_offset": offset,
        "next_offset": (offset + limit if offset + limit < len(tasks) else None),
        "tasks": tasks[offset:offset + limit],
        "proof_status_upgrades": 0,
        "historical_lean_execution_attestation":
            "NOT_ESTABLISHED_BY_OFFLINE_AUDIT",
        "novelty": "NOT_ASSESSED",
    }


def write_agenda(db_path: str, output: str, *, domain: str | None = None,
                 limit: int = 30, offset: int = 0) -> dict:
    report = research_agenda(db_path, domain=domain, limit=limit,
                             offset=offset)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".axiom-agenda-", suffix=".tmp", delete=False) as out:
            tmp_name = out.name
            out.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
        os.replace(tmp_name, path)
    finally:
        if tmp_name is not None and os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return report


def audit_agenda(db_path: str, report_path: str) -> dict:
    path = Path(report_path)
    if path.stat().st_size > 5_000_000:
        raise ValueError("agenda file is too large")
    report = json.loads(path.read_text(encoding="utf-8"))
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unrecognized agenda schema")
    config = report.get("configuration")
    if type(config) is not dict or set(config) != {"domain", "limit", "offset"}:
        raise ValueError("malformed agenda configuration")
    expected = research_agenda(db_path, domain=config["domain"],
                               limit=config["limit"], offset=config["offset"])
    if stable(report) != stable(expected):
        raise ValueError("agenda differs from independently replayed evidence")
    return {
        "schema": SCHEMA,
        "audit": "ACCEPTED",
        "source_fingerprint": expected["source_fingerprint"],
        "eligible_actions": expected["eligible_action_count"],
        "reported_actions": expected["returned_count"],
        "refuted_excluded": expected["refuted_statements_excluded"],
        "proof_status_upgrades": 0,
        "novelty": "NOT_ASSESSED",
    }
