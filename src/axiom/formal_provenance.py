"""AXIOM v0.8 — source-bound Lean proof lineage, without forged attestation.

Imports full historical algebraic / number-theory Lean result records into the
already-audited v0.7 federation. Cross-layer links are rebuilt from immutable
source inputs during every audit. An offline validated record is NEVER proof
that an external Lean process ran. Historic CI executions remain external.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sqlite3

from .graph_claims import stable, digest
from .knowledge_graph import _open
from .knowledge_federation import _audit as audit_federation
from .knowledge_federation import _sources, _source_id, _node_id, _validate

SCHEMA = "axiom.lean_provenance.v1"
MAX_RECORDS = 256
MAX_INPUT_BYTES = 8_000_000
DOMAINS = ("algebra", "number_theory")
OFFLINE_STATUS = "SOURCE_BOUND_OFFLINE_ONLY"


def _tables(db: sqlite3.Connection) -> None:
    # Individual DDL statements are safe inside an existing transaction;
    # sqlite3.executescript() would force an implicit COMMIT.
    for ddl in (
        """CREATE TABLE IF NOT EXISTS formal_batches (
            source_id TEXT PRIMARY KEY REFERENCES federation_nodes(node_id),
            kind TEXT NOT NULL, batch_digest TEXT NOT NULL,
            items_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS formal_links (
            record_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES federation_nodes(node_id),
            finding_id TEXT NOT NULL REFERENCES federation_nodes(node_id),
            statement_id TEXT NOT NULL REFERENCES federation_nodes(node_id),
            local_proof_id TEXT NOT NULL REFERENCES federation_nodes(node_id),
            source_sha256 TEXT NOT NULL,
            record_digest TEXT NOT NULL,
            evidence_json TEXT NOT NULL)""",
        """CREATE INDEX IF NOT EXISTS formal_links_source
             ON formal_links(source_id)""",
    ):
        db.execute(ddl)

def _read_ndjson(path: str) -> list[dict]:
    file = Path(path)
    if file.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("formal NDJSON exceeds byte limit")
    lines = file.read_text(encoding="utf-8").splitlines()
    if not lines or len(lines) > MAX_RECORDS or any(not line.strip() for line in lines):
        raise ValueError("formal NDJSON must contain 1..256 nonempty records")
    result = [json.loads(line) for line in lines]
    if any(type(item) is not dict for item in result):
        raise ValueError("formal NDJSON contains invalid records")
    return result


def _source_report(db: sqlite3.Connection, sid: str) -> dict:
    if not sid.startswith("source:"):
        raise ValueError("invalid formal source reference")
    row = db.execute(
        "SELECT report_digest,report_json FROM federation_sources "
        "WHERE source_id=?", (sid.removeprefix("source:"),)).fetchone()
    if row is None:
        raise ValueError("formal records require exact originating campaign")
    report = json.loads(row[1])
    if (stable(report) != row[1] or digest(report) != row[0]
            or "source:" + _source_id(report) != sid):
        raise ValueError("corrupted federated source")
    _validate(report)
    return report

def _batch(kind: str, source_id: str, entries: list[dict]) -> dict:
    if kind not in DOMAINS or not 1 <= len(entries) <= MAX_RECORDS:
        raise ValueError("unsupported or empty formal evidence batch")
    return {"schema": SCHEMA, "kind": kind, "source_id": source_id, "items": entries}


def _materialize(batch: dict, report: dict, nodes: dict) -> dict[str, tuple]:
    """Source-bind EVERY record to the exact original statement and certificate."""
    kind, sid = batch["kind"], batch["source_id"]
    if (type(batch) is not dict or set(batch) != {"schema", "kind", "source_id", "items"}
            or batch["schema"] != SCHEMA or kind not in DOMAINS
            or sid != "source:" + _source_id(report)
            or type(batch["items"]) is not list
            or not 1 <= len(batch["items"]) <= MAX_RECORDS):
        raise ValueError("formal batch source/schema mismatch")
    if (kind == "algebra") != (report["schema"] == "axiom.v0.2.report"):
        raise ValueError("formal evidence domain mismatch")
    if (kind == "number_theory") != (
            report["schema"] == "axiom.number_theory.report.v1"):
        raise ValueError("formal evidence domain mismatch")
    from .lean_backend import verify_record_integrity
    from .number_theory_lean import verify_nt_record_integrity
    by_candidate = {f["candidate_id"]: f for f in report["findings"]
                    if f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT"}
    seen: set[str] = set()
    result: dict[str, tuple] = {}
    for item in batch["items"]:
        if type(item) is not dict or set(item) != {"metadata", "record"}:
            raise ValueError("malformed formal evidence item")
        meta, record = item["metadata"], item["record"]
        if type(record) is not dict:
            raise ValueError("malformed full Lean record")
        if kind == "algebra":
            if meta is not None:
                raise ValueError("algebra records cannot have number-theory index")
            candidate = record.get("origin_candidate_id")
            if (record.get("origin_campaign_id") != report["campaign_id"] or
                    record.get("origin_candidate_status") != "PROVED_IN_SUPPORTED_FRAGMENT"):
                raise ValueError("algebra record has invalid source binding")
            verify_record_integrity(record)
        else:
            if type(meta) is not dict:
                raise ValueError("number-theory record requires index metadata")
            candidate = meta.get("candidate_id")
            expected_path = (
                "research/lean_verified/number_theory/"
                + str(candidate)[:24] + ".json")
            if (meta.get("campaign_id") != report["campaign_id"] or
                    meta.get("evidence_path") != expected_path):
                raise ValueError("number-theory index campaign/path mismatch")
            verify_nt_record_integrity(record)
        if type(candidate) is not str or candidate not in by_candidate or candidate in seen:
            raise ValueError("duplicate or unknown verified candidate")
        seen.add(candidate)
        origin = by_candidate[candidate]
        if (record.get("statement") != origin["statement"] or
                record.get("certificate") != origin["proof"]["certificate"] or
                record.get("accepted") is not True or
                record.get("status") != "FORMALLY_VERIFIED"):
            raise ValueError("formal record is not bound to exact original proof")
        if kind == "number_theory":
            expected_index = {
                "campaign_id": report["campaign_id"],
                "candidate_id": candidate,
                "ordinal": origin["ordinal"],
                "template": origin["template"],
                "status": record["status"],
                "source_sha256": record["source_sha256"],
                "statement_sha256": record["statement_sha256"],
                "theorem": record["theorem"],
                "axioms": record["axioms"],
                "lean_version": record["lean_version"],
                "mathlib_revision": record["mathlib_revision"],
            }
            if any(meta.get(k) != v for k, v in expected_index.items()):
                raise ValueError("number-theory index and full Lean record disagree")
        subject = origin["statement"]
        finding_id = _node_id("finding", [_source_id(report), candidate])
        statement_id = _node_id("statement", [kind, subject])
        local_proof_id = _node_id("local_proof", [
            kind, subject, origin["proof"]["certificate"]])
        if (finding_id not in nodes or statement_id not in nodes or
                local_proof_id not in nodes):
            raise ValueError("orphan formal evidence relationship")
        record_id = _node_id("formal_record", [kind, sid, candidate, record])
        evidence = {
            "kind": kind, "campaign_id": report["campaign_id"],
            "candidate_id": candidate, "theorem": record["theorem"],
            "source_sha256": record["source_sha256"],
            "statement_sha256": record["statement_sha256"],
            "lean_version": record["lean_version"],
            "mathlib_revision": record["mathlib_revision"],
            "declared_kernel_status": record["status"],
            "offline_record_integrity": "ACCEPTED",
            "external_execution_attestation": "NOT_ESTABLISHED_BY_OFFLINE_AUDIT",
            "status": OFFLINE_STATUS,
            "originality": "NOT_ASSESSED",
        }
        result[record_id] = (sid, finding_id, statement_id, local_proof_id,
                             record["source_sha256"], digest(record), stable(evidence))
    return result


def _expected(db: sqlite3.Connection, nodes: dict) -> dict[str, tuple]:
    result = {}
    for sid, kind, batch_digest, payload in db.execute(
            "SELECT source_id,kind,batch_digest,items_json FROM formal_batches"):
        batch = json.loads(payload)
        if (stable(batch) != payload or digest(batch) != batch_digest or
                batch.get("source_id") != sid or batch.get("kind") != kind):
            raise ValueError("tampered formal input batch")
        report = _source_report(db, sid)
        new = _materialize(batch, report, nodes)
        for record_id, row in new.items():
            if record_id in result:
                raise ValueError("duplicate formal record ID")
            result[record_id] = row
    return result


def _audit(db: sqlite3.Connection) -> dict[str, tuple]:
    nodes, _ = audit_federation(db)  # Recheck entire v0.5–v0.7 evidence chain.
    _tables(db)
    expected = _expected(db, nodes)
    observed = {rid: (sid, fid, stid, pid, shash, rdigest, data)
                for rid, sid, fid, stid, pid, shash, rdigest, data in db.execute(
                    "SELECT record_id,source_id,finding_id,statement_id,"
                    "local_proof_id,source_sha256,record_digest,evidence_json "
                    "FROM formal_links")}
    if expected != observed:
        raise ValueError("formal lineage differs from audited source proof records")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("formal evidence contains orphan foreign keys")
    return expected


def formal_summary(db_path: str) -> dict:
    with _open(db_path, existing=True) as db:
        verified = _audit(db)
        batches = list(db.execute("SELECT source_id,kind FROM formal_batches"))
    return {
        "schema": SCHEMA, "audit": "ACCEPTED",
        "historical_full_records_source_bound": len(verified),
        "records_by_domain": dict(sorted(Counter(
            json.loads(row[-1])["kind"] for row in verified.values()).items())),
        "batches": len(batches),
        "external_lean_execution_attestation":
            "NOT_ESTABLISHED_BY_OFFLINE_AUDIT",
        "knowledge_graph_status_upgrades": 0,
        "novelty": "NOT_ASSESSED",
    }


def import_formal(db_path: str, *, algebra_ndjson: str | None = None,
                  number_index: str | None = None,
                  number_records_dir: str | None = None) -> dict:
    if (algebra_ndjson is None and number_index is None or
            (number_index is None) != (number_records_dir is None)):
        raise ValueError("provide algebra NDJSON or number-theory index and full record directory")
    incoming = []
    if algebra_ndjson is not None:
        entries = [{"metadata": None, "record": r} for r in
                   _read_ndjson(algebra_ndjson)]
        if not entries:
            raise ValueError("empty algebra proof records")
        incoming.append(("algebra", entries))
    if number_index is not None:
        metas = _read_ndjson(number_index)
        folder = Path(number_records_dir).resolve()
        if not folder.is_dir():
            raise ValueError("number-theory full record directory unavailable")
        seen_files: set[str] = set()
        entries = []
        for meta in metas:
            cid = meta.get("candidate_id")
            if not isinstance(cid, str) or len(cid) != 64 or not all(
                    c in "0123456789abcdef" for c in cid):
                raise ValueError("malformed number-theory candidate ID")
            filename = cid[:24] + ".json"
            if filename in seen_files:
                raise ValueError("duplicate number-theory proof record file")
            seen_files.add(filename)
            file = folder / filename
            if not file.is_file() or file.is_symlink() or file.stat().st_size > 65_536:
                raise ValueError("missing or unsafe full number-theory record")
            entries.append({"metadata": meta, "record": json.loads(
                file.read_text(encoding="utf-8"))})
        incoming.append(("number_theory", entries))
    with _open(db_path, existing=True) as db:
        _tables(db)
        # No writes before verifying the current materialized evidence and
        # every incoming full record.
        _audit(db)
        reports = {_source_id(r): r for r in _sources(db)}
        batches = []
        for domain, entries in incoming:
            if domain == "algebra":
                campaign_ids = {entry["record"].get("origin_campaign_id")
                                for entry in entries}
            else:
                campaign_ids = {entry["metadata"].get("campaign_id")
                                for entry in entries}
            if len(campaign_ids) != 1:
                raise ValueError("formal records span multiple campaigns")
            campaign_id = next(iter(campaign_ids))
            if not isinstance(campaign_id, str):
                raise ValueError("invalid formal source campaign identity")
            source_ref = domain + ":" + campaign_id
            report = reports.get(source_ref)
            if report is None:
                raise ValueError("exact formal source campaign not federated")
            sid = "source:" + source_ref
            batch = _batch(domain, sid, entries)
            nodes, _ = audit_federation(db)
            _materialize(batch, report, nodes)
            prior = db.execute("SELECT items_json FROM formal_batches "
                               "WHERE source_id=?", (sid,)).fetchone()
            if prior is not None and prior[0] != stable(batch):
                raise ValueError("conflicting immutable Lean batch")
            batches.append(batch)
        with db:
            for batch in batches:
                db.execute("INSERT OR IGNORE INTO formal_batches VALUES (?,?,?,?)",
                           (batch["source_id"], batch["kind"],
                            digest(batch), stable(batch)))
            # All original federation material was fully audited before this
            # transaction. Its nodes do not change during a formal import.
            expected = _expected(db, nodes)
            db.execute("DELETE FROM formal_links")
            db.executemany(
                "INSERT INTO formal_links VALUES (?,?,?,?,?,?,?,?)",
                [(key, *expected[key]) for key in sorted(expected)])
    return formal_summary(db_path)


def formal_query(db_path: str, *, domain: str | None = None,
                 limit: int = 20) -> list[dict]:
    if domain is not None and domain not in DOMAINS:
        raise ValueError("formal provenance domain must be algebra or number_theory")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("invalid formal query limit")
    with _open(db_path, existing=True) as db:
        entries = _audit(db)
    findings = [json.loads(row[-1]) for _, row in sorted(entries.items())
                if domain is None or json.loads(row[-1])["kind"] == domain]
    return findings[:limit]
