"""Standalone, stdlib-only checker for AXIOM v0.2 algebraic certificates.

No imports from the conjecture generator, symbolic engine, or SymPy. It can be
executed as `python src/axiom/certificate_checker.py ARTIFACT.json`.

Trust base: Python arbitrary precision integers, JSON parser, and this small
coefficient-ring checker. Acceptance is *not* Lean kernel verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "axiom.polynomial.certificate.v1"
MAX_AST_NODES = 128
MAX_COEFFICIENT_BITS = 4096
MAX_POLYNOMIAL_TERMS = 4096
MAX_TOTAL_DEGREE = 128
MAX_MULTIPLICATION_PAIRS = 200_000


class CertificateError(ValueError):
    """Malformed, invalid, unsupported, or excessive certificate."""


def _integer(x: Any, *, nonnegative: bool = False, positive: bool = False) -> int:
    if type(x) is not int or x.bit_length() > MAX_COEFFICIENT_BITS:
        raise CertificateError("non-integer or oversized integer")
    if (positive and x <= 0) or (nonnegative and x < 0):
        raise CertificateError("invalid integer sign")
    return x


def _guard(poly: dict[tuple[int, ...], int]) -> dict[tuple[int, ...], int]:
    clean = {m: c for m, c in poly.items() if c}
    if len(clean) > MAX_POLYNOMIAL_TERMS:
        raise CertificateError("polynomial term budget exceeded")
    if any(sum(m) > MAX_TOTAL_DEGREE or any(n < 0 for n in m) for m in clean):
        raise CertificateError("polynomial degree budget exceeded")
    if any(c.bit_length() > MAX_COEFFICIENT_BITS for c in clean.values()):
        raise CertificateError("polynomial coefficient budget exceeded")
    return clean


def _plus(p: dict, q: dict, sign: int = 1) -> dict:
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, 0) + sign * c
    return _guard(r)


def _times(p: dict, q: dict) -> dict:
    if len(p) * len(q) > MAX_MULTIPLICATION_PAIRS:
        raise CertificateError("polynomial multiplication work budget exceeded")
    out: dict[tuple[int, ...], int] = {}
    for m, a in p.items():
        for n, b in q.items():
            power = tuple(i + j for i, j in zip(m, n))
            if sum(power) > MAX_TOTAL_DEGREE:
                raise CertificateError("polynomial degree budget exceeded")
            out[power] = out.get(power, 0) + a * b
    return _guard(out)


def _scale(p: dict, factor: int) -> dict:
    return _guard({m: c * factor for m, c in p.items()})


def _normal_form(node: Any, variables: tuple[str, ...], budget: list[int]) -> dict:
    budget[0] += 1
    if budget[0] > MAX_AST_NODES or not isinstance(node, dict) or set(node) != {"op", "value", "args"}:
        raise CertificateError("invalid or oversized expression")
    op, value, args = node["op"], node["value"], node["args"]
    if type(op) is not str or type(args) is not list:
        raise CertificateError("malformed expression fields")
    zero = (0,) * len(variables)
    if op == "const" and len(args) == 0:
        c = _integer(value)
        return {zero: c} if c else {}
    if op == "var" and len(args) == 0 and type(value) is str and value in variables:
        m = [0] * len(variables)
        m[variables.index(value)] = 1
        return {tuple(m): 1}
    if op == "pow" and len(args) == 1:
        n = _integer(value, nonnegative=True)
        if n > 8:
            raise CertificateError("exponent outside supported grammar")
        b = _normal_form(args[0], variables, budget)
        result = {zero: 1}
        for _ in range(n):
            result = _times(result, b)
        return result
    if op in ("add", "sub", "mul") and len(args) == 2 and value is None:
        p = _normal_form(args[0], variables, budget)
        q = _normal_form(args[1], variables, budget)
        if op == "mul":
            return _times(p, q)
        return _plus(p, q, -1 if op == "sub" else 1)
    raise CertificateError("unsupported expression operation or arity")


def _statement(stmt: Any) -> tuple[tuple[str, ...], dict, dict, str]:
    if not isinstance(stmt, dict) or set(stmt) != {"lhs", "rhs", "relation", "variables", "bounds"}:
        raise CertificateError("invalid statement encoding")
    names, bounds, relation = stmt["variables"], stmt["bounds"], stmt["relation"]
    if (type(names) is not list or len(names) not in (1, 2) or
            len(set(str(x) for x in names)) != len(names) or
            any(type(x) is not str or x not in ("x", "y") for x in names)):
        raise CertificateError("unsupported or duplicated quantified variables")
    if relation not in ("==", ">=", "<=") or not isinstance(bounds, list):
        raise CertificateError("unsupported relation or bounds")
    used: set[str] = set()
    for entry in bounds:
        if not isinstance(entry, list) or len(entry) != 3:
            raise CertificateError("invalid assumption format")
        v, lo, hi = entry
        if type(v) is not str or v not in names or v in used or _integer(lo) > _integer(hi):
            raise CertificateError("contradictory or duplicated assumptions")
        used.add(v)
    budget = [0]
    left = _normal_form(stmt["lhs"], tuple(names), budget)
    right = _normal_form(stmt["rhs"], tuple(names), budget)
    return tuple(names), left, right, relation


def _load_coefficients(data: Any, nvars: int) -> dict:
    if not isinstance(data, list) or len(data) > MAX_POLYNOMIAL_TERMS:
        raise CertificateError("invalid term list")
    result: dict[tuple[int, ...], int] = {}
    previous: tuple[int, ...] | None = None
    for term in data:
        if not isinstance(term, list) or len(term) != 2 or not isinstance(term[0], list) or len(term[0]) != nvars:
            raise CertificateError("invalid coefficient tuple")
        exp = tuple(_integer(x, nonnegative=True) for x in term[0])
        if sum(exp) > MAX_TOTAL_DEGREE or (previous is not None and exp <= previous):
            raise CertificateError("non-canonical or excessive monomial order")
        coef = _integer(term[1])
        if coef == 0:
            raise CertificateError("zero coefficient in normalized list")
        result[exp] = coef
        previous = exp
    return _guard(result)


def _encode_coefficients(poly: dict) -> list:
    return [[list(exponents), coef] for exponents, coef in sorted(poly.items()) if coef]


def statement_digest(statement: dict) -> str:
    return hashlib.sha256(json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def check_supported_statement(statement: Any) -> None:
    """Reject inputs exceeding standalone checker limits before proof construction."""
    _statement(statement)


def check_certificate(statement: Any, certificate: Any) -> bool:
    """Raises CertificateError on any invalid artifact; never accepts sampled evidence."""
    if not isinstance(certificate, dict) or certificate.get("schema") != SCHEMA:
        raise CertificateError("unsupported certificate schema")
    names, lhs, rhs, relation = _statement(statement)
    if certificate.get("statement_sha256") != statement_digest(statement):
        raise CertificateError("certificate bound to different statement")
    if certificate.get("variables") != list(names):
        raise CertificateError("certificate quantified variables differ")
    method = certificate.get("method")
    if method == "coefficient_identity":
        if set(certificate) != {"schema", "statement_sha256", "variables", "method", "lhs_coefficients", "rhs_coefficients"}:
            raise CertificateError("unexpected or missing identity fields")
        if relation != "==":
            raise CertificateError("identity certificate on a non-equality")
        c_lhs = _load_coefficients(certificate["lhs_coefficients"], len(names))
        c_rhs = _load_coefficients(certificate["rhs_coefficients"], len(names))
        if c_lhs != lhs or c_rhs != rhs or lhs != rhs:
            raise CertificateError("polynomial coefficient identity does not hold")
        return True
    if method == "sum_of_squares":
        if set(certificate) != {"schema", "statement_sha256", "variables", "method", "multiplier", "squares", "constant"}:
            raise CertificateError("unexpected or missing SOS fields")
        if relation not in (">=", "<="):
            raise CertificateError("SOS certificate requires an inequality")
        mul = _integer(certificate["multiplier"], positive=True)
        c = _integer(certificate["constant"], nonnegative=True)
        squares = certificate["squares"]
        if not isinstance(squares, list) or len(squares) > 16:
            raise CertificateError("invalid SOS list")
        zero = (0,) * len(names)
        sos = {zero: c} if c else {}
        for entry in squares:
            if not isinstance(entry, dict) or set(entry) != {"weight", "polynomial"}:
                raise CertificateError("invalid square term")
            w = _integer(entry["weight"], positive=True)
            p = _load_coefficients(entry["polynomial"], len(names))
            sos = _plus(sos, _scale(_times(p, p), w))
        diff = _plus(lhs, rhs, -1) if relation == ">=" else _plus(rhs, lhs, -1)
        if _scale(diff, mul) != sos:
            raise CertificateError("SOS decomposition not equal to target polynomial")
        return True
    raise CertificateError("unknown certificate proof method")


def main() -> None:
    parser = argparse.ArgumentParser(description="Independent stdlib AXIOM proof certificate checker")
    parser.add_argument("artifact", type=Path, help="JSON object with statement and certificate fields")
    args = parser.parse_args()
    try:
        record = json.loads(args.artifact.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or set(record) != {"statement", "certificate"}:
            raise CertificateError("artifact must contain statement and certificate")
        check_certificate(record["statement"], record["certificate"])
    except (CertificateError, ValueError, TypeError, RecursionError) as err:
        parser.exit(1, f"REJECTED: {err}\n")
    print("ACCEPTED: independently checked supported polynomial certificate (NOT Lean formal verification)")


if __name__ == "__main__":
    main()
