"""Training-only four-term candidates for the opt-in proof experiment."""
from itertools import combinations, product

from .graph_affine import ASSUMPTIONS, MAX_BOUND, VARIABLES, applicable
from .graph_proof import BANK
from .graph_proof_search import SearchLimits, search
from .graph_relations import AffineRelation, known_fact

KNOWN_QUEUE = "KNOWN_OR_DERIVABLE_PROOF_TARGET"
OPEN_QUEUE = "OPEN_PROOF_TARGET"


def _rank(vector, groups):
    maxima = []
    minimum = MAX_BOUND + 1
    for group in groups:
        values = [sum(weight * value for weight, value in zip(vector, row)) for row in group]
        maxima.append(max(values))
        minimum = min(minimum, min(values))
    high = max(maxima)
    return high, (minimum == high, maxima.count(high), high - minimum)


def _weights(vector):
    return {name: value for name, value in zip(VARIABLES, vector) if value}


def candidate_beam(training, width, *, novelty=None):
    """Rank training-only bounds; also retain certified proof opportunities.

    Beam width limits retained expressions at every depth, per premise.
    Rule sums are an explicitly tagged, target-independent opportunity lane.
    """
    known, opened = {}, {}
    counts = {"training_expressions_evaluated": 0, "certified_expressions_evaluated": 0,
              "states_pruned_by_beam_width": 0}
    for assumption in ASSUMPTIONS:
        groups = [[tuple(row[name] for name in VARIABLES) for row in training[n]
                   if applicable(assumption, row)] for n in (5, 6, 7)]
        if not all(groups):
            continue

        previous = {(0,) * len(VARIABLES)}
        for depth in range(1, 5):
            vectors = set()
            for state in previous:
                for index, value in product(range(len(VARIABLES)), (-2, -1, 1, 2)):
                    if not state[index]:
                        vectors.add(state[:index] + (value,) + state[index + 1:])
            measured = [(vector, *_rank(vector, groups)) for vector in sorted(vectors)]
            counts["training_expressions_evaluated"] += len(measured)
            ranked = sorted(measured, key=lambda row: (row[2], row[0]), reverse=True)
            counts["states_pruned_by_beam_width"] += max(0, len(ranked) - width)
            ranked = ranked[:width]
            previous = {vector for vector, _, _ in ranked}
            if depth < 3:
                continue
            for vector, high, score in ranked:
                if abs(high) > MAX_BOUND or score[1] < 2:
                    continue
                claim = AffineRelation.normalized(_weights(vector), high, assumption,
                                                  "=" if score[0] else "<=")
                derivable = search(claim, BANK, SearchLimits())["derived"]
                legacy_known = derivable or known_fact(claim)
                if novelty is None:
                    (known if legacy_known else opened)[claim] = score
                elif novelty.classify(claim):
                    if legacy_known:
                        known[claim] = score
                    else:
                        counts["certified_known_implications"] = counts.get("certified_known_implications", 0) + 1
                else:
                    opened[claim] = score

        usable = [lemma for lemma in BANK if lemma.premise in ("ALL", assumption)]
        for left, right in combinations(usable, 2):
            if assumption != "ALL" and assumption not in (left.premise, right.premise):
                continue
            vector = tuple(a + b for a, b in zip(left.vector, right.vector))
            weights = _weights(vector)
            if not 3 <= len(weights) <= 4:
                continue
            counts["certified_expressions_evaluated"] += 1
            high, score = _rank(vector, groups)
            limit = left.rhs + right.rhs
            if high > limit:
                raise ValueError("certified inequality conflicts with the training oracles")
            claim = AffineRelation.normalized(weights, limit, assumption)
            if search(claim, BANK, SearchLimits())["derived"]:
                known[claim] = (False, score[1], score[2])

    def ordered(bank):
        return sorted(bank.items(), key=lambda entry: (entry[1], entry[0].id), reverse=True)

    return {KNOWN_QUEUE: ordered(known), OPEN_QUEUE: ordered(opened)}, counts
