"""Small, typed integer-polynomial AST with an independent exact evaluator.

All supported expressions denote total maps Z^n -> Z. No Python eval,
floating-point arithmetic, division, or implicit symbol creation is permitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json

VARIABLES = ("x", "y")
MAX_NODES = 128
MAX_POWER = 8


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple["Expr", ...] = ()
    value: int | str | None = None

    def __post_init__(self) -> None:
        if self.op == "const":
            if type(self.value) is not int or self.args:
                raise ValueError("constant must be an integer")
        elif self.op == "var":
            if self.value not in VARIABLES or self.args:
                raise ValueError("unknown variable")
        elif self.op in ("add", "sub", "mul"):
            if len(self.args) != 2 or self.value is not None or any(not isinstance(a, Expr) for a in self.args):
                raise ValueError("binary operator requires two expressions")
        elif self.op == "pow":
            if len(self.args) != 1 or not isinstance(self.args[0], Expr) or type(self.value) is not int or not 0 <= self.value <= MAX_POWER:
                raise ValueError("power must have an integer exponent between 0 and 8")
        else:
            raise ValueError(f"unsupported operation: {self.op}")

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.op, "value": self.value, "args": [a.to_dict() for a in self.args]}

    @classmethod
    def from_dict(cls, obj: dict[str, Any], depth: int = 0) -> "Expr":
        if not isinstance(obj, dict) or depth > MAX_NODES:
            raise ValueError("malformed expression")
        if set(obj) != {"op", "value", "args"} or not isinstance(obj["args"], list):
            raise ValueError("expression must have op, value, args")
        args = tuple(cls.from_dict(a, depth + 1) for a in obj["args"])
        return cls(obj["op"], args, obj["value"])

    def key(self) -> str:
        if self.op in ("add", "mul"):
            children = sorted(a.key() for a in self.args)
            return json.dumps([self.op, children], separators=(",", ":"))
        return json.dumps([self.op, self.value, [a.key() for a in self.args]], separators=(",", ":"))


def C(value: int) -> Expr:
    return Expr("const", value=value)


def V(name: str) -> Expr:
    return Expr("var", value=name)


def add(a: Expr, b: Expr) -> Expr:
    return Expr("add", (a, b))


def sub(a: Expr, b: Expr) -> Expr:
    return Expr("sub", (a, b))


def mul(a: Expr, b: Expr) -> Expr:
    return Expr("mul", (a, b))


def power(a: Expr, n: int) -> Expr:
    return Expr("pow", (a,), n)


def inspect(expr: Expr, limit: int = MAX_NODES) -> set[str]:
    count = 0
    names: set[str] = set()
    def walk(node: Expr) -> None:
        nonlocal count
        count += 1
        if count > limit:
            raise ValueError("expression exceeds node budget")
        if node.op == "var":
            names.add(str(node.value))
        for child in node.args:
            walk(child)
    walk(expr)
    return names


def evaluate(expr: Expr, environment: dict[str, int]) -> int:
    """Evaluate the original syntax tree, not the symbolic normal form."""
    if expr.op == "const":
        return int(expr.value)
    if expr.op == "var":
        val = environment[expr.value]
        if type(val) is not int:
            raise ValueError("variable assignment must be an exact integer")
        return val
    if expr.op == "pow":
        return evaluate(expr.args[0], environment) ** int(expr.value)
    a, b = (evaluate(x, environment) for x in expr.args)
    return {"add": lambda: a + b, "sub": lambda: a - b, "mul": lambda: a * b}[expr.op]()


@dataclass(frozen=True)
class Statement:
    lhs: Expr
    rhs: Expr
    relation: str
    variables: tuple[str, ...]
    bounds: tuple[tuple[str, int, int], ...] = ()

    def __post_init__(self) -> None:
        if self.relation not in ("==", ">=", "<="):
            raise ValueError("unsupported relation")
        if not self.variables or len(self.variables) != len(set(self.variables)) or any(v not in VARIABLES for v in self.variables):
            raise ValueError("invalid quantified variables")
        used = inspect(self.lhs) | inspect(self.rhs)
        if not used.issubset(self.variables):
            raise ValueError("unquantified variable")
        seen: set[str] = set()
        for v, lo, hi in self.bounds:
            if v not in self.variables or v in seen or type(lo) is not int or type(hi) is not int or lo > hi:
                raise ValueError("invalid bounds or contradictory assumptions")
            seen.add(v)

    def to_dict(self) -> dict[str, Any]:
        return {"lhs": self.lhs.to_dict(), "rhs": self.rhs.to_dict(), "relation": self.relation,
                "variables": list(self.variables), "bounds": [list(b) for b in self.bounds]}

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "Statement":
        if not isinstance(obj, dict) or set(obj) != {"lhs", "rhs", "relation", "variables", "bounds"}:
            raise ValueError("malformed statement")
        return cls(Expr.from_dict(obj["lhs"]), Expr.from_dict(obj["rhs"]), obj["relation"],
                   tuple(obj["variables"]), tuple(tuple(b) for b in obj["bounds"]))

    def canonical_key(self) -> str:
        sides = [self.lhs.key(), self.rhs.key()]
        if self.relation == "==":
            sides.sort()
        return json.dumps([self.relation, tuple(sorted(self.variables)), tuple(sorted(self.bounds)), sides],
                          separators=(",", ":"))

    def holds(self, env: dict[str, int]) -> bool:
        left, right = evaluate(self.lhs, env), evaluate(self.rhs, env)
        return {"==": left == right, ">=": left >= right, "<=": left <= right}[self.relation]

    def assumption_holds(self, env: dict[str, int]) -> bool:
        return all(lo <= env[v] <= hi for v, lo, hi in self.bounds)
