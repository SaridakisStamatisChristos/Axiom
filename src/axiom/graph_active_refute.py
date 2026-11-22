"""Bounded deterministic mutation search over typed affine graph claims."""
from collections import Counter
from itertools import combinations
import random

from .graph_explicit import ExplicitGraph
from .graph_invariants import _max_subset, bipartite, components, matching_number, triangles
from .graph_large_witness import MAX_EXACT_ORDER, certify_witness, replay_witness

SCHEMA = "axiom.graph.active_refutation.v1"


def _chromatic(graph):
    adjacency = graph.adjacency()
    colors = [-1] * graph.n

    def fits(left, used, limit):
        if not left:
            return True
        forbidden = {v: {colors[u] for u in range(graph.n)
                         if adjacency[v] & (1 << u) and colors[u] >= 0} for v in left}
        v = max(left, key=lambda node: (len(forbidden[node]), adjacency[node].bit_count(), -node))
        for color in range(min(used + 1, limit)):
            if color in forbidden[v]:
                continue
            colors[v] = color
            if fits(left - {v}, max(used, color + 1), limit):
                colors[v] = -1
                return True
            colors[v] = -1
        return False

    return next(k for k in range(graph.n + 1) if fits(set(range(graph.n)), 0, k))


def _score(claim, graph):
    assumption = claim.bound.assumption
    if assumption == "CONNECTED" and len(components(graph)) != 1:
        return None
    if assumption == "BIPARTITE" and not bipartite(graph):
        return None
    if assumption == "TRIANGLE_FREE" and triangles(graph):
        return None
    funcs = {"n": lambda: graph.n, "edges": lambda: len(graph.edges),
             "maximum_degree": lambda: max(graph.degrees, default=0),
             "components": lambda: len(components(graph)), "triangles": lambda: triangles(graph),
             "clique": lambda: _max_subset(graph, True), "independence": lambda: _max_subset(graph, False),
             "matching": lambda: matching_number(graph), "chromatic": lambda: _chromatic(graph)}
    lhs = sum(weight * funcs[name]() for name, weight in claim.bound.terms)
    slack = lhs - claim.bound.upper
    return abs(slack) if claim.relation == "=" else slack


def _mutations(graph, assumption):
    edges = set(graph.edges)
    partition = None
    if assumption == "BIPARTITE":
        adjacency = graph.adjacency()
        partition = {}
        for root in range(graph.n):
            if root in partition:
                continue
            partition[root] = 0
            queue = [root]
            for v in queue:
                for u in range(graph.n):
                    if adjacency[v] & (1 << u) and u not in partition:
                        partition[u] = 1 - partition[v]
                        queue.append(u)
    for edge in combinations(range(graph.n), 2):
        if edge in edges or partition is None or partition[edge[0]] != partition[edge[1]]:
            yield "toggle_edge", ExplicitGraph(graph.n, tuple(sorted(edges ^ {edge})))
    for removed in range(graph.n):
        remaining = tuple((a - (a > removed), b - (b > removed)) for a, b in graph.edges
                          if removed not in (a, b))
        yield "delete_vertex", ExplicitGraph(graph.n - 1, remaining)
    if graph.n < MAX_EXACT_ORDER:
        for a in range(graph.n):
            yield "attach_leaf", ExplicitGraph(graph.n + 1, tuple(sorted((*graph.edges, (a, graph.n)))))
    n = graph.n
    if assumption != "BIPARTITE" and graph.edges and 2 * n + 1 <= MAX_EXACT_ORDER:
        edges = graph.edges + tuple((a, n + b) for a, b in graph.edges)
        edges += tuple((b, n + a) for a, b in graph.edges)
        edges += tuple((n + a, 2 * n) for a in range(n))
        yield "mycielski", ExplicitGraph(2 * n + 1, tuple(sorted(edges)))


def search(claim, initial, *, seed=42, budget=1000, beam=8):
    """Spend a fixed number of deterministic, unique labelled graph evaluations."""
    if (type(seed) is not int or type(budget) is not int or not 1 <= budget <= 100_000
            or type(beam) is not int or not 1 <= beam <= 64
            or not initial or any(type(g) is not ExplicitGraph or g.n > MAX_EXACT_ORDER for g in initial)):
        raise ValueError("invalid active refutation graph inputs or budget")
    rng = random.Random(seed)
    visited = set()
    counts = Counter()
    levels = []
    frontier = [("input", graph) for graph in sorted(set(initial), key=lambda g: (g.n, g.edges))]
    while frontier and len(visited) < budget:
        ranked = []
        for operator, graph in frontier:
            if graph in visited:
                continue
            visited.add(graph)
            counts[operator] += 1
            score = _score(claim, graph)
            if score is None:
                counts["outside_premise"] += 1
            else:
                ranked.append((score, graph))
                if score > 0:
                    witness = certify_witness(claim, graph, origin=f"{SCHEMA} seed={seed}, operator={operator}")
                    replay_witness(claim, witness)
                    return _report(claim, initial, seed, beam, budget, counts, len(visited), levels, witness)
            if len(visited) == budget:
                break
        if not ranked:
            break
        ranked.sort(key=lambda row: (row[0], row[1].n, row[1].edges), reverse=True)
        first_by_order = {}
        for score, graph in ranked:
            first_by_order.setdefault(graph.n, (score, graph))
        winners = list(first_by_order.values())[:beam]
        if len(winners) < beam:
            used = {graph for _, graph in winners}
            winners.extend([row for row in ranked if row[1] not in used][:beam - len(winners)])
        levels.append({"applicable": len(ranked), "best_violation": ranked[0][0]})
        frontier = [mutation for _, graph in winners for mutation in _mutations(graph, claim.bound.assumption)]
        rng.shuffle(frontier)
    return _report(claim, initial, seed, beam, budget, counts, len(visited), levels, None)


def _report(claim, initial, seed, beam, budget, counts, evaluations, levels, witness):
    from .graph_claims import digest

    return {"schema": SCHEMA, "candidate_id": claim.id, "seed": seed, "budget": budget, "beam": beam,
            "initial_sha256": digest([g.to_dict() for g in sorted(set(initial), key=lambda g: (g.n, g.edges))]),
            "evaluations": evaluations, "counts": dict(counts), "levels": levels,
            "status": "REFUTED" if witness else "NO_REFUTATION_OBSERVED", "witness": witness}
