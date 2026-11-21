"""One-step affine projection with deterministic proof ancestry."""
from dataclasses import asdict, dataclass
from itertools import combinations
from math import gcd

from .graph_affine import VARIABLES
from .graph_claims import digest
from .graph_proof_search import LemmaSpec
from .graph_relations import AffineRelation, _vector

SYNTHESIS_VERSION = "axiom.graph_affine_projection.v1"
MAX_SYNTHESIZED_LEMMAS = 32


@dataclass(frozen=True)
class Projection:
    lemma: LemmaSpec
    parents: tuple[tuple[LemmaSpec, int], ...]
    pivot: str
    divisor: int

    def evidence(self):
        return {
            "lemma": asdict(self.lemma),
            "parents": [{"lemma": asdict(lemma), "coefficient": scale}
                        for lemma, scale in self.parents],
            "pivot": self.pivot,
            "divisor": self.divisor,
        }


def synthesize(claim: AffineRelation, bank: tuple[LemmaSpec, ...], limit: int) -> tuple[Projection, ...]:
    """Eliminate one oppositely signed variable from pairs of applicable lemmas.

    Primitive normalization floors the right-hand side because all graph
    invariants are integer valued, including when the combined bound is negative.
    """
    applicable = sorted((lemma for lemma in bank if lemma.premise in ("ALL", claim.bound.assumption)),
                        key=lambda lemma: lemma.theorem)
    known = {}
    for lemma in applicable:
        known[lemma.vector] = min(known.get(lemma.vector, lemma.rhs), lemma.rhs)

    projections = {}
    for left, right in combinations(applicable, 2):
        for index, (a, b) in enumerate(zip(left.vector, right.vector)):
            if a * b >= 0:
                continue
            common = gcd(a, b)
            p, q = abs(b) // common, abs(a) // common
            summed = tuple(p * x + q * y for x, y in zip(left.vector, right.vector))
            divisor = gcd(*summed)
            if not divisor:
                continue
            vector = tuple(value // divisor for value in summed)
            rhs = (p * left.rhs + q * right.rhs) // divisor
            if vector in known and known[vector] <= rhs:
                continue
            previous = projections.get(vector)
            if previous is not None and previous.lemma.rhs <= rhs:
                continue
            premise = right.premise if left.premise == "ALL" else left.premise
            pivot = VARIABLES[index]
            key = [SYNTHESIS_VERSION, asdict(left), p, asdict(right), q, pivot, divisor]
            name = "synthesized_" + digest(key)[:24]
            projections[vector] = Projection(LemmaSpec(name, premise, vector, rhs),
                                             ((left, p), (right, q)), pivot, divisor)

    targets = [_vector(side.terms) for side in claim.inequalities()]

    def rank(item):
        vector = item.lemma.vector
        overlap = max(sum(a * b > 0 for a, b in zip(vector, target)) for target in targets)
        return (vector not in targets, -overlap, sum(x != 0 for x in vector),
                item.lemma.theorem)

    return tuple(sorted(projections.values(), key=rank)[:limit])
