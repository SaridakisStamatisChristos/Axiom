"""Canonical integer-valued affine relations for compositional discovery."""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, lcm

from .graph_affine import AffineGraphConjecture, VARIABLES
from .graph_claims import digest


@dataclass(frozen=True)
class AffineRelation:
    bound: AffineGraphConjecture
    relation: str = "<="

    def __post_init__(self):
        if (type(self.bound) is not AffineGraphConjecture or type(self.relation) is not str
                or self.relation not in ("<=", "=")):
            raise ValueError("expected a typed affine inequality or equality")
        divisor = gcd(*(coefficient for _, coefficient in self.bound.terms))
        if divisor != 1 or (self.relation == "=" and self.bound.terms[0][1] < 0):
            raise ValueError("noncanonical integer affine relation")

    @classmethod
    def normalized(cls, weights, rhs, assumption="ALL", relation="<="):
        if (type(weights) is not dict or type(rhs) not in (int, Fraction)
                or any(type(name) is not str or name not in VARIABLES or
                       type(value) not in (int, Fraction) for name, value in weights.items())):
            raise ValueError("affine relations require exact rational coefficients")
        terms = sorted((name, Fraction(value)) for name, value in weights.items() if value)
        if not terms:
            raise ValueError("missing nonzero affine terms")
        scale = lcm(*(value.denominator for _, value in terms))
        integers = [(name, int(value * scale)) for name, value in terms]
        divisor = gcd(*(value for _, value in integers))
        threshold = Fraction(rhs) * scale / divisor
        if relation == "=" and threshold.denominator != 1:
            raise ValueError("integer affine equality has a nonintegral primitive bound")
        # The left side is integer-valued: dividing <= by a positive integer floors the RHS.
        sign = -1 if relation == "=" and integers[0][1] < 0 else 1
        return cls(AffineGraphConjecture(
            tuple((name, sign * coefficient // divisor) for name, coefficient in integers),
            sign * (threshold.numerator // threshold.denominator), assumption), relation)

    def to_dict(self):
        return {"relation": self.relation, "bound": self.bound.to_dict()}

    @classmethod
    def from_dict(cls, data):
        if type(data) is not dict or set(data) != {"relation", "bound"}:
            raise ValueError("invalid affine relation")
        return cls(AffineGraphConjecture.from_dict(data["bound"]), data["relation"])

    @property
    def id(self):
        return "graph-relation:" + digest(self.to_dict())

    def inequalities(self):
        if self.relation == "<=":
            return (self.bound,)
        opposite = AffineGraphConjecture.normalized(
            {name: -value for name, value in self.bound.terms},
            -self.bound.upper, self.bound.assumption)
        return self.bound, opposite


def _vector(terms):
    weights = dict(terms)
    return tuple(weights.get(name, 0) for name in VARIABLES)


# Every row is a universal implication under the listed antecedent. The
# empty graph is permitted, including in the unconditional bounds.
_FACTS = {
    "ALL": (
        ({"clique": 1, "chromatic": -1}, 0),
        ({"chromatic": 1, "maximum_degree": -1}, 1),
        ({"independence": 1, "clique": 1, "n": -1}, 1),
        ({"matching": 2, "n": -1}, 0),
        ({"matching": 1, "edges": -1}, 0),
        ({"maximum_degree": 1, "n": -1}, 0),
        ({"components": 1, "n": -1}, 0),
        *(({name: 1, "n": -1}, 0) for name in ("independence", "clique", "chromatic")),
    ),
    "CONNECTED": (({"components": 1}, 1), ({"n": 1, "edges": -1}, 1)),
    "BIPARTITE": (({"triangles": 1}, 0), ({"chromatic": 1}, 2),
                  ({"chromatic": 1, "clique": -1}, 0)),
    "TRIANGLE_FREE": (({"triangles": 1}, 0), ({"clique": 1}, 2)),
}


def _implies(terms, rhs, target, bound):
    # A nonnegative remainder can only decrease the target LHS. All graph
    # invariants here are nonnegative integers. Multipliers are exact.
    lower = Fraction(0)
    upper = None
    for source, goal in zip(terms, target):
        if source < 0:
            ratio = Fraction(goal, source)
            upper = ratio if upper is None else min(upper, ratio)
        elif source > 0:
            lower = max(lower, Fraction(goal, source))
        elif goal > 0:
            return False
    if rhs < 0:
        lower = max(lower, Fraction(bound, rhs))
    elif rhs > 0:
        ratio = Fraction(bound, rhs)
        upper = ratio if upper is None else min(upper, ratio)
    elif bound < 0:
        return False
    return upper is None or lower <= upper


def known_fact(claim):
    """Conservatively reject claims implied by a supported symbolic bound."""
    assumption = claim.bound.assumption
    facts = _FACTS["ALL"]
    if assumption != "ALL":
        facts += _FACTS[assumption]
    facts = (({}, 0), *facts)
    return all(any(_implies(_vector(source), rhs, _vector(side.terms), side.upper)
                   for source, rhs in facts)
               for side in claim.inequalities())


def implies(left, right):
    """Sound implication by an antecedent subsumption and bound scaling."""
    source = left.bound.assumption
    target = right.bound.assumption
    if source != target and source != "ALL" and (source, target) != ("TRIANGLE_FREE", "BIPARTITE"):
        return False
    return all(any(_implies(_vector(a.terms), a.upper, _vector(b.terms), b.upper)
                   for a in left.inequalities())
               for b in right.inequalities())
