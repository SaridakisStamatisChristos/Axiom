"""AXIOM v0.15: actual Lean-kernel graph proofs, exact n=6 scope only.

Trusted translation is deliberately closed: no raw user Lean source is accepted.
The source-checked n=6 Python certificate is a prerequisite, never a substitute.
Only three structurally formalized templates are supported in this first stage.
The Lean statement counts the same fifteen labelled edges as the n=6 checker.
All results live in a separate evidence ledger; historical findings are immutable.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from itertools import combinations
from typing import Any

from .graph_claims import GraphStatement, digest, stable
from .graph_model import edge_positions
from .graph_n6_exact import check_n6_certificate, N, LABELED_GRAPHS
from .lean_backend import (
    _axiom_report, _dependency_manifest, _toolchain_matches,
    ALLOWED_AXIOMS, LEAN_VERSION, TOOLCHAIN, MATHLIB_REV,
    MAX_LOG_BYTES, VERSION_RE, LeanBackendError,
)

SCHEMA = "axiom.graph_n6.lean_evidence.v1"
SOURCE_SCHEMA = "axiom.graph_n6.lean_source.v1"
SUPPORTED = ("handshake", "degree_bound", "triangle_upper_bound")
EDGES = tuple(edge_positions(N))
TRIANGLES = tuple(combinations(range(N), 3))
assert len(EDGES) == 15 and len(TRIANGLES) == 20


def _sum(parts: list[str]) -> str:
    return " + ".join(parts) if parts else "0"


def _source_for_template(template: str, theorem: str) -> str:
    if template not in SUPPORTED:
        raise LeanBackendError("graph template not yet formally supported")
    out = [
        "-- AXIOM closed, exact-six-vertex graph formalization.",
        "-- Vertex set is {0,1,2,3,4,5}; each of the 15 edges is one mask bit.",
        "-- The theorem is about this graph order only, not arbitrary graph orders.",
        "import Mathlib", "",
        "namespace AxiomGraphN6", "",
        "private def bit (mask i : Nat) : Nat :=",
        "  if Nat.testBit mask i = true then 1 else 0", "",
        "private theorem bit_le_one (mask i : Nat) : bit mask i ≤ 1 := by",
        "  unfold bit",
        "  split_ifs <;> omega", "",
    ]
    out.extend([
        "private def edgeCount (mask : Nat) : Nat :=",
        "  " + _sum([f"bit mask {i}" for i in range(15)]), "",
    ])
    for v in range(6):
        indices = [i for i, (a, b) in enumerate(EDGES) if a == v or b == v]
        out.extend([
            f"private def degree{v} (mask : Nat) : Nat :=",
            "  " + _sum([f"bit mask {i}" for i in indices]), "",
        ])
    out.extend([
        "private def degreeSum (mask : Nat) : Nat :=",
        "  " + _sum([f"degree{i} mask" for i in range(6)]), "",
        "private def maximumDegree (mask : Nat) : Nat :=",
    ])
    nested = "degree5 mask"
    for v in reversed(range(5)):
        nested = f"max (degree{v} mask) ({nested})"
    out.extend(["  " + nested, ""])
    if template == "triangle_upper_bound":
        edge_index = {pair: i for i, pair in enumerate(EDGES)}
        for i, (a, b, c) in enumerate(TRIANGLES):
            bits = (edge_index[(a, b)], edge_index[(a, c)], edge_index[(b, c)])
            premise = " ∧ ".join(f"bit mask {j} = 1" for j in bits)
            out.extend([
                f"private def tri{i} (mask : Nat) : Nat :=",
                f"  if {premise} then 1 else 0", "",
                f"private theorem tri{i}_le_one (mask : Nat) : tri{i} mask ≤ 1 := by",
                f"  unfold tri{i}",
                "  split_ifs <;> omega", "",
            ])
        out.extend([
            "private def triangleCount (mask : Nat) : Nat :=",
            "  " + _sum([f"tri{i} mask" for i in range(20)]), "",
        ])
    if template == "handshake":
        out.extend([
            f"theorem {theorem} (mask : Nat) (hmask : mask < 32768) :",
            "    degreeSum mask = 2 * edgeCount mask := by",
            "  simp only [degreeSum, edgeCount, degree0, degree1, degree2,",
            "    degree3, degree4, degree5]",
            "  omega",
        ])
    elif template == "degree_bound":
        out.extend([
            f"theorem {theorem} (mask : Nat) (hmask : mask < 32768) :",
            "    maximumDegree mask ≤ 5 := by",
        ])
        for i in range(15):
            out.append(f"  have hb{i} := bit_le_one mask {i}")
        for v in range(6):
            out.extend([
                f"  have hd{v} : degree{v} mask ≤ 5 := by",
                f"    simp only [degree{v}]",
                "    omega",
            ])
        out.extend(["  unfold maximumDegree", "  omega"])
    elif template == "triangle_upper_bound":
        out.extend([
            f"theorem {theorem} (mask : Nat) (hmask : mask < 32768) :",
            "    triangleCount mask ≤ 20 := by",
        ])
        for i in range(20):
            out.append(f"  have ht{i} := tri{i}_le_one mask")
        out.extend(["  unfold triangleCount", "  omega"])
    out.extend(["", f"#print axioms {theorem}", "", "end AxiomGraphN6", ""])
    return "\n".join(out)


def build_graph_lean_source(statement: dict, certificate: dict) -> dict:
    """Recheck ALL 32768 graphs before constructing fixed-template Lean input."""
    try:
        claim = GraphStatement.from_dict(statement)
        if claim.n != N or claim.k != 0 or claim.template not in SUPPORTED:
            raise LeanBackendError("only selected exact n=6, k=0 templates are supported")
        check_n6_certificate(statement, certificate)
        if certificate["vacuous"] is not False:
            raise LeanBackendError("cannot formalize a vacuous certificate")
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        raise LeanBackendError("graph certificate failed independent exact-n6 audit") from exc
    sid = digest(statement)
    theorem = "axiom_graph_n6_" + claim.template + "_" + sid[:16]
    source = _source_for_template(claim.template, theorem)
    return {
        "schema": SOURCE_SCHEMA, "statement": statement, "certificate": certificate,
        "statement_sha256": sid, "certificate_sha256": digest(certificate),
        "theorem": "AxiomGraphN6." + theorem,
        "source": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV,
        "scope": "ALL labelled simple graphs with exactly n=6 vertices",
        "all_order_generalization": "NOT_PROVED",
    }


def verify_graph_with_lean(statement: dict, certificate: dict, *,
                           project_root: str | Path = ".",
                           timeout_seconds: int = 180) -> dict[str, Any]:
    """Execute the REAL Lean kernel, fail closed, and preserve complete input."""
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise LeanBackendError("invalid graph Lean timeout")
    proof = build_graph_lean_source(statement, certificate)
    root = Path(project_root).expanduser().resolve()
    result = {
        **proof,
        "schema": SCHEMA,
        "status": "VERIFICATION_PENDING", "accepted": False,
        "axioms": None, "lean_version": None, "checker_exit_code": None,
        "stdout_sha256": None, "stderr_excerpt": "",
        "dependency_manifest_sha256": None, "mathlib_revision": None,
        "toolchain_file_matches": _toolchain_matches(root),
        "command": ["lake", "env", "lean"],
        "duration_seconds": None,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if not result["toolchain_file_matches"] or not (root / "lakefile.toml").is_file():
        result["status"] = "CONFIGURATION_MISSING"
        return result
    if shutil.which("lake") is None:
        result["status"] = "LEAN_UNAVAILABLE"
        return result
    start = time.perf_counter()
    try:
        dep = _dependency_manifest(root)
        result["dependency_manifest_sha256"] = dep["manifest_sha256"]
        result["mathlib_revision"] = dep["mathlib_revision"]
        if not dep["mathlib_revision"]:
            result["status"] = "DEPENDENCY_MANIFEST_MISSING"
            return result
        version = subprocess.run(
            ["lake", "env", "lean", "--version"], cwd=root,
            capture_output=True, text=True, timeout=30, check=False)
        matched = VERSION_RE.search(version.stdout)
        if version.returncode != 0 or not matched:
            result["status"] = "VERSION_CHECK_FAILED"
            return result
        result["lean_version"] = matched.group(1)
        if matched.group(1) != LEAN_VERSION:
            result["status"] = "VERSION_MISMATCH"
            return result
        with tempfile.TemporaryDirectory(prefix="axiom-graph-lean-") as temp:
            path = Path(temp) / "ExactN6.lean"
            path.write_text(proof["source"], encoding="utf-8")
            checked = subprocess.run(
                ["lake", "env", "lean", str(path)], cwd=root,
                capture_output=True, text=True, timeout=timeout_seconds, check=False)
        result["checker_exit_code"] = checked.returncode
        result["stdout_sha256"] = hashlib.sha256(checked.stdout.encode()).hexdigest()
        result["stderr_excerpt"] = checked.stderr[-2048:]
        if (len(checked.stdout.encode()) > MAX_LOG_BYTES or
                len(checked.stderr.encode()) > MAX_LOG_BYTES):
            result["status"] = "OUTPUT_LIMIT_EXCEEDED"
        elif checked.returncode != 0 or checked.stderr.strip():
            result["status"] = "CHECKER_FAILED"
        else:
            axioms = _axiom_report(checked.stdout, proof["theorem"])
            result["axioms"] = axioms
            if axioms is None:
                result["status"] = "AXIOM_AUDIT_MISSING"
            elif not set(axioms).issubset(ALLOWED_AXIOMS):
                result["status"] = "UNTRUSTED_AXIOMS"
            else:
                result["status"], result["accepted"] = "FORMALLY_VERIFIED", True
    except (LeanBackendError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        result["status"] = ("CHECKER_TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired)
                            else "CHECKER_IO_ERROR")
        result["stderr_excerpt"] = str(exc)[:512]
    finally:
        result["duration_seconds"] = round(time.perf_counter() - start, 6)
    return result


def audit_graph_lean_record(record: dict) -> bool:
    """Offline source integrity check; cannot attest that the Lean process ran."""
    if type(record) is not dict or record.get("schema") != SCHEMA:
        raise LeanBackendError("unrecognized graph formal record")
    generated = build_graph_lean_source(record["statement"], record["certificate"])
    for k in ("statement_sha256", "certificate_sha256", "source",
              "source_sha256", "theorem", "toolchain", "mathlib_rev",
              "scope", "all_order_generalization"):
        if record.get(k) != generated[k]:
            raise LeanBackendError("graph Lean evidence fails source binding")
    if record.get("status") == "FORMALLY_VERIFIED":
        if not (record.get("accepted") is True and
                record.get("checker_exit_code") == 0 and
                record.get("toolchain_file_matches") is True and
                record.get("lean_version") == LEAN_VERSION and
                isinstance(record.get("dependency_manifest_sha256"), str) and
                isinstance(record.get("mathlib_revision"), str) and
                len(record["mathlib_revision"]) == 40 and
                isinstance(record.get("stdout_sha256"), str) and
                isinstance(record.get("axioms"), list) and
                set(record["axioms"]).issubset(ALLOWED_AXIOMS)):
            raise LeanBackendError("forged success record")
    elif record.get("accepted") is not False:
        raise LeanBackendError("invalid graph Lean verification status")
    return True


def save_record(record: dict, path: str | Path) -> None:
    """Atomic standalone JSON evidence write; never modify original reports."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=destination.parent,
                                         prefix=".axiom-graph-lean-", delete=False) as stream:
            temp = stream.name
            stream.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
        os.replace(temp, destination)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
