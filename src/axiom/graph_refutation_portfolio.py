"""Small graph families for deterministic counterexample search."""
from itertools import combinations

from .graph_explicit import ExplicitGraph


def _union(parts):
    n = 0
    edges = []
    for part in parts:
        edges.extend((n + a, n + b) for a, b in part.edges)
        n += part.n
    return ExplicitGraph(n, tuple(edges))


def _complete(n):
    return ExplicitGraph(n, tuple(combinations(range(n), 2)))


def _multipartite(n, parts):
    return ExplicitGraph(n, tuple((a, b) for a, b in combinations(range(n), 2)
                                  if a * parts // n != b * parts // n))


def _circulant(n, distances):
    return ExplicitGraph(n, tuple((a, b) for a, b in combinations(range(n), 2)
                                  if min(b - a, n - b + a) in distances))


def structured_graphs(max_order, premise):
    """Interleave orders and constructions independently of the coefficients."""
    if premise != "CONNECTED":
        yield "empty", ExplicitGraph(0, ())
    yield "singleton", ExplicitGraph(1, ())
    for n in range(2, max_order + 1):
        if premise in ("ALL", "CONNECTED"):
            yield "complete", _complete(n)
        if premise != "CONNECTED":
            yield "edgeless", ExplicitGraph(n, ())
        yield "star", ExplicitGraph(n, tuple((0, b) for b in range(1, n)))
        yield "balanced_bipartite", _multipartite(n, 2)
        yield "path", ExplicitGraph(n, tuple((a, a + 1) for a in range(n - 1)))
        if n >= 3 and (premise not in ("BIPARTITE", "TRIANGLE_FREE") or n % 2 == 0
                       or (premise == "TRIANGLE_FREE" and n >= 5)):
            yield "cycle", _circulant(n, {1})
        if n >= 4 and premise != "CONNECTED":
            k = 2 if premise in ("BIPARTITE", "TRIANGLE_FREE") else 3
            yield "clique_union", _union([_complete(k)] * (n // k) + [_complete(n % k)])
            clique_order = 2 if k == 2 else min(n - 1, k + n // 2)
            yield "clique_and_isolates", _union([_complete(clique_order),
                                                ExplicitGraph(n - clique_order, ())])
        if n >= 5 and premise in ("ALL", "CONNECTED"):
            yield "multipartite", _multipartite(n, 3)
            halves = _union([_complete(n // 2), _complete(n - n // 2)])
            yield "barbell", ExplicitGraph(n, tuple(sorted((*halves.edges, (n // 2 - 1, n // 2)))))
            yield "circulant", _circulant(n, {1, 2})
        if premise == "TRIANGLE_FREE" and n >= 5:
            yield "odd_cycle_blowup", ExplicitGraph(n, tuple(
                (a, b) for a, b in combinations(range(n), 2) if (b % 5 - a % 5) % 5 in (1, 4)))
