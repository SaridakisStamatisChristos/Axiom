"""AXIOM v0.19 — CLOSED exact-n3 affine-to-Lean graph proof bridge.

Actual graph semantics, not an unverified lookup table: three labelled edge
bits, a sum of edges, and a conjunction defining a triangle. Source generation
proves the generated typed relation for all 8 labelled n=3 simple graphs.

IMPORTANT: n=3 finite-order formal verification does NOT prove the original
all-orders graph conjecture. Reject every unimplemented invariant/assumption.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .graph_affine import AffineGraphConjecture, check_conjecture
from .graph_checker import reference_properties
from .graph_campaign import _discovery_properties
from .graph_claims import digest, stable
from .graph_lean import (
    _axiom_report, _dependency_manifest, _toolchain_matches, LEAN_VERSION,
    TOOLCHAIN, MATHLIB_REV, ALLOWED_AXIOMS, MAX_LOG_BYTES,
    VERSION_RE, LeanBackendError,
)

SCHEMA = "axiom.affine.n3.lean_evidence.v1"
DISCOVERY_SCHEMA = "axiom.affine.n3.discovery_lean_evidence.v1"
SUPPORTED = ("edges", "triangles", "n")
ORDER = 3
TOTAL_MASKS = 8


def _expression(stmt: AffineGraphConjecture, extended: bool) -> str:
    edges = "edgeCount mask.val"
    clique = f"(if {edges} = 3 then 3 else if {edges} = 0 then 1 else 2)"
    values = {"edges": edges, "triangles": "triangleCount mask.val"}
    if extended:
        # Graphs on three vertices have four isomorphism types, determined
        # by their edge counts: empty, one edge, a path, and a triangle.
        values.update({
            "independence": f"(if {edges} = 0 then 3 else if {edges} = 3 then 1 else 2)",
            "clique": clique,
            "chromatic": clique,
            "maximum_degree": f"(min ({edges}) 2)",
            "matching": f"(min ({edges}) 1)",
            "components": f"(max (3 - ({edges})) 1)",
        })
    terms = [
        f"({coefficient} : Int) * "
        + ("(3 : Int)" if symbol == "n" else f"(Int.ofNat ({values[symbol]}))")
        for symbol, coefficient in stmt.terms
    ]
    return " + ".join(terms)


def build_n3_affine_source(statement: dict, *, extended: bool = False) -> dict:
    try:
        stmt = AffineGraphConjecture.from_dict(statement)
    except (ValueError, TypeError, KeyError) as exc:
        raise LeanBackendError("affine n3 statement failed typed parsing") from exc
    if not extended and (stmt.assumption != "ALL" or
                         any(key not in SUPPORTED for key, _ in stmt.terms)):
        raise LeanBackendError(
            "unsupported n3 affine statement; conditional graph assumptions not translated")
    applicable_count = 0
    for mask in range(TOTAL_MASKS):
        oracle = reference_properties(ORDER, mask)
        applies, valid, value = check_conjecture(stmt, oracle)
        other_applies, other_valid, other_value = check_conjecture(
            stmt, _discovery_properties(ORDER, mask))
        if (applies != other_applies or
                valid != other_valid or value != other_value):
            raise LeanBackendError("independent n3 affine semantics disagree")
        if not applies:
            continue
        applicable_count += 1
        if not valid:
            raise LeanBackendError(
                "n3 exact-order affine conjecture is refuted by a labelled graph")
    if not applicable_count:
        raise LeanBackendError("n3 affine statement has no applicable labelled graph")
    statement_hash = digest(statement)
    theorem = ("axiom_discovery_n3_" if extended else "axiom_affine_n3_") + statement_hash[:16]
    premise = {
        "ALL": "", "CONNECTED": "2 ≤ edgeCount mask.val → ",
        "BIPARTITE": "edgeCount mask.val < 3 → ",
        "TRIANGLE_FREE": "edgeCount mask.val < 3 → ",
    }[stmt.assumption]
    signature = f"theorem {theorem} : ∀ mask : Fin 8," if extended else f"theorem {theorem} (mask : Fin 8) :"
    source = "\n".join([
        "-- Closed AXIOM affine graph bridge: n=3 ONLY, not all orders.",
        "-- Three labelled edges: (0,1) bit 0, (0,2) bit 1, (1,2) bit 2.",
        "-- Formal predicates operate on mask.val of Fin 8, covering all labelled graphs.",
        "import Lean" if extended else "import Mathlib", "",
        "namespace AxiomAffineN3", "",
        "private def bit (mask i : Nat) : Nat :=",
        "  if Nat.testBit mask i then 1 else 0", "",
        "private def edgeCount (mask : Nat) : Nat :=",
        "  bit mask 0 + bit mask 1 + bit mask 2", "",
        "private def triangleCount (mask : Nat) : Nat :=",
        "  if bit mask 0 = 1 ∧ bit mask 1 = 1 ∧ bit mask 2 = 1 then 1 else 0", "",
        signature,
        f"    {premise}{_expression(stmt, extended)} ≤ ({stmt.upper} : Int) := by",
        "  decide" if extended else "  fin_cases mask <;> decide", "",
        f"#print axioms {theorem}", "",
        "end AxiomAffineN3", "",
    ])
    return {
        "schema": DISCOVERY_SCHEMA if extended else SCHEMA, "statement": stmt.to_dict(),
        "statement_sha256": statement_hash,
        "source": source,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "theorem": f"AxiomAffineN3.{theorem}",
        "toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV,
        "formal_graph_order": ORDER,
        "labelled_graphs_semantically_prechecked": applicable_count,
        "formal_scope": ("exactly n=3 labelled simple graphs satisfying " + stmt.assumption
                         if extended else "all 8 labelled simple graphs with exactly n=3 vertices"),
        "all_order_generalization": "NOT_PROVED",
    }


def verify_n3_affine(statement: dict, *, project_root: str = ".",
                     timeout_seconds: int = 180, extended: bool = False) -> dict:
    return run_affine_kernel(
        build_n3_affine_source(statement, extended=extended),
        project_root, timeout_seconds, "FORMALLY_VERIFIED_EXACT_N3")


def run_affine_kernel(result, project_root, timeout_seconds, success_status, *,
                      expected_mathlib_revision=None, retain_logs=False):
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 900:
        raise LeanBackendError("invalid affine Lean timeout")
    root = Path(project_root).expanduser().resolve()
    record = {
        **result,
        "status": "VERIFICATION_PENDING", "accepted": False,
        "lean_kernel_executed": False, "axioms": None,
        "lean_version": None, "checker_exit_code": None,
        "stdout_sha256": None, "stderr_excerpt": "",
        "dependency_manifest_sha256": None, "mathlib_revision": None,
        "toolchain_file_matches": _toolchain_matches(root),
        "command": ["lake", "env", "lean"],
        "duration_seconds": None,
        "offline_audit_is_execution_attestation": False,
    }
    if retain_logs:
        record.update(stdout=None, stderr=None, stderr_sha256=None)
    if not record["toolchain_file_matches"] or not (root/"lakefile.toml").is_file():
        record["status"] = "CONFIGURATION_MISSING"
        return record
    if shutil.which("lake") is None:
        record["status"] = "LEAN_UNAVAILABLE"
        return record
    started = time.perf_counter()
    try:
        dependency = _dependency_manifest(root)
        record["dependency_manifest_sha256"] = dependency["manifest_sha256"]
        record["mathlib_revision"] = dependency["mathlib_revision"]
        if not record["mathlib_revision"]:
            record["status"] = "DEPENDENCY_MANIFEST_MISSING"
            return record
        if expected_mathlib_revision and record["mathlib_revision"] != expected_mathlib_revision:
            record["status"] = "MATHLIB_REVISION_MISMATCH"
            return record
        version = subprocess.run(
            ["lake", "env", "lean", "--version"], cwd=root,
            capture_output=True, text=True, timeout=30, check=False)
        match = VERSION_RE.search(version.stdout)
        if version.returncode or not match:
            record["status"] = "VERSION_CHECK_FAILED"
            return record
        record["lean_version"] = match.group(1)
        if record["lean_version"] != LEAN_VERSION:
            record["status"] = "VERSION_MISMATCH"
            return record
        with tempfile.TemporaryDirectory(prefix="axiom-affine-n3-") as temp:
            path = Path(temp)/"AffineN3.lean"
            path.write_text(result["source"], encoding="utf-8")
            checked = subprocess.run(
                ["lake", "env", "lean", str(path)], cwd=root,
                capture_output=True, text=True, timeout=timeout_seconds,
                check=False)
        record["lean_kernel_executed"] = True
        record["checker_exit_code"] = checked.returncode
        record["stdout_sha256"] = hashlib.sha256(
            checked.stdout.encode("utf-8")).hexdigest()
        record["stderr_excerpt"] = checked.stderr[-2048:]
        oversized = (len(checked.stdout.encode()) > MAX_LOG_BYTES
                     or len(checked.stderr.encode()) > MAX_LOG_BYTES)
        if retain_logs and not oversized:
            record.update(stdout=checked.stdout, stderr=checked.stderr,
                          stderr_sha256=hashlib.sha256(checked.stderr.encode("utf-8")).hexdigest())
        if oversized:
            record["status"] = "CHECKER_OUTPUT_EXCEEDED"
        elif checked.returncode != 0 or checked.stderr.strip():
            record["status"] = "CHECKER_FAILED"
        else:
            axioms = _axiom_report(checked.stdout, record["theorem"])
            record["axioms"] = axioms
            if axioms is None:
                record["status"] = "LEAN_AXIOM_REPORT_MISSING"
            elif not set(axioms).issubset(ALLOWED_AXIOMS):
                record["status"] = "UNTRUSTED_AXIOMS"
            else:
                record["status"],record["accepted"] = success_status,True
    except (LeanBackendError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        record["status"] = (
            "CHECKER_TIMEOUT" if isinstance(exc, subprocess.TimeoutExpired)
            else "CHECKER_IO_ERROR")
        record["stderr_excerpt"] = str(exc)[:512]
    finally:
        record["duration_seconds"] = round(time.perf_counter()-started, 6)
    return record


def audit_n3_affine(record: dict) -> bool:
    """Source replay verifies integrity, NOT actual past external execution."""
    if type(record) is not dict or record.get("schema") not in (SCHEMA, DISCOVERY_SCHEMA):
        raise LeanBackendError("unknown affine n3 source binding")
    expected = build_n3_affine_source(record["statement"], extended=record["schema"] == DISCOVERY_SCHEMA)
    for key, value in expected.items():
        if record.get(key) != value:
            raise LeanBackendError("altered affine Lean semantics/source identity")
    if record.get("all_order_generalization") != "NOT_PROVED":
        raise LeanBackendError("attempted universal theorem promotion")
    if record.get("status") == "FORMALLY_VERIFIED_EXACT_N3":
        if not (record.get("accepted") is True and
                record.get("lean_kernel_executed") is True and
                record.get("checker_exit_code") == 0 and
                record.get("toolchain_file_matches") is True and
                record.get("lean_version") == LEAN_VERSION and
                isinstance(record.get("dependency_manifest_sha256"), str) and
                isinstance(record.get("mathlib_revision"), str) and
                len(record["mathlib_revision"]) == 40 and
                isinstance(record.get("stdout_sha256"), str) and
                isinstance(record.get("axioms"), list) and
                set(record["axioms"]).issubset(ALLOWED_AXIOMS)):
            raise LeanBackendError("forged n3 finite-order Lean success record")
    elif record.get("accepted") is not False:
        raise LeanBackendError("invalid Lean acceptance without success")
    return True
