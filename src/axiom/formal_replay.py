"""Fresh Lean execution evidence for audited historical proof records."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

from .formal_provenance import _audit
from .graph_claims import digest
from .knowledge_graph import _open
from .lean_backend import LEAN_VERSION, TOOLCHAIN, _dependency_manifest, verify_with_lean
from .number_theory_lean import verify_nt_with_lean

SCHEMA = "axiom.lean_execution_replay.v1"
# These are the resolved pins shared by both historical campaigns.
MATHLIB_COMMIT = "56a005855ea17e0b0958f73ec801ae140b0a1679"
MANIFEST_SHA256 = "a19b8a2e5b1293ae2beadbc3ae84812adcdae07162ab07d2232d023da83841cd"


def replay_formal(db_path: str, *, project_root: str | Path,
                  timeout_seconds: int = 180,
                  statement_ids: set[str] | None = None) -> dict:
    """Replay audited, regenerated source and return evidence for this invocation."""
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise ValueError("invalid Lean timeout")
    with _open(db_path, existing=True) as db:
        with db:
            db.execute("BEGIN")
            links = _audit(db)
            originals = {}
            for (payload,) in db.execute("SELECT items_json FROM formal_batches"):
                for entry in json.loads(payload)["items"]:
                    record = entry["record"]
                    originals[digest(record)] = record
    selected = [(key, row) for key, row in sorted(links.items())
                if statement_ids is None or row[2] in statement_ids]
    if not selected and statement_ids is None:
        raise ValueError("no audited formal records to replay")
    root = Path(project_root).resolve()
    if selected:
        try:
            dependencies = _dependency_manifest(root)
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Mathlib revision check timed out") from exc
        if dependencies != {"mathlib_revision": MATHLIB_COMMIT,
                            "manifest_sha256": MANIFEST_SHA256}:
            raise ValueError("Lean replay requires the pinned historical Lake manifest and Mathlib")

    def replay(entry: tuple) -> dict:
        record_id, (source_id, finding_id, statement_id, proof_id,
                    source_sha, record_digest, evidence_json) = entry
        provenance = json.loads(evidence_json)
        original = originals[record_digest]
        check = verify_with_lean if provenance["kind"] == "algebra" else verify_nt_with_lean
        outcome = check(original["statement"], original["certificate"],
                        project_root=root, timeout_seconds=timeout_seconds)
        if (outcome["accepted"] is not True or outcome["status"] != "FORMALLY_VERIFIED"
                or outcome["checker_exit_code"] != 0):
            raise ValueError(f"Lean replay failed for {record_id} ({outcome['status']})")
        for field in ("theorem", "source", "source_sha256", "statement_sha256",
                      "lean_version", "mathlib_revision", "dependency_manifest_sha256"):
            if outcome[field] != original[field]:
                raise ValueError(f"Lean replay changed {field} for {record_id}")
        if (outcome["mathlib_revision"] != MATHLIB_COMMIT
                or outcome["dependency_manifest_sha256"] != MANIFEST_SHA256
                or outcome["lean_version"] != LEAN_VERSION
                or sorted(outcome["axioms"]) != sorted(original["axioms"])):
            raise ValueError(f"Lean replay pins or axioms differ for {record_id}")
        return {
            "status": "LEAN_KERNEL_REPLAY_VERIFIED",
            "domain": provenance["kind"],
            "campaign_id": provenance["campaign_id"],
            "candidate_id": provenance["candidate_id"],
            "formal_record_id": record_id,
            "formal_record_digest": record_digest,
            "source_id": source_id,
            "finding_id": finding_id,
            "statement_id": statement_id,
            "local_proof_id": proof_id,
            "statement_sha256": outcome["statement_sha256"],
            "source_sha256": source_sha,
            "theorem": outcome["theorem"],
            "axioms": sorted(outcome["axioms"]),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(replay, selected))
    return {
        "schema": SCHEMA,
        "evidence_origin": ("LIVE_LEAN_KERNEL_REPLAY" if records else
                            "NO_ELIGIBLE_FORMAL_RECORDS"),
        "toolchain": TOOLCHAIN,
        "lean_version": LEAN_VERSION,
        "mathlib_revision": MATHLIB_COMMIT,
        "dependency_manifest_sha256": MANIFEST_SHA256,
        "records": records,
    }


def add_replayed_evidence(db_path: str, statements: list[dict], *,
                          project_root: str | Path, timeout_seconds: int) -> dict:
    """Add evidence only for the selected statements, leaving findings intact."""
    report = replay_formal(db_path, project_root=project_root,
                           timeout_seconds=timeout_seconds,
                           statement_ids={row["statement_id"] for row in statements})
    evidence: dict[str, list[dict]] = {}
    for record in report.pop("records"):
        evidence.setdefault(record["statement_id"], []).append(record)
    return {"lean_replay": report, "statements": [
        {**row, "verified_evidence": evidence.get(row["statement_id"], [])}
        for row in statements
    ]}
