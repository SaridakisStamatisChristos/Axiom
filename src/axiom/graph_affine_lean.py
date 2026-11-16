"""AXIOM v0.19 — sound, intentionally narrow affine-graph Lean translator.

First supported fragment: exact n=6, unconditional affine inequalities with
positive edge and triangle coefficients, optional n coefficient, and an upper
bound derivable from the independent structural envelopes |E|<=15 and
triangles<=20. The real Lean 4 kernel must accept the produced theorem.

This NEVER proves all-order source conjectures: the generated theorem is
quantified over masks encoding graphs on EXACTLY SIX vertices. There is no
fallback to a Python assertion, 'sorry', or 'native_decide'.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from .graph_affine import AffineGraphConjecture
from .graph_claims import digest
from .graph_model import edge_positions
from .lean_backend import (
    _axiom_report, _dependency_manifest, _toolchain_matches,
    ALLOWED_AXIOMS, LEAN_VERSION, TOOLCHAIN, MATHLIB_REV,
    MAX_LOG_BYTES, VERSION_RE, LeanBackendError,
)

SCHEMA = "axiom.graph_affine_n6_lean.v1"
SOURCE_SCHEMA = "axiom.graph_affine_n6_lean_source.v1"
N = 6
EDGE_PAIRS = edge_positions(N)
TRIPLES = tuple(combinations(range(N), 3))
assert len(EDGE_PAIRS) == 15 and len(TRIPLES) == 20


def _supported(stmt: AffineGraphConjecture) -> dict:
    if stmt.assumption != "ALL":
        raise LeanBackendError("conditional graph semantics not supported by n6 Lean translator")
    coeff = dict(stmt.terms)
    if not {"edges", "triangles"} <= coeff.keys() or (
            set(coeff) - {"edges", "triangles", "n"}):
        raise LeanBackendError("only exact n6 edge/triangle envelope with optional n is supported")
    if coeff["edges"] < 1 or coeff["triangles"] < 1:
        raise LeanBackendError("only positive edge/triangle coefficients have an envelope proof")
    ceiling = coeff["edges"] * 15 + coeff["triangles"] * 20 + coeff.get("n", 0) * N
    if ceiling > stmt.upper:
        raise LeanBackendError("candidate not justified by the certified structural envelope")
    return {"coefficients": coeff, "envelope": ceiling}


def _sum(parts: list[str]) -> str:
    return " + ".join(parts) if parts else "0"


def build_affine_lean_source(statement: dict) -> dict:
    """Compile *the typed AST* to a Lean theorem about EXACTLY six vertices."""
    try:
        stmt = AffineGraphConjecture.from_dict(statement)
        proven = _supported(stmt)
    except (ValueError, TypeError, KeyError) as exc:
        raise LeanBackendError("affine statement failed strict canonical semantic audit") from exc
    name = "affine_exact_n6_" + digest(statement)[:20]
    coeff = proven["coefficients"]
    edge_index = {pair: i for i, pair in enumerate(EDGE_PAIRS)}
    out = [
        "-- AXIOM trusted closed translator: n=6 graph masks only.",
        "-- This is NOT a proof for all graph orders.",
        "import Mathlib",
        "",
        "namespace AxiomAffineN6",
        "",
        "private def bit (mask i : Nat) : Nat :=",
        "  if Nat.testBit mask i = true then 1 else 0",
        "",
        "private theorem bit_le_one (mask i : Nat) : bit mask i ≤ 1 := by",
        "  unfold bit",
        "  split_ifs <;> omega",
        "",
        "private def edgeCount (mask : Nat) : Nat :=",
        "  " + _sum([f"bit mask {i}" for i in range(15)]),
        "",
    ]
    for j, (a, b, c) in enumerate(TRIPLES):
        indices = [edge_index[(a, b)], edge_index[(a, c)], edge_index[(b, c)]]
        premise = " ∧ ".join(f"bit mask {k} = 1" for k in indices)
        out.extend([
            f"private def tri{j} (mask : Nat) : Nat :=",
            f"  if {premise} then 1 else 0",
            "",
            f"private theorem tri{j}_le_one (mask : Nat) : tri{j} mask ≤ 1 := by",
            f"  unfold tri{j}",
            "  split_ifs <;> omega",
            "",
        ])
    out.extend([
        "private def triangleCount (mask : Nat) : Nat :=",
        "  " + _sum([f"tri{j} mask" for j in range(20)]),
        "",
    ])
    c = coeff.get("n", 0)
    bound = stmt.upper
    a, b = coeff["edges"], coeff["triangles"]
    out.extend([
        f"theorem {name} (mask : Nat) (hmask : mask < 32768) :",
        f"    ({a} : Int) * (edgeCount mask : Int) +",
        f"    ({b} : Int) * (triangleCount mask : Int) +",
        f"    ({c} : Int) * (6 : Int) ≤ ({bound} : Int) := by",
    ])
    for i in range(15):
        out.append(f"  have hb{i} := bit_le_one mask {i}")
    out.extend([
        "  have he : edgeCount mask ≤ 15 := by",
        "    unfold edgeCount",
        "    omega",
    ])
    for i in range(20):
        out.append(f"  have ht{i} := tri{i}_le_one mask")
    out.extend([
        "  have ht : triangleCount mask ≤ 20 := by",
        "    unfold triangleCount",
        "    omega",
        "  have heZ : (edgeCount mask : Int) ≤ 15 := by exact_mod_cast he",
        "  have htZ : (triangleCount mask : Int) ≤ 20 := by exact_mod_cast ht",
        "  omega",
        "",
        f"#print axioms {name}",
        "",
        "end AxiomAffineN6",
        "",
    ])
    code = "\n".join(out)
    if any(forbidden in code for forbidden in ("sorry", "native_decide", "admit", "axiom ")):
        # 'axiom ' is not an allowed source command, even if a name contains
        # 'axiom'. The generated source only uses definitional facts and omega.
        raise LeanBackendError("forbidden unproved Lean construct in generated source")
    return {
        "schema": SOURCE_SCHEMA,
        "statement": statement,
        "statement_sha256": digest(statement),
        "supported_fragment": "UNCONDITIONAL_N6_POSITIVE_EDGE_TRIANGLE_ENVELOPE",
        "exact_graph_order": N,
        "theorem": "AxiomAffineN6." + name,
        "source": code,
        "source_sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "toolchain": TOOLCHAIN,
        "mathlib_rev": MATHLIB_REV,
        "envelope_upper_bound": proven["envelope"],
        "claim_scope": "exactly n=6 labelled loop-free undirected graphs only",
        "all_orders_verified": False,
    }


def verify_affine_lean(statement: dict, *, project_root: str | Path = ".",
                       timeout_seconds: int = 240) -> dict:
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise LeanBackendError("invalid Lean timeout")
    prepared = build_affine_lean_source(statement)
    root = Path(project_root).expanduser().resolve()
    result = {
        **prepared,
        "schema": SCHEMA, "status": "VERIFICATION_PENDING",
        "accepted": False, "axioms": None, "lean_version": None,
        "checker_exit_code": None, "stdout_sha256": None,
        "stderr_excerpt": "", "dependency_manifest_sha256": None,
        "mathlib_revision": None, "toolchain_file_matches": _toolchain_matches(root),
        "duration_seconds": None, "command": ["lake", "env", "lean"],
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "universal_lean_proof": False,
    }
    if not result["toolchain_file_matches"] or not (root / "lakefile.toml").is_file():
        result["status"] = "CONFIGURATION_MISSING"
        return result
    if shutil.which("lake") is None:
        result["status"] = "LEAN_UNAVAILABLE"
        return result
    start = time.perf_counter()
    try:
        dependency = _dependency_manifest(root)
        result["dependency_manifest_sha256"] = dependency["manifest_sha256"]
        result["mathlib_revision"] = dependency["mathlib_revision"]
        if not dependency["mathlib_revision"]:
            result["status"] = "DEPENDENCY_MANIFEST_MISSING"
            return result
        version = subprocess.run(
            ["lake", "env", "lean", "--version"], cwd=root,
            capture_output=True, text=True, timeout=30, check=False)
        match = VERSION_RE.search(version.stdout)
        if version.returncode or not match:
            result["status"] = "VERSION_CHECK_FAILED"
            return result
        result["lean_version"] = match.group(1)
        if result["lean_version"] != LEAN_VERSION:
            result["status"] = "VERSION_MISMATCH"
            return result
        with tempfile.TemporaryDirectory(prefix="axiom-affine-n6-") as tmp:
            filepath = Path(tmp) / "CertifiedAffineN6.lean"
            filepath.write_text(prepared["source"], encoding="utf-8")
            checked = subprocess.run(
                ["lake", "env", "lean", str(filepath)], cwd=root,
                capture_output=True, text=True,
                timeout=timeout_seconds, check=False)
        result["checker_exit_code"] = checked.returncode
        result["stdout_sha256"] = hashlib.sha256(checked.stdout.encode()).hexdigest()
        result["stderr_excerpt"] = checked.stderr[-2048:]
        if (len(checked.stdout.encode()) > MAX_LOG_BYTES
                or len(checked.stderr.encode()) > MAX_LOG_BYTES):
            result["status"] = "OUTPUT_LIMIT_EXCEEDED"
        elif checked.returncode or checked.stderr.strip():
            result["status"] = "CHECKER_FAILED"
        else:
            result["axioms"] = _axiom_report(checked.stdout, prepared["theorem"])
            if result["axioms"] is None:
                result["status"] = "AXIOM_AUDIT_MISSING"
            elif not set(result["axioms"]).issubset(ALLOWED_AXIOMS):
                result["status"] = "UNTRUSTED_AXIOMS"
            else:
                result["status"], result["accepted"] = "FORMALLY_VERIFIED", True
    except (LeanBackendError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        result["status"] = (
            "CHECKER_TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired)
            else "CHECKER_IO_ERROR")
        result["stderr_excerpt"] = str(exc)[:512]
    finally:
        result["duration_seconds"] = round(time.perf_counter() - start, 6)
    return result


def audit_affine_lean_record(record: dict) -> bool:
    """Check offline source integrity, not external execution attestation."""
    if type(record) is not dict or record.get("schema") != SCHEMA:
        raise LeanBackendError("unrecognized affine Lean evidence schema")
    expected = build_affine_lean_source(record["statement"])
    for key in ("source", "source_sha256", "statement_sha256", "theorem",
                "toolchain", "mathlib_rev", "exact_graph_order",
                "claim_scope", "all_orders_verified", "supported_fragment",
                "envelope_upper_bound"):
        if record.get(key) != expected[key]:
            raise LeanBackendError("affine Lean source or scope changed")
    if (record.get("universal_lean_proof") is not False or
            record.get("all_orders_verified") is not False):
        raise LeanBackendError("false universal theorem scope promotion")
    if record.get("status") == "FORMALLY_VERIFIED":
        if (record.get("accepted") is not True
                or record.get("checker_exit_code") != 0
                or record.get("toolchain_file_matches") is not True
                or record.get("lean_version") != LEAN_VERSION
                or type(record.get("axioms")) is not list
                or not set(record["axioms"]).issubset(ALLOWED_AXIOMS)
                or type(record.get("mathlib_revision")) is not str
                or len(record["mathlib_revision"]) != 40
                or type(record.get("stdout_sha256")) is not str):
            raise LeanBackendError("invalid claimed Lean success record")
    elif record.get("accepted") is not False:
        raise LeanBackendError("invalid pending Lean execution")
    return True


def save_affine_lean_record(record: dict, destination: str) -> None:
    path = Path(destination)
    if path.exists():
        raise LeanBackendError("formal evidence immutable; destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = __import__("os").open(path, __import__("os").O_CREAT |
                              __import__("os").O_EXCL |
                              __import__("os").O_WRONLY, 0o644)
    with __import__("os").fdopen(fd, "wb") as stream:
        stream.write((json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
        stream.flush()
        __import__("os").fsync(stream.fileno())
