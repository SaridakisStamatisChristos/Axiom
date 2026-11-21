"""All-orders proof attempts and offline replay of their evidence."""
from dataclasses import asdict
from hashlib import sha256
from math import isfinite
import re
from time import perf_counter

from .graph_affine import ASSUMPTIONS, VARIABLES
from .graph_affine_lean_n3 import run_affine_kernel
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_discovery import _failed_side
from .graph_model import edge_positions
from .graph_proof_search import LemmaSpec, SearchLimits, search
from .graph_relations import AffineRelation, _vector
from .graph_synthesis import _witness
from .graph_universal_lean import PINNED_MATHLIB_SHA, VERIFIED, _RULES, _lemma_facts, _render_source
from .lean_backend import ALLOWED_AXIOMS, LEAN_VERSION, MATHLIB_REV, TOOLCHAIN, _axiom_report

SCHEMA = "axiom.graph_proof_attempt.v1"
BANK = tuple(LemmaSpec(name, premise, _vector(weights.items()), rhs)
             for name, premise, weights, rhs in _RULES)
UNAVAILABLE = frozenset({
    "CONFIGURATION_MISSING", "LEAN_UNAVAILABLE", "DEPENDENCY_MANIFEST_MISSING",
    "MATHLIB_REVISION_MISMATCH", "VERSION_CHECK_FAILED", "VERSION_MISMATCH",
})
REJECTED = frozenset({
    "CHECKER_FAILED", "CHECKER_TIMEOUT", "CHECKER_IO_ERROR", "CHECKER_OUTPUT_EXCEEDED",
    "LEAN_AXIOM_REPORT_MISSING", "UNTRUSTED_AXIOMS",
})


def _sha(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _unsupported(statement):
    bound = statement.get("bound") if type(statement) is dict else None
    if type(bound) is dict:
        if bound.get("assumption") not in ASSUMPTIONS:
            return "UNSUPPORTED_PREMISE"
        terms = bound.get("lhs")
        if type(terms) is list and any(type(term) is dict and term.get("symbol") not in VARIABLES
                                       for term in terms):
            return "UNSUPPORTED_INVARIANT"
        if type(terms) is list and len(terms) > 6:
            return "UNSUPPORTED_ARITY"
    return "INVALID_CANONICAL_STATEMENT"


def _small_witness(claim, witness_order):
    for order in range(witness_order + 1):
        for mask in range(1 << len(edge_positions(order))):
            side = _failed_side(claim, reference_properties(order, mask))
            if side is not None:
                return _witness(side, order, mask)
    return None


def _prepare(statement, limits, witness_order, external_witness):
    if type(witness_order) is not int or not 0 <= witness_order <= 5:
        raise ValueError("witness order must be between 0 and 5")
    base = {
        "schema": SCHEMA, "statement": statement, "statement_sha256": digest(statement),
        "candidate_id": None, "scope": None, "toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV,
        "expected_mathlib_revision": PINNED_MATHLIB_SHA, "novelty": "NOT_ASSESSED",
        "offline_audit_is_execution_attestation": False, "invariant_order": list(VARIABLES),
        "search_limits": asdict(limits), "witness_order_limit": witness_order,
        "derivation": None, "counterexample": None, "generated": None,
    }
    try:
        claim = AffineRelation.from_dict(statement)
    except (ValueError, TypeError, KeyError):
        return dict(base, status="UNSUPPORTED", reason=_unsupported(statement))
    base.update(candidate_id=claim.id, scope="ALL_GRAPH_ORDERS")
    witness = _small_witness(claim, witness_order)
    if external_witness is not None:
        order = external_witness["exact_order"]
        mask = external_witness["labelled_edge_mask"]
        side = _failed_side(claim, reference_properties(order, mask))
        if side is None or stable(_witness(side, order, mask)) != stable(external_witness):
            raise ValueError("invalid externally supplied graph witness")
        witness = witness or external_witness
    if witness:
        return dict(base, status="COUNTEREXAMPLE", reason="INDEPENDENT_GRAPH_WITNESS",
                    counterexample=witness)

    derivation = search(claim, BANK, limits)
    base["derivation"] = derivation
    if not derivation["derived"]:
        reason = "NODE_BUDGET_EXHAUSTED" if derivation["node_budget_exhausted"] else "NO_BOUNDED_COMBINATION"
        return dict(base, status="SEARCH_EXHAUSTED", reason=reason)
    matches = sorted({(lemma["theorem"], lemma["premise"])
                      for direction in derivation["directions"] for lemma in direction["lemmas"]})
    name = "composite_" + digest(statement)[:24]
    source = _render_source(claim, name, _lemma_facts(matches))
    base["generated"] = {"source": source, "source_sha256": _sha(source),
                         "theorem": f"AxiomGraphUniversal.{name}"}
    return dict(base, status="NOT_ATTEMPTED", reason="DERIVATION_READY")


def _kernel_status(kernel, generated):
    if kernel is None:
        return "NOT_ATTEMPTED", "DERIVATION_READY"
    if type(kernel) is not dict or any(kernel.get(k) != v for k, v in generated.items()):
        raise ValueError("kernel evidence does not match generated source")
    if kernel.get("offline_audit_is_execution_attestation") is not False or kernel.get("command") != [
            "lake", "env", "lean"]:
        raise ValueError("invalid kernel execution metadata")
    for stream in ("stdout", "stderr"):
        log = kernel.get(stream)
        if log is not None and (type(log) is not str or _sha(log) != kernel.get(stream + "_sha256")):
            raise ValueError(f"{stream} digest differs from retained log")
    status = kernel["status"]
    if status == VERIFIED:
        log = kernel.get("stdout")
        axioms = _axiom_report(log, generated["theorem"]) if type(log) is str else None
        if not (kernel.get("accepted") is True and kernel.get("lean_kernel_executed") is True
                and type(kernel.get("checker_exit_code")) is int and kernel["checker_exit_code"] == 0
                and kernel.get("toolchain_file_matches") is True
                and kernel.get("lean_version") == LEAN_VERSION
                and kernel.get("mathlib_revision") == PINNED_MATHLIB_SHA
                and type(kernel.get("dependency_manifest_sha256")) is str
                and re.fullmatch("[0-9a-f]{64}", kernel["dependency_manifest_sha256"])
                and type(kernel.get("stderr")) is str and not kernel["stderr"].strip()
                and kernel.get("stderr_excerpt") == kernel["stderr"][-2048:]
                and axioms is not None and axioms == kernel.get("axioms")
                and set(axioms) <= ALLOWED_AXIOMS):
            raise ValueError("invalid successful kernel evidence")
        return VERIFIED, "LEAN_ACCEPTED_AND_AXIOMS_ALLOWED"
    if kernel.get("accepted") is not False:
        raise ValueError("unexpected kernel acceptance")
    if status in UNAVAILABLE and kernel.get("lean_kernel_executed") is False:
        return "LEAN_UNAVAILABLE", status
    if status in REJECTED:
        return "LEAN_REJECTED", status
    raise ValueError("unknown kernel outcome")


def prove(statement, *, limits=SearchLimits(), witness_order=5, project_root=".", timeout=180,
          provenance=None, external_witness=None):
    if type(timeout) is not int or not 1 <= timeout <= 900:
        raise ValueError("Lean timeout must be between 1 and 900 seconds")
    started = perf_counter()
    attempt = _prepare(statement, limits, witness_order, external_witness)
    elapsed = perf_counter() - started
    kernel = None
    if attempt["generated"] is not None:
        kernel = run_affine_kernel(
            attempt["generated"], project_root, timeout, VERIFIED,
            expected_mathlib_revision=PINNED_MATHLIB_SHA, retain_logs=True)
        attempt["status"], attempt["reason"] = _kernel_status(kernel, attempt["generated"])
    attempt.update(kernel=kernel, search_elapsed_seconds=elapsed, lean_timeout_seconds=timeout,
                   provenance=provenance,
                   external_witness=external_witness)
    return {**attempt, "record_sha256": digest(attempt)}


def audit(attempt):
    if type(attempt) is not dict or attempt.get("schema") != SCHEMA:
        raise ValueError("unknown proof attempt schema")
    payload = {key: value for key, value in attempt.items() if key != "record_sha256"}
    if digest(payload) != attempt.get("record_sha256"):
        raise ValueError("proof attempt digest mismatch")
    elapsed, timeout = attempt["search_elapsed_seconds"], attempt["lean_timeout_seconds"]
    if (type(elapsed) not in (int, float) or not isfinite(elapsed) or elapsed < 0
            or type(timeout) is not int or not 1 <= timeout <= 900):
        raise ValueError("invalid proof timing evidence")
    expected = _prepare(attempt["statement"], SearchLimits(**attempt["search_limits"]),
                        attempt["witness_order_limit"], attempt["external_witness"])
    kernel = attempt["kernel"]
    if expected["generated"] is not None:
        expected["status"], expected["reason"] = _kernel_status(kernel, expected["generated"])
    elif kernel is not None:
        raise ValueError("unexpected kernel evidence")
    if any(stable(attempt.get(key)) != stable(value) for key, value in expected.items()):
        raise ValueError("proof attempt differs from deterministic replay")
    return True
