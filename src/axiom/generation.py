"""Deterministic finite-grammar candidate generator (no benchmarks mixed in)."""
from __future__ import annotations
import random
from .mathematics import Statement, C, V, add, mul, sub, power


def generate(seed: int, budget: int, domain: str = "polynomial") -> list[tuple[str, Statement]]:
    if budget < 1 or budget > 100_000:
        raise ValueError("candidate budget must be in [1, 100000]")
    if domain not in ("polynomial", "mixed"):
        raise ValueError("unknown research domain")
    rng = random.Random(seed)
    x, y = V("x"), V("y")
    out: list[tuple[str, Statement]] = []
    for i in range(budget):
        k = rng.choice([v for v in range(-6, 7) if v])
        c = rng.choice([v for v in range(-5, 6) if v])
        mutation = rng.choice((0, 0, 1, -1, 2))
        template = i % (7 if domain == "mixed" else 4)
        if template == 0:
            lhs = power(add(x, C(k)), 2)
            rhs = add(add(power(x, 2), mul(C(2 * k), x)), C(k * k + mutation))
            statement = Statement(lhs, rhs, "==", ("x",))
            label = "square_expansion"
        elif template == 1:
            lhs = mul(add(x, C(k)), add(y, C(c)))
            rhs = add(add(add(mul(x, y), mul(C(c), x)), mul(C(k), y)), C(k * c + mutation))
            statement = Statement(lhs, rhs, "==", ("x", "y"))
            label = "distributivity"
        elif template == 2:
            lhs = power(add(x, C(k)), 3)
            rhs = add(add(add(power(x, 3), mul(C(3 * k), power(x, 2))), mul(C(3 * k * k), x)), C(k ** 3 + mutation))
            statement = Statement(lhs, rhs, "==", ("x",))
            label = "cubic_expansion"
        elif template == 3:
            lhs = mul(add(x, C(k)), sub(x, C(k)))
            rhs = add(sub(power(x, 2), C(k * k)), C(mutation))
            statement = Statement(lhs, rhs, "==", ("x",))
            label = "difference_of_squares"
        elif template == 4:
            lhs = add(power(x, 2), C(mutation))
            rhs = C(0)
            statement = Statement(lhs, rhs, ">=", ("x",))
            label = "quadratic_nonnegativity"
        elif template == 5:
            lhs = add(add(power(sub(x, C(k)), 2),
                          power(add(y, C(c)), 2)), C(mutation))
            statement = Statement(lhs, C(0), ">=", ("x", "y"))
            label = "multivariate_sum_of_squares"
        else:
            # True under explicit bounds, false outside them: deliberately no
            # universal SOS proof; finite testing cannot be promoted to proof.
            lhs = mul(x, sub(C(8), x))
            statement = Statement(lhs, C(0), ">=", ("x",), (("x", 0, 8),))
            label = "finite_interval_inequality"
        out.append((label, statement))
    return out
