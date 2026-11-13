"""Optional *real* Lean 4 proof backend. Pure generation never marks a theorem verified.

Trust boundary: the fixed AST-to-Lean translation is trusted as the formalization
of AXIOM's supported integer fragment. Proof term acceptance is delegated to
Lean and Mathlib; the Python certificate checker is a preliminary gate only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from typing import Any

from .certificate_checker import CertificateError, check_certificate, statement_digest
from .mathematics import Expr, Statement

LEAN_VERSION = "4.35.0"
MATHLIB_REV = "v4.35.0"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
SOURCE_SCHEMA = "axiom.lean4.proof_source.v1"
RESULT_SCHEMA = "axiom.lean4.verification.v1"
# Limits are explicitly separate from the stand-alone coefficient certificate budgets.
MAX_SOURCE_BYTES = 250_000
MAX_LOG_BYTES = 65_536
ANSI_ESC = re.compile(r"\x1b\[[0-9;]*m")
VERSION_RE = re.compile(r"\bversion\s+(\d+\.\d+\.\d+)\b")


class LeanBackendError(ValueError):
    """Unsafe, unsupported or malformed input to the external checker."""


def _num(value: int) -> str:
    if type(value) is not int:
        raise LeanBackendError("invalid integer literal")
    return f"({value} : Int)"


def _expr(expr: Expr) -> str:
    if expr.op == "const":
        return _num(expr.value)
    if expr.op == "var":
        return str(expr.value)  # restricted by the typed AST to x or y
    if expr.op == "pow":
        return f"({_expr(expr.args[0])} ^ {expr.value})"
    a, b = (_expr(e) for e in expr.args)
    sign = {"add": "+", "sub": "-", "mul": "*"}[expr.op]
    return f"({a} {sign} {b})"


def _poly(terms: list, names: tuple[str, ...]) -> str:
    """Render already independently checked sparse integer polynomial terms."""
    if not terms:
        return _num(0)
    pieces = []
    for monomial, coefficient in terms:
        factors = [_num(coefficient)]
        factors.extend(f"({name} ^ {degree})" for name, degree in zip(names, monomial) if degree)
        pieces.append("(" + " * ".join(factors) + ")")
    return "(" + " + ".join(pieces) + ")"


def build_lean_source(statement: dict, certificate: dict) -> dict[str, Any]:
    """Generate a fixed, closed Lean theorem only from certified typed input.

    No arbitrary Lean code, imports, user-specified tactic, custom axiom or
    include path can enter through the statement/certificate serialization.
    """
    try:
        check_certificate(statement, certificate)
        stmt = Statement.from_dict(statement)
    except (CertificateError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise LeanBackendError("failed independent mathematical input check") from exc
    method = certificate["method"]
    if method not in ("coefficient_identity", "sum_of_squares"):
        raise LeanBackendError("unsupported Lean proof method")
    theorem = "axiom_" + statement_digest(statement)[:24]
    names = tuple(stmt.variables)
    decl = " ".join(f"({name} : Int)" for name in names)
    assumptions = " ".join(
        f"(h{idx} : {_num(lo)} ≤ {name} ∧ {name} ≤ {_num(hi)})"
        for idx, (name, lo, hi) in enumerate(stmt.bounds)
    )
    relation = {"==": "=", ">=": "≥", "<=": "≤"}[stmt.relation]
    proposition = f"{_expr(stmt.lhs)} {relation} {_expr(stmt.rhs)}"
    tactic = []
    if method == "coefficient_identity":
        tactic = ["  ring"]
    else:
        target = (f"({_expr(stmt.lhs)} - {_expr(stmt.rhs)})" if stmt.relation == ">=" else
                  f"({_expr(stmt.rhs)} - {_expr(stmt.lhs)})")
        square_parts = []
        for idx, sq in enumerate(certificate["squares"]):
            p = _poly(sq["polynomial"], names)
            tactic.append(f"  have hs{idx} : (0 : Int) ≤ ({p}) ^ 2 := sq_nonneg ({p})")
            square_parts.append(f"({_num(sq['weight'])} * ({p}) ^ 2)")
        square_parts.append(_num(certificate["constant"]))
        cert_eq = (f"({_num(certificate['multiplier'])} * {target}) = " +
                   "(" + " + ".join(square_parts) + ")")
        tactic.append(f"  have hcert : {cert_eq} := by ring")
        tactic.append("  nlinarith" + (" [" + ", ".join("hs" + str(i) for i in range(len(certificate["squares"]))) + "]" if certificate["squares"] else ""))
    imports = ["Mathlib.Tactic.Ring"] if method == "coefficient_identity" else ["Mathlib.Tactic.Ring", "Mathlib.Tactic.Linarith"]
    source = ("-- Generated exclusively from a separately validated AXIOM v0.2 certificate.\n" +
              f"-- Statement SHA-256: {statement_digest(statement)}\n" +
              "\n".join("import " + x for x in imports) + "\n\n" +
              f"theorem {theorem} {decl}" + (" " + assumptions if assumptions else "") +
              f" : {proposition} := by\n" + "\n".join(tactic) + "\n\n" +
              f"#print axioms {theorem}\n")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise LeanBackendError("Lean source exceeds size cap")
    if re.search(r"\b(?:sorry|sorryAx|admit|native_decide|axiom|unsafe|run_tac|set_option)\b", "\n".join(tactic)):
        raise LeanBackendError("disallowed tactic or axiom construct")
    return {"schema": SOURCE_SCHEMA, "theorem": theorem, "statement": statement,
            "statement_sha256": statement_digest(statement), "certificate": certificate,
            "method": method, "imports": imports, "assumptions": list(stmt.bounds),
            "toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV, "source": source,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()}


def _axiom_report(log: str, theorem: str) -> list[str] | None:
    """Require exactly one matching #print axioms declaration audit line."""
    text = ANSI_ESC.sub("", log)
    matches = []
    pattern = re.compile(r"^(?:[^\n]*?:[0-9]+:[0-9]+:\s*info:\s*)?\s*'?" + re.escape(theorem) +
                         r"'?(?: does not depend on any axioms| depends on axioms: \[([^\]\n]*)\])\s*$")
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if match:
            matches.append([] if match.group(1) is None else [s.strip() for s in match.group(1).split(",")])
    if len(matches) != 1 or any(not name for name in matches[0]):
        return None
    return matches[0]


def _toolchain_matches(project_root: Path) -> bool:
    """Require stable Lean and Mathlib pins; no silently swapped dependency."""
    try:
        if (project_root / "lean-toolchain").read_text(encoding="utf-8").strip() != TOOLCHAIN:
            return False
        config = tomllib.loads((project_root / "lakefile.toml").read_text(encoding="utf-8"))
        mathlibs = [req for req in config.get("require", []) if req.get("name") == "mathlib"]
        return len(mathlibs) == 1 and mathlibs[0].get("rev") == MATHLIB_REV and \
            mathlibs[0].get("scope") == "leanprover-community"
    except (OSError, ValueError, TypeError, KeyError):
        return False


def _dependency_manifest(root: Path) -> dict[str, str | None]:
    """Record actual resolved Mathlib revision and a hash of Lake's manifest."""
    path = root / "lake-manifest.json"
    if not path.is_file():
        return {"manifest_sha256": None, "mathlib_revision": None}
    raw = path.read_bytes()
    data = json.loads(raw)
    libs = [x for x in data.get("packages", []) if x.get("name") == "mathlib"]
    if len(libs) != 1 or not isinstance(libs[0].get("rev"), str) or len(libs[0]["rev"]) != 40:
        raise LeanBackendError("Lake dependency manifest does not pin mathlib")
    revision = libs[0]["rev"]
    result = subprocess.run(["git", "-C", str(root / ".lake/packages/mathlib"), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=10, check=False)
    if result.returncode != 0 or result.stdout.strip() != revision:
        raise LeanBackendError("checked-out mathlib does not match manifest")
    return {"manifest_sha256": hashlib.sha256(raw).hexdigest(), "mathlib_revision": revision}


def verify_with_lean(statement: dict, certificate: dict, *, project_root: str | Path,
                     timeout_seconds: int = 120, max_memory_mb: int | None = None) -> dict[str, Any]:
    """Run *installed* Lean and audit transitive axioms; never infer success.

    Verification proof evidence lives in a distinct record from v0.2 local
    evidence. A failed adapter cannot promote an original research finding.
    max_memory_mb is reserved for future process isolation and not enforced.
    """
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1200:
        raise LeanBackendError("invalid Lean timeout")
    if max_memory_mb is not None:
        raise LeanBackendError("memory limiting not implemented; use external OS isolation")
    generated = build_lean_source(statement, certificate)
    root = Path(project_root).expanduser().resolve()
    stamp = time.time()
    outcome: dict[str, Any] = {
        "schema": RESULT_SCHEMA, "status": "VERIFICATION_PENDING", "accepted": False,
        "theorem": generated["theorem"], "statement_sha256": generated["statement_sha256"],
        "statement": statement, "assumptions": generated["assumptions"],
        "certificate": certificate, "source_sha256": generated["source_sha256"],
        "source": generated["source"], "imports": generated["imports"],
        "expected_toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV,
        "toolchain_file_matches": _toolchain_matches(root),
        "dependency_manifest_sha256": None, "mathlib_revision": None,
        "lean_version": None, "axioms": None, "command": ["lake", "env", "lean"],
        "checker_exit_code": None, "stdout_sha256": None, "stderr_excerpt": "",
        "duration_seconds": None, "timestamp_utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stamp)),
    }
    if not outcome["toolchain_file_matches"] or not (root / "lakefile.toml").is_file():
        outcome["status"] = "CONFIGURATION_MISSING"
        return outcome
    if shutil.which("lake") is None:
        outcome["status"] = "LEAN_UNAVAILABLE"
        return outcome
    begin = time.perf_counter()
    try:
        dependencies = _dependency_manifest(root)
        outcome["dependency_manifest_sha256"] = dependencies["manifest_sha256"]
        outcome["mathlib_revision"] = dependencies["mathlib_revision"]
        if not dependencies["mathlib_revision"]:
            outcome["status"] = "DEPENDENCY_MANIFEST_MISSING"
            return outcome
        version = subprocess.run(["lake", "env", "lean", "--version"], cwd=root, capture_output=True,
                                 text=True, timeout=min(timeout_seconds, 30), check=False)
        match = VERSION_RE.search(version.stdout)
        if version.returncode != 0 or not match:
            outcome["status"] = "VERSION_CHECK_FAILED"
            outcome["stderr_excerpt"] = (version.stderr or version.stdout)[:1000]
            return outcome
        outcome["lean_version"] = match.group(1)
        if match.group(1) != LEAN_VERSION:
            outcome["status"] = "VERSION_MISMATCH"
            return outcome
        with tempfile.TemporaryDirectory(prefix="axiom-lean-") as temp:
            path = Path(temp) / f"{generated['theorem']}.lean"
            path.write_text(generated["source"], encoding="utf-8")
            check = subprocess.run(["lake", "env", "lean", str(path)], cwd=root,
                                   capture_output=True, text=True, timeout=timeout_seconds, check=False)
        outcome["checker_exit_code"] = check.returncode
        outcome["stdout_sha256"] = hashlib.sha256(check.stdout.encode("utf-8")).hexdigest()
        outcome["stderr_excerpt"] = check.stderr[-2048:]
        if len(check.stdout.encode("utf-8")) > MAX_LOG_BYTES or len(check.stderr.encode("utf-8")) > MAX_LOG_BYTES:
            outcome["status"] = "OUTPUT_LIMIT_EXCEEDED"
        elif check.returncode != 0 or check.stderr.strip():
            outcome["status"] = "CHECKER_FAILED"
        else:
            axioms = _axiom_report(check.stdout, generated["theorem"])
            outcome["axioms"] = axioms
            if axioms is None:
                outcome["status"] = "AXIOM_AUDIT_MISSING"
            elif not set(axioms).issubset(ALLOWED_AXIOMS):
                outcome["status"] = "UNTRUSTED_AXIOMS"
            else:
                outcome["status"] = "FORMALLY_VERIFIED"
                outcome["accepted"] = True
    except (LeanBackendError, ValueError, TypeError, KeyError) as exc:
        outcome["status"] = "DEPENDENCY_MANIFEST_INVALID"
        outcome["stderr_excerpt"] = str(exc)[:512]
    except subprocess.TimeoutExpired:
        outcome["status"] = "CHECKER_TIMEOUT"
    except OSError as exc:
        outcome["status"] = "CHECKER_IO_ERROR"
        outcome["stderr_excerpt"] = str(exc)[:512]
    finally:
        outcome["duration_seconds"] = round(time.perf_counter() - begin, 6)
    return outcome


def verify_saved_artifact(artifact_path: str | Path, *, project_root: str | Path,
                          timeout_seconds: int = 120) -> dict[str, Any]:
    record = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    if not isinstance(record, dict) or set(record) != {"statement", "certificate"}:
        raise LeanBackendError("artifact requires exactly statement and certificate")
    return verify_with_lean(record["statement"], record["certificate"],
                            project_root=project_root, timeout_seconds=timeout_seconds)


def verify_record_integrity(record: dict[str, Any]) -> bool:
    """Offline audit of source binding, *not* proof of an actual Lean execution."""
    if not isinstance(record, dict) or record.get("schema") != RESULT_SCHEMA:
        raise LeanBackendError("unrecognized formal evidence schema")
    expected = build_lean_source(record["statement"], record["certificate"])
    if (record.get("source") != expected["source"] or
        record.get("source_sha256") != expected["source_sha256"] or
        record.get("statement_sha256") != expected["statement_sha256"] or
        record.get("theorem") != expected["theorem"] or
        record.get("imports") != expected["imports"] or
        record.get("expected_toolchain") != TOOLCHAIN or
        record.get("mathlib_rev") != MATHLIB_REV):
        raise LeanBackendError("formal evidence input/source binding mismatch")
    if record.get("status") == "FORMALLY_VERIFIED":
        if not (record.get("accepted") is True and record.get("checker_exit_code") == 0 and
                record.get("toolchain_file_matches") is True and record.get("lean_version") == LEAN_VERSION and
                isinstance(record.get("dependency_manifest_sha256"), str) and
                isinstance(record.get("mathlib_revision"), str) and len(record["mathlib_revision"]) == 40 and
                isinstance(record.get("axioms"), list) and
                set(record["axioms"]).issubset(ALLOWED_AXIOMS) and
                isinstance(record.get("stdout_sha256"), str)):
            raise LeanBackendError("inconsistent formal verification status")
    elif record.get("accepted") is not False:
        raise LeanBackendError("unsupported status/acceptance pair")
    return True
