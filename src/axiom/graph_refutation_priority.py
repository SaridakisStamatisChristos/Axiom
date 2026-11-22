"""Cheap invariant intervals for prioritizing exact refutation evaluations."""
from .graph_invariants import components, triangles


def _clique_interval(adjacency):
    """Greedy clique and proper coloring bound the clique number."""
    order = sorted(range(len(adjacency)), key=lambda v: (-adjacency[v].bit_count(), v))
    clique = 0
    color_classes = []
    for v in order:
        if clique & adjacency[v] == clique:
            clique |= 1 << v
        for i, group in enumerate(color_classes):
            if not group & adjacency[v]:
                color_classes[i] |= 1 << v
                break
        else:
            color_classes.append(1 << v)
    return clique.bit_count(), len(color_classes)


def violation_interval(claim, graph):
    """Return lower and upper violation bounds without exact invariant search."""
    adjacency = graph.adjacency()
    n = graph.n
    all_vertices = (1 << n) - 1
    clique_interval = None
    exact = {"n": lambda: n, "edges": lambda: len(graph.edges),
             "maximum_degree": lambda: max(map(int.bit_count, adjacency), default=0),
             "components": lambda: len(components(graph)), "triangles": lambda: triangles(graph)}
    low = high = -claim.bound.upper
    for name, weight in claim.bound.terms:
        if name in ("clique", "chromatic"):
            if clique_interval is None:
                clique_interval = _clique_interval(adjacency)
            lower, upper = clique_interval
        elif name == "independence":
            complement = tuple(all_vertices ^ row ^ (1 << v) for v, row in enumerate(adjacency))
            lower, upper = _clique_interval(complement)
        elif name == "matching":
            free = all_vertices
            lower = 0
            for a, b in graph.edges:
                pair = (1 << a) | (1 << b)
                if free & pair == pair:
                    free ^= pair
                    lower += 1
            upper = min(n // 2, len(graph.edges))
        else:
            lower = upper = exact[name]()
        ends = weight * lower, weight * upper
        low += min(ends)
        high += max(ends)
    if claim.relation == "=":
        return max(0, low, -high), max(abs(low), abs(high))
    return low, high
