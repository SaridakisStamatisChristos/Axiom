"""Budgeted, deterministic campaigns with SQLite per-candidate checkpoints."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any
import sympy

from .generation import generate
from .mathematics import Expr, Statement
from .verification import falsify, polynomial_proof

STATUSES = frozenset({"GENERATED", "UNDER_TEST", "EXPERIMENTALLY_SUPPORTED", "REFUTED",
                      "PROOF_CANDIDATE", "PROVED_IN_SUPPORTED_FRAGMENT", "FORMALLY_VERIFIED",
                      "UNRESOLVED", "INVALID"})


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def heuristic_rank(statement: Statement) -> float:
    """Explicit illustrative complexity heuristic, NOT a novelty metric."""
    def nodes(e: Expr) -> int:
        return 1 + sum(nodes(a) for a in e.args)
    return round(100.0 / (1 + nodes(statement.lhs) + nodes(statement.rhs) + len(statement.variables)), 4)


def open_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY, configuration TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
            duplicates INTEGER NOT NULL DEFAULT 0, created_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS findings (
            campaign_id TEXT NOT NULL REFERENCES campaigns(id), candidate_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL, template TEXT NOT NULL, canonical_key TEXT NOT NULL,
            statement TEXT NOT NULL, status TEXT NOT NULL, originality TEXT NOT NULL,
            ranking_score REAL NOT NULL, status_history TEXT NOT NULL,
            search_evidence TEXT NOT NULL, proof_evidence TEXT,
            PRIMARY KEY (campaign_id, candidate_id), UNIQUE (campaign_id, canonical_key));
    """)
    return conn


def run_campaign(db_path: str, seed: int = 42, candidates: int = 100, domain: str = "polynomial",
                 lower: int = -8, upper: int = 8, max_evals: int = 300,
                 step_limit: int | None = None, report_path: str | None = None) -> dict[str, Any]:
    if type(seed) is not int or lower > upper or max_evals < 1 or max_evals > 1_000_000:
        raise ValueError("invalid campaign configuration")
    if step_limit is not None and step_limit < 0:
        raise ValueError("step_limit must be nonnegative")
    config = {"campaign": "integer_polynomial_discovery", "seed": seed, "candidates": candidates,
              "domain": domain, "lower": lower, "upper": upper, "max_evals": max_evals}
    generated = generate(seed, candidates, domain)
    campaign_id = hashlib.sha256(stable_json(config).encode()).hexdigest()[:24]
    started = time.perf_counter()
    with open_db(db_path) as db:
        db.execute("INSERT OR IGNORE INTO campaigns (id,configuration,cursor,duplicates,created_utc) VALUES (?,?,0,0,?)",
                   (campaign_id, stable_json(config), datetime.now(timezone.utc).isoformat()))
        db.commit()
        row = db.execute("SELECT configuration,cursor,duplicates FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row[0] != stable_json(config):
            raise RuntimeError("campaign identity collision")
        cursor, duplicates = int(row[1]), int(row[2])
        start_cursor = cursor
        seen = {r[0] for r in db.execute("SELECT canonical_key FROM findings WHERE campaign_id=?", (campaign_id,))}
        end = min(len(generated), cursor + step_limit) if step_limit is not None else len(generated)
        for ordinal in range(cursor, end):
            template, statement = generated[ordinal]
            key = statement.canonical_key()
            if key in seen:
                duplicates += 1
                with db:
                    db.execute("UPDATE campaigns SET cursor=?,duplicates=? WHERE id=?", (ordinal + 1, duplicates, campaign_id))
                continue
            search = falsify(statement, lower, upper, max_evals, seed + ordinal)
            proof = None
            if search["counterexample"] is not None:
                status = "REFUTED"
            elif statement.relation == "==":
                proof = polynomial_proof(statement)
                status = "PROVED_IN_SUPPORTED_FRAGMENT" if proof else "UNRESOLVED"
            else:
                status = "EXPERIMENTALLY_SUPPORTED"
            if status not in STATUSES:
                raise AssertionError("unrecognized evidence status")
            candidate_id = hashlib.sha256(key.encode()).hexdigest()
            transitions = ["GENERATED", "UNDER_TEST"]
            if proof:
                transitions.append("PROOF_CANDIDATE")
            transitions.append(status)
            with db:
                db.execute("""INSERT INTO findings
                  (campaign_id,candidate_id,ordinal,template,canonical_key,statement,status,originality,
                   ranking_score,status_history,search_evidence,proof_evidence)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (campaign_id, candidate_id, ordinal, template, key, stable_json(statement.to_dict()),
                   status, "NOT_ASSESSED", heuristic_rank(statement), stable_json(transitions),
                   stable_json(search), stable_json(proof) if proof else None))
                db.execute("UPDATE campaigns SET cursor=?,duplicates=? WHERE id=?", (ordinal + 1, duplicates, campaign_id))
            seen.add(key)
        cursor = db.execute("SELECT cursor FROM campaigns WHERE id=?", (campaign_id,)).fetchone()[0]
        findings = [dict(candidate_id=r[0], ordinal=r[1], template=r[2], statement=json.loads(r[3]),
                         status=r[4], originality=r[5], ranking_score=r[6], history=json.loads(r[7]),
                         search=json.loads(r[8]), proof=json.loads(r[9]) if r[9] else None)
                    for r in db.execute("""SELECT candidate_id,ordinal,template,statement,status,originality,
                                             ranking_score,status_history,search_evidence,proof_evidence FROM findings
                                             WHERE campaign_id=? ORDER BY ordinal""", (campaign_id,))]
    counts = {s: sum(f["status"] == s for f in findings) for s in sorted(STATUSES)}
    duration = time.perf_counter() - started
    report = {"schema": "axiom.v0.1.report", "campaign_id": campaign_id, "configuration": config,
              "progress": {"cursor": cursor, "candidate_budget": candidates, "complete": cursor == candidates,
                           "duplicates_rejected": duplicates, "unique_candidates": len(findings)},
              "counts": counts, "findings": findings,
              "measurement": {"execution_seconds": round(duration, 6),
                              "candidate_positions_per_second": round((cursor - start_cursor) / duration, 2) if duration else None,
                              "peak_process_rss_kb_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if platform.system() == "Linux" else None},
              "environment": {"python": platform.python_version(), "sympy": sympy.__version__,
                              "platform": platform.platform(), "verification": "sparse_ZZ_and_SymPy_ZZ",
                              "lean": "not_executed", "z3": "not_executed"},
              "originality_policy": "NOT_ASSESSED: no literature search performed"}
    if report_path:
        target = Path(report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, target)
    return report
