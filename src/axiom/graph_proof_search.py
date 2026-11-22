"""Deterministic bounded search for exact nonnegative integer combinations."""
from dataclasses import dataclass

from .graph_relations import AffineRelation, _vector


@dataclass(frozen=True)
class LemmaSpec:
    theorem: str
    premise: str
    vector: tuple[int, ...]
    rhs: int


@dataclass(frozen=True)
class SearchLimits:
    max_lemmas: int = 3
    max_coefficient: int = 3
    max_nodes: int = 10_000

    def __post_init__(self):
        for value, limit in ((self.max_lemmas, 7), (self.max_coefficient, 32),
                             (self.max_nodes, 1_000_000)):
            if type(value) is not int or not 1 <= value <= limit:
                raise ValueError("invalid proof search budget")


def search(claim: AffineRelation, bank: tuple[LemmaSpec, ...], limits: SearchLimits, *,
           integer_rounding=False) -> dict:
    """Return each direction's shortest certificate and a shared node count.

    A node budget, rather than a wall-clock cutoff, makes truncation replayable.
    Bounds allow opposite signs to cancel and only prune impossible residuals.
    """
    usable = tuple(sorted(
        (lemma for lemma in bank if lemma.premise in ("ALL", claim.bound.assumption)),
        key=lambda lemma: lemma.theorem))
    cap = limits.max_coefficient
    total_nodes = 0
    truncated = False
    scales = range(1, cap + 1) if integer_rounding else (1,)
    directions = []

    for side in claim.inequalities():
        target = _vector(side.terms)
        failed = set()

        def visit(start, slots, residual, slack):
            nonlocal total_nodes, truncated
            if total_nodes == limits.max_nodes:
                truncated = True
                return None
            total_nodes += 1
            if slots == 0:
                return () if not any(residual) and slack >= 0 else None
            state = (start, slots, residual, slack)
            if state in failed or len(usable) - start < slots:
                return None
            suffix = usable[start:]
            for coordinate, required in enumerate(residual):
                values = [lemma.vector[coordinate] for lemma in suffix]
                if not (min(0, min(values)) * cap * slots <= required
                        <= max(0, max(values)) * cap * slots):
                    failed.add(state)
                    return None
            for index in range(start, len(usable) - slots + 1):
                lemma = usable[index]
                for coefficient in range(1, cap + 1):
                    remaining = tuple(x - coefficient * y for x, y in zip(residual, lemma.vector))
                    proof = visit(index + 1, slots - 1, remaining, slack - coefficient * lemma.rhs)
                    if proof is not None:
                        return ((lemma, coefficient), *proof)
                    if truncated:
                        return None
            failed.add(state)
            return None

        proof, target_scale = None, 1
        for size in range(1, min(limits.max_lemmas, len(usable)) + 1):
            for target_scale in scales:
                scaled = tuple(target_scale * value for value in target)
                # Integer LHS: scaled lhs < scale * (upper + 1) implies lhs ≤ upper.
                slack = target_scale * (side.upper + 1) - 1
                proof = visit(0, size, scaled, slack)
                if proof is not None or truncated:
                    break
            if proof is not None or truncated:
                break
        directions.append({
            "target_vector": list(target), "target_rhs": side.upper,
            "lemmas": [{"theorem": lemma.theorem, "premise": lemma.premise,
                        "vector": list(lemma.vector), "rhs": lemma.rhs, "coefficient": value}
                       for lemma, value in proof] if proof is not None else None,
            "combined_rhs": sum(lemma.rhs * value for lemma, value in proof)
            if proof is not None else None,
            **({"target_scale": target_scale} if proof is not None and target_scale > 1 else {}),
        })
        if truncated:
            break
    return {"directions": directions, "nodes": total_nodes, "node_budget_exhausted": truncated,
            "derived": len(directions) == len(claim.inequalities())
            and all(direction["lemmas"] is not None for direction in directions)}
