"""Independent exact replay for explicit simple-graph refutations."""
from functools import lru_cache
from itertools import combinations

from .graph_affine import check_conjecture
from .graph_claims import digest, stable
from .graph_explicit import ExplicitGraph

SCHEMA = "axiom.graph.large_witness.v1"
CHECKER = "axiom.graph.explicit_witness_checker.v1"
MAX_EXACT_ORDER = 12


def exact_properties(graph):
    """Enumeration certifies both sides of every extremal invariant."""
    n, edges = graph.n, graph.edges
    if n > MAX_EXACT_ORDER:
        raise ValueError(f"explicit witness replay supports at most {MAX_EXACT_ORDER} vertices")
    edge_set = set(edges)
    pending = set(range(n))
    components = 0
    while pending:
        block = {min(pending)}
        while True:
            expanded = block | {b for a, b in edges if a in block} | {a for a, b in edges if b in block}
            if expanded == block:
                break
            block = expanded
        pending -= block
        components += 1
    independent = [[] for _ in range(n)]
    alpha = clique = 0
    for subset in range(1, 1 << n):
        vertices = [v for v in range(n) if subset & (1 << v)]
        pairs = tuple(combinations(vertices, 2))
        if not any(edge in edge_set for edge in pairs):
            alpha = max(alpha, len(vertices))
            for v in vertices:
                independent[v].append(subset)
        if all(edge in edge_set for edge in pairs):
            clique = max(clique, len(vertices))

    @lru_cache(maxsize=None)
    def chromatic(mask):
        if not mask:
            return 0
        first = (mask & -mask).bit_length() - 1
        return 1 + min(chromatic(mask ^ group) for group in independent[first] if group & mask == group)

    chi = chromatic((1 << n) - 1)
    matched = {0}
    for a, b in edges:
        pair = (1 << a) | (1 << b)
        matched |= {used | pair for used in matched if not used & pair}
    tri = sum(all(edge in edge_set for edge in combinations(vertices, 2))
              for vertices in combinations(range(n), 3))
    return {"n": n, "edges": len(edges), "components": components, "connected": components == 1,
            "maximum_degree": max(graph.degrees, default=0), "triangles": tri, "triangle_free": tri == 0,
            "clique": clique, "independence": alpha, "bipartite": chi <= 2, "chromatic": chi,
            "matching": max(mask.bit_count() for mask in matched) // 2}


def _violation(claim, properties):
    for index, side in enumerate(claim.inequalities()):
        applies, valid, lhs = check_conjecture(side, properties)
        if applies and not valid:
            return index, lhs, side.upper
    return None


def certify_witness(claim, graph, *, origin):
    if type(origin) is not str or not origin.strip() or len(origin) > 512:
        raise ValueError("expected a short nonempty witness origin")
    properties = exact_properties(graph)
    result = _violation(claim, properties)
    if result is None:
        raise ValueError("explicit graph does not refute the typed statement")
    side, lhs, rhs = result
    return {"schema": SCHEMA, "checker": CHECKER, "origin": origin,
            "statement_sha256": digest(claim.to_dict()), "graph": graph.to_dict(),
            "graph_sha256": digest(graph.to_dict()), "checked_properties": properties,
            "violated_direction": side, "left_hand_side": lhs, "right_hand_side": rhs}


def replay_witness(claim, witness):
    if type(witness) is not dict or witness.get("schema") != SCHEMA:
        raise ValueError("unknown explicit witness schema")
    expected = certify_witness(claim, ExplicitGraph.from_dict(witness.get("graph")),
                               origin=witness.get("origin"))
    if stable(witness) != stable(expected):
        raise ValueError("independent explicit graph witness replay differs")
    return True


def _deletions(graph):
    for v in range(graph.n):
        edges = tuple((a - (a > v), b - (b > v)) for a, b in graph.edges if v not in (a, b))
        yield ExplicitGraph(graph.n - 1, edges)
    for index in range(len(graph.edges)):
        yield ExplicitGraph(graph.n, graph.edges[:index] + graph.edges[index + 1:])


def minimize_witness(claim, graph):
    if _violation(claim, exact_properties(graph)) is None:
        raise ValueError("explicit graph does not refute the typed statement")
    while True:
        smaller = next((g for g in _deletions(graph) if _violation(claim, exact_properties(g)) is not None), None)
        if smaller is None:
            return graph
        graph = smaller
