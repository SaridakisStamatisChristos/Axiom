"""Typed universal integer divisibility and positive-modulus congruence statements.

Semantics: a | b iff there exists k in Z with b=a*k. Thus 0|0 is true
and 0|b (b != 0) is false. a ≡ b (mod m) is defined only when m>0,
and means m | (a-b). Explicit integer bounds are logical assumptions.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json
from .mathematics import Expr, inspect, VARIABLES, evaluate


@dataclass(frozen=True)
class NTStatement:
    lhs: Expr
    rhs: Expr
    relation: str
    variables: tuple[str, ...]
    modulus: int | None = None
    bounds: tuple[tuple[str, int, int], ...] = ()

    def __post_init__(self) -> None:
        if self.relation not in ('divides', 'congruent'):
            raise ValueError('unknown integer relation')
        if self.relation == 'divides':
            if self.modulus is not None:
                raise ValueError('divisibility has no separate modulus')
        elif type(self.modulus) is not int or not 1 <= self.modulus <= 2**31:
            raise ValueError('modulus must be a strictly positive bounded integer')
        if (not 1 <= len(self.variables) <= 2 or
                len(set(self.variables)) != len(self.variables) or
                any(type(n) is not str or n not in VARIABLES for n in self.variables)):
            raise ValueError('invalid quantified integer variable list')
        if not (inspect(self.lhs) | inspect(self.rhs)).issubset(self.variables):
            raise ValueError('unquantified variable in expression')
        seen: set[str] = set()
        for entry in self.bounds:
            if (not isinstance(entry, (list, tuple)) or len(entry) != 3):
                raise ValueError('invalid bound shape')
            name, lo, hi = entry
            if (type(name) is not str or name not in self.variables or name in seen or
                    type(lo) is not int or type(hi) is not int or lo > hi):
                raise ValueError('invalid or contradictory integer bounds')
            seen.add(name)

    def to_dict(self) -> dict[str, Any]:
        return {'lhs': self.lhs.to_dict(), 'rhs': self.rhs.to_dict(),
                'relation': self.relation, 'variables': list(self.variables),
                'modulus': self.modulus, 'bounds': [list(e) for e in self.bounds]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'NTStatement':
        if (not isinstance(data, dict) or
                set(data) != {'lhs', 'rhs', 'relation', 'variables', 'modulus', 'bounds'} or
                type(data['variables']) is not list or type(data['bounds']) is not list):
            raise ValueError('invalid number-theory statement schema')
        return cls(Expr.from_dict(data['lhs']), Expr.from_dict(data['rhs']),
                   data['relation'], tuple(data['variables']), data['modulus'],
                   tuple(tuple(b) for b in data['bounds']))

    def canonical_key(self) -> str:
        lhs, rhs = self.lhs.key(), self.rhs.key()
        if self.relation == 'congruent' and lhs > rhs:
            lhs, rhs = rhs, lhs
        return json.dumps([self.relation, self.modulus, sorted(self.variables),
                           sorted(self.bounds), lhs, rhs], separators=(',', ':'))

    def assumption_holds(self, env: dict[str, int]) -> bool:
        return all(lo <= env[n] <= hi for n, lo, hi in self.bounds)

    def holds(self, env: dict[str, int]) -> bool:
        if not self.assumption_holds(env):
            raise ValueError('assignment violates assumptions')
        a, b = evaluate(self.lhs, env), evaluate(self.rhs, env)
        if self.relation == 'congruent':
            return (a - b) % self.modulus == 0
        return (b == 0 if a == 0 else b % a == 0)
