"""AXIOM v0.15 research cycle: formal proofs and independently checked falsification.

A source-replayed v0.14 agenda is the sole task selector. Formal proofs are
delegated to the existing real Lean 4 executor. A distinct, deterministic
experiment lane searches for counterexamples to unresolved order-seven claims,
using the independent reference oracle, not the graph discovery engine.

Historical SQLite findings are never mutated. Each run occupies a unique,
source-content-addressed directory; a completed run is auditable and cannot
be replaced by another run with the same identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .graph_checker import check_graph_witness, reference_properties
from .graph_claims import GraphStatement, digest, holds, stable
from .graph_model import SimpleGraph, edge_positions
from .graph_n6_exact import save_n6
from .graph_research_executor import execute_graph_research, audit_executor_report
from .knowledge_graph_plan import graph_research_plan

SCHEMA = "axiom.graph_research_cycle.v1"
BOUNDED_SCHEMA = "axiom.graph_research_bounded_trial.v1"
SEARCH_ACTIONS = frozenset({
    "EXTEND_BOUNDED_FALSIFICATION", "FALSIFY_WITH_INDEPENDENT_SEARCH"
})


def _validate(proof_quota: int, experiment_quota: int,
              search_budget: int, seed: int, timeout_seconds: int) -> None:
    if type(proof_quota) is not int or not 1 <= proof_quota <= 7:
        raise ValueError("proof_quota must be 1..7")
    if type(experiment_quota) is not int or not 1 <= experiment_quota <= 10:
        raise ValueError("experiment_quota must be 1..10")
    if type(search_budget) is not int or not 1 <= search_budget <= 256:
        raise ValueError("search_budget must be 1..256")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be a uint32 integer")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise ValueError("timeout_seconds must be 1..1200")


def _tasks(db_path: str, order: int) -> tuple[str, list[dict]]:
    page = graph_research_plan(db_path, order=order, limit=100)
    fingerprint = page["source_fingerprint"]
    tasks = list(page["tasks"])
    while page["next_offset"] is not None:
        page = graph_research_plan(db_path, order=order, limit=100,
                                   offset=page["next_offset"])
        if page["source_fingerprint"] != fingerprint:
            raise ValueError("research source changed between agenda pages")
        tasks.extend(page["tasks"])
    if len({t["task_id"] for t in tasks}) != len(tasks):
        raise ValueError("duplicate agenda task identities")
    return fingerprint, tasks


def _mask_stream(task_id: str, order: int, seed: int, budget: int) -> list[int]:
    """Independent finite, nonrepeating samples. This is NOT full exhaustion."""
    space = 1 << len(edge_positions(order))
    selected: list[int] = []
    seen: set[int] = set()
    index = 0
    while len(selected) < budget:
        raw = f"AXIOMv015:{seed}:{task_id}:{index}".encode("utf-8")
        candidate = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % space
        index += 1
        if candidate not in seen:
            selected.append(candidate)
            seen.add(candidate)
    return selected


def bounded_trial(task: dict, source_fingerprint: str, *,
                  search_budget: int = 64, seed: int = 42) -> dict:
    """Search with the independent reference graph oracle and recheck witnesses."""
    if type(task) is not dict or task.get("action") not in SEARCH_ACTIONS:
        raise ValueError("only genuine graph falsification agenda tasks are supported")
    statement = GraphStatement.from_dict(task["statement"])
    if statement.n != 7 or type(task.get("task_id")) is not str:
        raise ValueError("bounded research requires an exact-order-seven task")
    if type(task.get("statement_id")) is not str:
        raise ValueError("missing full agenda statement identity")
    if type(source_fingerprint) is not str or len(source_fingerprint) != 64:
        raise ValueError("missing audited source fingerprint")
    _validate(1, 1, search_budget, seed, 180)
    samples = _mask_stream(task["task_id"], statement.n, seed, search_budget)
    checked, satisfying, witness = [], 0, None
    for mask in samples:
        applicable, valid = holds(statement, reference_properties(statement.n, mask))
        checked.append(mask)
        if applicable:
            satisfying += 1
            if not valid:
                witness = SimpleGraph.from_mask(statement.n, mask).to_dict()
                check_graph_witness(statement.to_dict(), witness)
                break
    return {
        "schema": BOUNDED_SCHEMA,
        "task_id": task["task_id"],
        "statement_id": task["statement_id"],
        "action": task["action"],
        "statement": statement.to_dict(),
        "source_fingerprint": source_fingerprint,
        "seed": seed,
        "budget": search_budget,
        "masks_checked": checked,
        "labelled_graphs_sampled": len(checked),
        "assumption_satisfying": satisfying,
        "status": "REFUTED" if witness is not None else "SURVIVED_BOUNDED_SEARCH",
        "counterexample": witness,
        "independent_witness_audit": witness is not None,
        "exact_scope": "n=7 labelled simple graphs only",
        "exhaustive": False,
        "formal_lean_verification": "NOT_PERFORMED",
        "all_order_generalization": "NOT_PROVED",
        "original_evidence_modified": False,
    }


def audit_bounded_trial(task: dict, source_fingerprint: str, record: dict) -> bool:
    """Independently reproduce every sampled mask and every conclusion."""
    if type(record) is not dict or record.get("schema") != BOUNDED_SCHEMA:
        raise ValueError("unknown bounded-trial evidence")
    expected = bounded_trial(task, source_fingerprint,
                             search_budget=record["budget"], seed=record["seed"])
    if stable(record) != stable(expected):
        raise ValueError("bounded-trial evidence disagrees with independent replay")
    return True


def _ledger(entries: list[dict]) -> list[dict]:
    prior = "0" * 64
    result = []
    for index, entry in enumerate(entries):
        row = {"sequence": index, "previous_sha256": prior, **entry}
        prior = digest(row)
        result.append({**row, "entry_sha256": prior})
    return result


def execute_cycle(db_path: str, output_dir: str, *,
                  project_root: str = ".", proof_quota: int = 3,
                  experiment_quota: int = 2, search_budget: int = 64,
                  seed: int = 42, timeout_seconds: int = 240) -> dict:
    """Execute, audit, preserve or reuse one complete source-bound run."""
    _validate(proof_quota, experiment_quota, search_budget, seed, timeout_seconds)
    fp6, _ = _tasks(db_path, 6)
    fp7, tasks7 = _tasks(db_path, 7)
    if fp6 != fp7:
        raise ValueError("graph research source changed during selection")
    chosen = [t for t in tasks7 if t["action"] in SEARCH_ACTIONS][:experiment_quota]
    run_id = digest([SCHEMA, fp6, proof_quota, experiment_quota,
                     search_budget, seed, timeout_seconds])[:32]
    directory = Path(output_dir) / "runs" / run_id
    if directory.exists():
        result = audit_cycle(db_path, directory)
        return result["report"]
    directory.mkdir(parents=True, exist_ok=False)
    formal = execute_graph_research(
        db_path, str(directory / "formal"), project_root=project_root,
        max_proofs=proof_quota, timeout_seconds=timeout_seconds)
    if formal["source_fingerprint"] != fp6:
        raise ValueError("formal executor source differs from selected agenda")
    records = []
    for task in chosen:
        result = bounded_trial(task, fp7, search_budget=search_budget, seed=seed)
        audit_bounded_trial(task, fp7, result)
        name = digest([task["task_id"], search_budget, seed])[:32] + ".json"
        save_n6(result, str(directory / "bounded" / name))
        records.append({
            "task_id": task["task_id"], "statement_id": task["statement_id"],
            "action": task["action"], "evidence_file": name,
            "record_sha256": digest(result), "status": result["status"],
            "checked": result["labelled_graphs_sampled"],
        })
    entries = []
    for item in formal["results"]:
        path = directory / "formal" / item["evidence_file"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.append({
            "lane": "FORMAL", "path": "formal/" + item["evidence_file"],
            "record_sha256": digest(payload), "status": item["status"],
            "task_id": item["task_id"],
        })
    for item in records:
        entries.append({
            "lane": "BOUNDED", "path": "bounded/" + item["evidence_file"],
            "record_sha256": item["record_sha256"], "status": item["status"],
            "task_id": item["task_id"],
        })
    report = {
        "schema": SCHEMA,
        "run_id": run_id,
        "source_fingerprint": fp6,
        "configuration": {
            "proof_quota": proof_quota, "experiment_quota": experiment_quota,
            "search_budget": search_budget, "seed": seed,
            "timeout_seconds": timeout_seconds,
        },
        "formal": {
            "candidate_count": formal["candidate_count"],
            "attempted": formal["attempted"],
            "formally_verified_recorded": formal["formally_verified"],
            "pending_count": len(formal["pending"]),
            "summary_file": "formal/summary.json",
            "summary_sha256": digest(formal),
        },
        "bounded": records,
        "ledger": _ledger(entries),
        "evidence_lanes": ["FORMAL_LEAN_KERNEL", "BOUNDED_REFERENCE_FALSIFICATION"],
        "original_evidence_modified": False,
        "all_order_generalization": "NOT_PROVED",
        "offline_replay_is_kernel_attestation": False,
    }
    save_n6(report, str(directory / "summary.json"))
    return report


def audit_cycle(db_path: str, run_dir: str | Path) -> dict:
    """Replay agenda + all bounded trials; source-check every formal artifact.

    A saved JSON result alone cannot prove that an external Lean process ran.
    CI logs and genuine reexecution supply that independent attestation.
    """
    directory = Path(run_dir)
    report = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unrecognized research-cycle schema")
    cfg = report.get("configuration")
    if type(cfg) is not dict or set(cfg) != {
        "proof_quota", "experiment_quota", "search_budget", "seed",
        "timeout_seconds"
    }:
        raise ValueError("research-cycle configuration differs from run schema")
    _validate(**cfg)
    fp6, _ = _tasks(db_path, 6)
    fp7, tasks7 = _tasks(db_path, 7)
    if fp6 != fp7 or fp6 != report["source_fingerprint"]:
        raise ValueError("research cycle no longer matches original source")
    run_id = digest([SCHEMA, fp6, cfg["proof_quota"], cfg["experiment_quota"],
                     cfg["search_budget"], cfg["seed"], cfg["timeout_seconds"]])[:32]
    if run_id != report["run_id"] or directory.name != run_id:
        raise ValueError("research cycle run identity changed")
    formal = json.loads(
        (directory / "formal" / "summary.json").read_text(encoding="utf-8"))
    if (digest(formal) != report["formal"]["summary_sha256"] or
            formal["attempted"] != report["formal"]["attempted"] or
            formal["formally_verified"] !=
            report["formal"]["formally_verified_recorded"] or
            formal["candidate_count"] != report["formal"]["candidate_count"] or
            len(formal["pending"]) != report["formal"]["pending_count"]):
        raise ValueError("formal research summary no longer matches ledger")
    audit_executor_report(db_path, str(directory / "formal"))
    chosen = [t for t in tasks7 if t["action"] in SEARCH_ACTIONS][
        :cfg["experiment_quota"]]
    if (type(report.get("bounded")) is not list or
            len(report["bounded"]) != len(chosen)):
        raise ValueError("bounded agenda selection changed")
    entries = []
    for item in formal["results"]:
        path = directory / "formal" / item["evidence_file"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.append({
            "lane": "FORMAL", "path": "formal/" + item["evidence_file"],
            "record_sha256": digest(payload), "status": item["status"],
            "task_id": item["task_id"],
        })
    for task, item in zip(chosen, report["bounded"]):
        name = digest([task["task_id"], cfg["search_budget"], cfg["seed"]])[:32] + ".json"
        if item["task_id"] != task["task_id"] or item["statement_id"] != task["statement_id"]:
            raise ValueError("bounded task identity changed")
        if item["action"] != task["action"] or item["evidence_file"] != name:
            raise ValueError("bounded task selection or artifact path changed")
        record = json.loads((directory / "bounded" / name).read_text(encoding="utf-8"))
        audit_bounded_trial(task, fp7, record)
        if (digest(record) != item["record_sha256"] or
                item["status"] != record["status"] or
                item["checked"] != record["labelled_graphs_sampled"]):
            raise ValueError("bounded proof status or samples have been altered")
        entries.append({
            "lane": "BOUNDED", "path": "bounded/" + name,
            "record_sha256": item["record_sha256"], "status": item["status"],
            "task_id": item["task_id"],
        })
    if (report.get("ledger") != _ledger(entries) or
            report.get("evidence_lanes") != [
                "FORMAL_LEAN_KERNEL", "BOUNDED_REFERENCE_FALSIFICATION"
            ] or report.get("original_evidence_modified") is not False or
            report.get("all_order_generalization") != "NOT_PROVED" or
            report.get("offline_replay_is_kernel_attestation") is not False):
        raise ValueError("research cycle chain or trust boundaries changed")
    return {
        "audit": "SOURCE_REPLAY_ACCEPTED",
        "kernel_reexecution_performed": False,
        "run_id": run_id,
        "formal_attempts": formal["attempted"],
        "bounded_attempts": len(chosen),
        "report": report,
    }
