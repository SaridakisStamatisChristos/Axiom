"""Exact finite falsification and two separate polynomial-normal-form procedures.

PROVED_IN_SUPPORTED_FRAGMENT is restricted to Z-polynomial equality; it is NOT
Lean/kernel formal verification. SymPy and a pure-Python sparse polynomial
expander must agree before a proof record can be returned.
"""
from __future__ import annotations

from itertools import product
from typing import Any
import sympy as sp
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


def polynomial_proof(statement: Statement) -> dict[str, Any] | None:
    if statement.relation != "==":
        return None
    names = tuple(sorted(statement.variables))
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
    if derived:
        return None
    return {"method": "integer_polynomial_coefficient_identity",
            "coefficient_difference": [], "quantifier_domain": "Z",
            "variables": list(names), "sympy_version": sp.__version__,
            "checks": ["pure_python_sparse_polynomial", "sympy_ZZ_Poly"],
            "claim_scope": "polynomial identity over all integers, subject to stated bounds"}


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


def falsify(statement: Statement, lower: int, upper: int, max_evals: int, seed: int) -> dict[str, Any]:
    if lower > upper or max_evals < 1 or max_evals > 1_000_000 or upper - lower > 100_000:
        raise ValueError("invalid search settings or excessive bounded range")
    bounds = {v: (lo, hi) for v, lo, hi in statement.bounds}
    if any(hi - lo > 100_000 for lo, hi in bounds.values()):
        raise ValueError("assumption range exceeds explicit v0.1 safety budget")
    grids = [_boundary_order(*bounds.get(v, (lower, upper)), seed + i) for i, v in enumerate(statement.variables)]
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
            # Independent witness validation evaluates the original AST again.
            lhs, rhs = _independent_tree_evaluation(statement.lhs, env), _independent_tree_evaluation(statement.rhs, env)
            valid = statement.assumption_holds(env) and {"==": lhs != rhs, ">=": lhs < rhs, "<=": lhs > rhs}[statement.relation]
            if not valid:
                raise ArithmeticError("CRITICAL: invalid counterexample")
            return {"counterexample": env, "lhs_value": lhs, "rhs_value": rhs,
                    "tested": checked, "search_space": possible, "exhaustive": False,
                    "method": "exact_boundary_first_enumeration", "seed": seed}
    return {"counterexample": None, "tested": checked, "search_space": possible,
            "exhaustive": checked == possible, "method": "exact_boundary_first_enumeration", "seed": seed}
