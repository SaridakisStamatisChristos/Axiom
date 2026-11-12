"""Exact finite falsification and two separate polynomial-normal-form procedures.

PROVED_IN_SUPPORTED_FRAGMENT is restricted to Z-polynomial equality; it is NOT
Lean/kernel formal verification. SymPy and a pure-Python sparse polynomial
expander must agree before a proof record can be returned.
"""
from __future__ import annotations

from itertools import product
from typing import Any
import sympy as sp
from .certificate_checker import (SCHEMA, CertificateError, check_certificate,
                                  check_supported_statement, statement_digest)
from .mathematics import Expr, Statement


def _sparse(expr: Expr, variables: tuple[str, ...]) -> dict[tuple[int, ...], int]:
    zero = (0,) * len(variables)
    if expr.op == "const":
        return {zero: int(expr.value)} if expr.value else {}
    if expr.op == "var":
        p = list(zero)
        p[variables.index(expr.value)] = 1
        return {tuple(p): 1}
    if expr.op == "pow":
        result = {zero: 1}
        base = _sparse(expr.args[0], variables)
        for _ in range(int(expr.value)):
            result = _mul(result, base)
        return result
    left, right = (_sparse(e, variables) for e in expr.args)
    if expr.op == "mul":
        return _mul(left, right)
    result = dict(left)
    sign = 1 if expr.op == "add" else -1
    for k, v in right.items():
        result[k] = result.get(k, 0) + sign * v
    return {k: v for k, v in result.items() if v}


def _mul(a: dict[tuple[int, ...], int], b: dict[tuple[int, ...], int]) -> dict[tuple[int, ...], int]:
    out: dict[tuple[int, ...], int] = {}
    for ka, va in a.items():
        for kb, vb in b.items():
            k = tuple(x + y for x, y in zip(ka, kb))
            out[k] = out.get(k, 0) + va * vb
    return {k: v for k, v in out.items() if v}


def _sympy(expr: Expr, symbols: dict[str, Any]) -> Any:
    if expr.op == "const":
        return sp.Integer(expr.value)
    if expr.op == "var":
        return symbols[expr.value]
    if expr.op == "pow":
        return _sympy(expr.args[0], symbols) ** int(expr.value)
    a, b = (_sympy(e, symbols) for e in expr.args)
    return {"add": lambda: a + b, "sub": lambda: a - b, "mul": lambda: a * b}[expr.op]()


def _coefficient_difference(statement: Statement) -> tuple[dict, dict, tuple[str, ...]]:
    """Symbolic candidate normalization; independent checker runs separately."""
    check_supported_statement(statement.to_dict())
    names = tuple(statement.variables)
    sparse_l = _sparse(statement.lhs, names)
    sparse_r = _sparse(statement.rhs, names)
    syms = {name: sp.Symbol(name, integer=True) for name in names}
    diff = sp.Poly(_sympy(statement.lhs, syms) - _sympy(statement.rhs, syms),
                   *(syms[name] for name in names), domain=sp.ZZ)
    independent = {tuple(m): int(c) for m, c in diff.terms() if c != 0}
    derived = dict(sparse_l)
    for k, v in sparse_r.items():
        derived[k] = derived.get(k, 0) - v
    derived = {k: v for k, v in derived.items() if v}
    if independent != derived:
        raise ArithmeticError("CRITICAL: independent polynomial normalizers disagree")
    return sparse_l, sparse_r, names


def _encoded(poly: dict) -> list:
    return [[list(m), c] for m, c in sorted(poly.items()) if c]


def _proof_record(statement: Statement, method: str, payload: dict) -> dict[str, Any]:
    artifact = {"schema": SCHEMA, "statement_sha256": statement_digest(statement.to_dict()),
                "variables": list(statement.variables), "method": method, **payload}
    # The separately importable checker derives coefficients from the original AST.
    if check_certificate(statement.to_dict(), artifact) is not True:
        raise ArithmeticError("CRITICAL: candidate certificate not independently accepted")
    return {"method": method, "certificate": artifact,
            "checker": {"name": "axiom.certificate_checker", "accepted": True,
                        "trust": "standalone_python_integer_polynomial_checker_not_Lean"},
            "coefficient_difference": [], "checks": ["pure_python_sparse_polynomial",
                                                     "sympy_ZZ_Poly", "standalone_certificate_checker"],
            "claim_scope": "universal integer-polynomial identity or certified SOS inequality",
            "sympy_version": sp.__version__}


def polynomial_proof(statement: Statement) -> dict[str, Any] | None:
    if statement.relation != "==":
        return None
    try:
        sparse_l, sparse_r, _ = _coefficient_difference(statement)
    except CertificateError:
        return None
    if sparse_l != sparse_r:
        return None
    return _proof_record(statement, "coefficient_identity", {
        "lhs_coefficients": _encoded(sparse_l), "rhs_coefficients": _encoded(sparse_r)})


def inequality_proof(statement: Statement) -> dict[str, Any] | None:
    """Sound complete-the-square SOS for separable quadratic inequalities.

    Proves M * target = sum_i w_i(2*a_i*x_i+b_i)^2 + R,
    with M,w_i positive integers and R a nonnegative integer.  This is a
    deliberately restricted proof search, not a general inequality solver.
    """
    if statement.relation not in (">=", "<="):
        return None
    try:
        left, right, names = _coefficient_difference(statement)
    except CertificateError:
        return None
    target = dict(left if statement.relation == ">=" else right)
    subtract = right if statement.relation == ">=" else left
    for powers, value in subtract.items():
        target[powers] = target.get(powers, 0) - value
    target = {k: v for k, v in target.items() if v}
    zero = (0,) * len(names)
    constant = target.get(zero, 0)
    square_data: list[tuple[int, int, int]] = []
    for i in range(len(names)):
        exp1 = tuple(1 if j == i else 0 for j in range(len(names)))
        exp2 = tuple(2 if j == i else 0 for j in range(len(names)))
        a, b = target.get(exp2, 0), target.get(exp1, 0)
        if a < 0 or (a == 0 and b != 0):
            return None
        if a:
            square_data.append((i, a, b))
    allowed = {zero}
    for i in range(len(names)):
        allowed.add(tuple(1 if j == i else 0 for j in range(len(names))))
        allowed.add(tuple(2 if j == i else 0 for j in range(len(names))))
    if any(k not in allowed for k in target):
        return None
    multiplier = 4
    for _, a, _ in square_data:
        multiplier *= a
    if not square_data:
        multiplier = 1
    squares = []
    remainder = multiplier * constant
    for i, a, b in square_data:
        weight = multiplier // (4 * a)
        remainder -= weight * b * b
        first = tuple(1 if j == i else 0 for j in range(len(names)))
        polynomial = {first: 2 * a}
        if b:
            polynomial[zero] = b
        squares.append({"weight": weight, "polynomial": _encoded(polynomial)})
    if remainder < 0:
        return None
    return _proof_record(statement, "sum_of_squares", {
        "multiplier": multiplier, "squares": squares, "constant": remainder})


def proof_search(statement: Statement) -> dict[str, Any] | None:
    """Dispatch only to sound supported proof strategies."""
    return polynomial_proof(statement) if statement.relation == "==" else inequality_proof(statement)


def _boundary_order(lo: int, hi: int, seed: int) -> list[int]:
    # Deterministic boundary-first order; seed cyclically rotates the non-boundary tail.
    front = [v for v in (0, 1, -1, lo, hi, lo + 1, hi - 1) if lo <= v <= hi]
    front = list(dict.fromkeys(front))
    others = [v for v in range(lo, hi + 1) if v not in front]
    if others:
        shift = seed % len(others)
        others = others[shift:] + others[:shift]
    return front + others


def _independent_tree_evaluation(root: Expr, env: dict[str, int]) -> int:
    """Iterative stack evaluator for validating a witness without using evaluate()."""
    pending = [(root, False)]
    values: list[int] = []
    while pending:
        node, ready = pending.pop()
        if not ready:
            pending.append((node, True))
            for child in reversed(node.args):
                pending.append((child, False))
            continue
        if node.op == "const":
            values.append(int(node.value))
        elif node.op == "var":
            values.append(env[node.value])
        elif node.op == "pow":
            values.append(values.pop() ** int(node.value))
        else:
            right = values.pop()
            left = values.pop()
            if node.op == "add":
                values.append(left + right)
            elif node.op == "sub":
                values.append(left - right)
            elif node.op == "mul":
                values.append(left * right)
            else:
                raise ValueError("unknown operator")
    if len(values) != 1:
        raise AssertionError("invalid expression evaluation stack")
    return values[0]


def _witness_is_valid(statement: Statement, env: dict[str, int]) -> tuple[int, int] | None:
    if not statement.assumption_holds(env):
        return None
    lhs = _independent_tree_evaluation(statement.lhs, env)
    rhs = _independent_tree_evaluation(statement.rhs, env)
    false = ((lhs != rhs) if statement.relation == "==" else
             (lhs < rhs) if statement.relation == ">=" else lhs > rhs)
    return (lhs, rhs) if false else None


def _minimize_witness(statement: Statement, initial: dict[str, int], limits: dict[str, tuple[int, int]],
                      budget: int = 64) -> tuple[dict[str, int], int]:
    """Deterministic bounded coordinate descent; does NOT claim global minimality."""
    names = tuple(statement.variables)
    current = dict(initial)
    calls = 0

    def rank(env: dict[str, int]) -> tuple:
        values = [env[v] for v in names]
        return sum(map(abs, values)), max(map(abs, values)), tuple(map(abs, values)), tuple(values)

    improved = True
    while improved and calls < budget:
        improved = False
        for v in names:
            if calls >= budget:
                break
            lo, hi = limits[v]
            val = current[v]
            tests = [0, 1, -1, lo, hi, val // 2, -(abs(val) // 2), (abs(val) // 2)]
            if abs(val) <= 32:
                tests.extend(range(max(lo, -32), min(hi, 32) + 1))
            candidates = sorted({x for x in tests if lo <= x <= hi}, key=lambda x: (abs(x), x))
            for attempt in candidates:
                if calls >= budget:
                    break
                modified = dict(current)
                modified[v] = attempt
                if rank(modified) >= rank(current):
                    continue
                calls += 1
                if _witness_is_valid(statement, modified) is not None:
                    current = modified
                    improved = True
    return current, calls


def falsify(statement: Statement, lower: int, upper: int, max_evals: int, seed: int) -> dict[str, Any]:
    if lower > upper or max_evals < 1 or max_evals > 1_000_000 or upper - lower > 100_000:
        raise ValueError("invalid search settings or excessive bounded range")
    bounds = {v: (lo, hi) for v, lo, hi in statement.bounds}
    if any(hi - lo > 100_000 for lo, hi in bounds.values()):
        raise ValueError("assumption range exceeds explicit safety budget")
    # A search window is an additional search restriction, not an assumption.
    limits = {v: (max(lower, bounds.get(v, (lower, upper))[0]),
                  min(upper, bounds.get(v, (lower, upper))[1])) for v in statement.variables}
    if any(lo > hi for lo, hi in limits.values()):
        return {"counterexample": None, "tested": 0, "search_space": 0,
                "exhaustive": True, "method": "exact_boundary_first_enumeration", "seed": seed,
                "search_bounds": limits}
    grids = [_boundary_order(*limits[v], seed + i) for i, v in enumerate(statement.variables)]
    possible = 1
    for g in grids:
        possible *= len(g)
    checked = 0
    for values in product(*grids):
        if checked == max_evals:
            break
        env = dict(zip(statement.variables, values))
        if not statement.assumption_holds(env):
            raise AssertionError("enumerator emitted a forbidden witness")
        checked += 1
        if not statement.holds(env):
            # Validate against a separate iterative evaluator before changing status.
            pair = _witness_is_valid(statement, env)
            if pair is None:
                raise ArithmeticError("CRITICAL: invalid counterexample")
            minimized, calls = _minimize_witness(statement, env, limits)
            minimized_pair = _witness_is_valid(statement, minimized)
            if minimized_pair is None:
                raise ArithmeticError("CRITICAL: minimized witness invalid")
            return {"counterexample": minimized, "lhs_value": minimized_pair[0],
                    "rhs_value": minimized_pair[1], "original_counterexample": env,
                    "minimization": {"method": "bounded_coordinate_descent",
                                     "probes": calls, "globally_minimal": False},
                    "tested": checked, "search_space": possible, "exhaustive": False,
                    "method": "exact_boundary_first_enumeration", "seed": seed,
                    "search_bounds": limits}
    return {"counterexample": None, "tested": checked, "search_space": possible,
            "exhaustive": checked == possible,
            "method": "exact_boundary_first_enumeration", "seed": seed,
            "search_bounds": limits}
