"""AXIOM v0.18 — exact, canonical, typed graph-invariant inequalities.

A statement is a *conjecture*, never a certificate. Normalization divides by a
positive common denominator and GCD; it NEVER reverses <= or changes any
logical assumption. Finite-order experiments do not verify a universal claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from functools import reduce
from math import gcd, lcm

from .graph_claims import digest, stable

SCHEMA = "axiom.graph.affine_conjecture.v1"


class GraphInvariant(StrEnum):
    ORDER = "n"
    EDGES = "edges"
    TRIANGLES = "triangles"
    INDEPENDENCE = "independence"
    CLIQUE = "clique"
    CHROMATIC = "chromatic"
    MAXIMUM_DEGREE = "maximum_degree"
    MATCHING = "matching"
    COMPONENTS = "components"


class GraphAssumption(StrEnum):
    ALL = "ALL"
    CONNECTED = "CONNECTED"
    BIPARTITE = "BIPARTITE"
    TRIANGLE_FREE = "TRIANGLE_FREE"


VARIABLES = tuple(invariant.value for invariant in GraphInvariant)
INVARIANTS = tuple(x for x in VARIABLES if x != "n")
ASSUMPTIONS = tuple(assumption.value for assumption in GraphAssumption)
MAX_COEFFICIENT = 8
MAX_BOUND = 256
ExactRational = int | Fraction


@dataclass(frozen=True)
class AffineExpression:
    """A sum of typed invariant terms and an exact rational constant."""

    terms: tuple[tuple[GraphInvariant, ExactRational], ...] = ()
    constant: ExactRational = 0

    def __post_init__(self) -> None:
        if type(self.constant) not in (int, Fraction):
            raise ValueError("affine constant must be an exact rational")
        if type(self.terms) is not tuple or any(
            type(term) is not tuple or len(term) != 2
            or type(term[0]) is not GraphInvariant
            or type(term[1]) not in (int, Fraction)
            for term in self.terms
        ):
            raise ValueError("affine terms require typed invariants and exact coefficients")

    @classmethod
    def invariant(cls, symbol: GraphInvariant) -> AffineExpression:
        return cls(((symbol, 1),))

    def __add__(self, other: AffineExpression, /) -> AffineExpression:
        if type(other) is not AffineExpression:
            return NotImplemented
        return AffineExpression(self.terms + other.terms, self.constant + other.constant)

    def __sub__(self, other: AffineExpression, /) -> AffineExpression:
        if type(other) is not AffineExpression:
            return NotImplemented
        return self + other.scaled(-1)

    def scaled(self, factor: ExactRational) -> AffineExpression:
        if type(factor) not in (int, Fraction):
            raise ValueError("affine scale must be an exact rational")
        return AffineExpression(
            tuple((symbol, factor * coefficient) for symbol, coefficient in self.terms),
            factor * self.constant,
        )


@dataclass(frozen=True)
class AffineGraphConjecture:
    """sum(coeff_i * integer_graph_invariant_i) <= upper, for all finite graphs."""
    terms: tuple[tuple[str, int], ...]
    upper: int
    assumption: str = "ALL"

    def __post_init__(self) -> None:
        if (type(self.terms) is not tuple or not 2 <= len(self.terms) <= 3
                or self.assumption not in ASSUMPTIONS
                or type(self.upper) is not int or abs(self.upper) > MAX_BOUND):
            raise ValueError("invalid affine statement arity/assumption/bound")
        names = []
        values = []
        for item in self.terms:
            if (type(item) is not tuple or len(item) != 2
                    or type(item[0]) is not str or item[0] not in VARIABLES
                    or type(item[1]) is not int or item[1] == 0
                    or abs(item[1]) > MAX_COEFFICIENT):
                raise ValueError("invalid graph invariant or exact coefficient")
            names.append(item[0])
            values.append(abs(item[1]))
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("affine terms must be sorted and unique")
        if sum(name != "n" for name in names) < 2:
            raise ValueError("require at least two graph observables")
        if reduce(gcd, values + [abs(self.upper)]) != 1:
            raise ValueError("affine statement has an unnormalized common factor")

    @classmethod
    def from_expressions(
        cls, lhs: AffineExpression, rhs: AffineExpression, *,
        assumption: GraphAssumption = GraphAssumption.ALL,
    ) -> AffineGraphConjecture:
        """Build a canonical universal statement of the form lhs <= rhs."""
        if type(lhs) is not AffineExpression or type(rhs) is not AffineExpression:
            raise ValueError("affine statement requires two affine expressions")
        if type(assumption) is not GraphAssumption:
            raise ValueError("affine statement requires a typed graph assumption")
        difference = lhs - rhs
        weights: dict[str, ExactRational] = {}
        for symbol, coefficient in difference.terms:
            weights[symbol.value] = weights.get(symbol.value, 0) + coefficient
        return cls.normalized(weights, -difference.constant, assumption.value)

    @classmethod
    def normalized(cls, weights: dict[str, int | Fraction],
                   upper: int | Fraction, assumption: str = "ALL"):
        if type(weights) is not dict or not weights:
            raise ValueError("missing affine weights")
        if assumption not in ASSUMPTIONS:
            raise ValueError("unknown graph assumption")
        if any(type(key) is not str or key not in VARIABLES for key in weights):
            raise ValueError("unsupported graph observable")
        if any(type(value) not in (int, Fraction) for value in weights.values()):
            raise ValueError("affine coefficients must be exact rationals")
        if type(upper) not in (int, Fraction):
            raise ValueError("affine upper bound must be exact")
        fractions = [Fraction(value) for value in weights.values()] + [Fraction(upper)]
        denominator = lcm(*(fraction.denominator for fraction in fractions))
        pairs = [(key, int(Fraction(value) * denominator))
                 for key, value in weights.items() if value != 0]
        rhs = int(Fraction(upper) * denominator)
        divisor = reduce(gcd, [abs(value) for _, value in pairs] + [abs(rhs)])
        if divisor < 1:
            raise ValueError("identically zero statement is uninformative")
        return cls(tuple(sorted((key, value // divisor) for key, value in pairs)),
                   rhs // divisor, assumption)

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "quantifier": "forall_finite_simple_graphs_all_orders",
            "assumption": self.assumption,
            "lhs": [{"symbol": symbol, "numerator": coefficient, "denominator": 1}
                    for symbol, coefficient in self.terms],
            "relation": "<=",
            "rhs": {"numerator": self.upper, "denominator": 1},
            "mathematical_novelty": "NOT_ASSESSED",
        }

    @classmethod
    def from_dict(cls, data: dict):
        if type(data) is not dict or set(data) != {
            "schema", "quantifier", "assumption", "lhs", "relation", "rhs",
            "mathematical_novelty",
        }:
            raise ValueError("wrong affine conjecture serialization")
        if type(data["lhs"]) is not list or any(
            type(t) is not dict or set(t) != {
                "symbol", "numerator", "denominator",
            } or type(t["numerator"]) is not int or
            type(t["denominator"]) is not int or t["denominator"] != 1
            for t in data["lhs"]
        ):
            raise ValueError("malformed affine coefficients")
        bound = data["rhs"]
        if (type(bound) is not dict or set(bound) != {
            "numerator", "denominator",
        } or type(bound["numerator"]) is not int or
                type(bound["denominator"]) is not int or bound["denominator"] != 1):
            raise ValueError("malformed affine constant")
        stmt = cls(tuple((term["symbol"], term["numerator"])
                         for term in data["lhs"]), bound["numerator"],
                   data["assumption"])
        if stable(stmt.to_dict()) != stable(data):
            raise ValueError("noncanonical or changed graph conjecture")
        return stmt

    @property
    def id(self) -> str:
        return "affine-graph:" + digest(self.to_dict())


def applicable(assumption: str, graph: dict) -> bool:
    if assumption not in ASSUMPTIONS:
        raise ValueError("unsupported graph assumption")
    if assumption == "ALL":
        return True
    key = {"CONNECTED": "connected", "BIPARTITE": "bipartite",
           "TRIANGLE_FREE": "triangle_free"}[assumption]
    if type(graph.get(key)) is not bool:
        raise ValueError("graph missing typed assumption")
    return graph[key]


def check_conjecture(statement: AffineGraphConjecture, properties: dict
                     ) -> tuple[bool, bool, int]:
    if type(properties) is not dict or type(properties.get("n")) is not int:
        raise ValueError("invalid graph property input")
    left = 0
    for symbol, weight in statement.terms:
        observed = properties.get(symbol)
        if type(observed) is not int or observed < 0:
            raise ValueError("graph invariant must be a nonnegative integer")
        left += weight * observed
    return (applicable(statement.assumption, properties),
            left <= statement.upper, left)
