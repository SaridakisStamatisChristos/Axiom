"""Bounded deterministic counterexample search over typed affine graph claims."""
from collections import Counter
from itertools import combinations, islice, zip_longest
import random

from .graph_explicit import ExplicitGraph
from .graph_invariants import _max_subset, bipartite, components, matching_number, triangles
from .graph_large_witness import MAX_EXACT_ORDER, certify_witness, replay_witness
from .graph_refutation_portfolio import structured_graphs
from .graph_refutation_priority import violation_interval

SCHEMA = "axiom.graph.active_refutation.v1"
PORTFOLIO_SCHEMA = "axiom.graph.active_refutation.v2"
GUIDED_SCHEMA = "axiom.graph.active_refutation.v3"
PROFILES = ("mutation-v1", "portfolio-v2", "guided-v3")


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


def _within_premise(assumption, graph):
    return not ((assumption == "CONNECTED" and len(components(graph)) != 1)
                or (assumption == "BIPARTITE" and not bipartite(graph))
                or (assumption == "TRIANGLE_FREE" and triangles(graph)))


def _score(claim, graph):
    if not _within_premise(claim.bound.assumption, graph):
        return None
    funcs = {"n": lambda: graph.n, "edges": lambda: len(graph.edges),
             "maximum_degree": lambda: max(graph.degrees, default=0),
             "components": lambda: len(components(graph)), "triangles": lambda: triangles(graph),
             "clique": lambda: _max_subset(graph, True), "independence": lambda: _max_subset(graph, False),
             "matching": lambda: matching_number(graph), "chromatic": lambda: _chromatic(graph)}
    lhs = sum(weight * funcs[name]() for name, weight in claim.bound.terms)
    slack = lhs - claim.bound.upper
    return abs(slack) if claim.relation == "=" else slack


def _mutations(graph, assumption, max_order):
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
    if graph.n < max_order:
        for a in range(graph.n):
            yield "attach_leaf", ExplicitGraph(graph.n + 1, tuple(sorted((*graph.edges, (a, graph.n)))))
    n = graph.n
    if assumption != "BIPARTITE" and graph.edges and 2 * n + 1 <= max_order:
        edges = graph.edges + tuple((a, n + b) for a, b in graph.edges)
        edges += tuple((b, n + a) for a, b in graph.edges)
        edges += tuple((n + a, 2 * n) for a in range(n))
        yield "mycielski", ExplicitGraph(2 * n + 1, tuple(sorted(edges)))


def _structural_mutations(graph, assumption, max_order):
    n = graph.n
    if assumption in ("ALL", "CONNECTED") and graph.edges:
        edges = set(graph.edges)
        yield "complement", ExplicitGraph(n, tuple(edge for edge in combinations(range(n), 2)
                                                   if edge not in edges))
    if n >= max_order:
        return
    if assumption != "CONNECTED":
        yield "add_isolate", ExplicitGraph(n + 1, graph.edges)
    if assumption in ("ALL", "CONNECTED") and n:
        edges = (*graph.edges, *((v, n) for v in range(n)))
        yield "add_universal", ExplicitGraph(n + 1, tuple(sorted(edges)))
    for neighbors in sorted(set(graph.adjacency()) - {0}):
        edges = (*graph.edges, *((v, n) for v in range(n) if neighbors & (1 << v)))
        yield "clone_neighbors", ExplicitGraph(n + 1, tuple(sorted(edges)))


def _portfolio_frontier(winners, assumption, visited, rng, max_order):
    buckets = {}
    planned = set(visited)
    for _, graph in winners:
        for moves in (_structural_mutations(graph, assumption, max_order), _mutations(graph, assumption, max_order)):
            for operator, candidate in moves:
                if candidate in planned:
                    continue
                planned.add(candidate)
                buckets.setdefault(operator, []).append((operator, candidate))
    for bucket in buckets.values():
        rng.shuffle(bucket)
    return (move for batch in zip_longest(*buckets.values()) for move in batch if move is not None)


def _guided_seeds(claim, candidates, counts):
    ranked = []
    for move in candidates:
        lower, upper = violation_interval(claim, move[1])
        counts["priority_evaluations"] += 1
        if lower > 0:
            # The exact scorer and independent witness checker still run.
            yield move
            return
        ranked.append(((upper, lower), move))
    yield from (move for _, move in sorted(ranked, key=lambda row: row[0], reverse=True))


def _guided_mutations(claim, frontier, counts, remaining):
    pending = []
    # Bound the additional lookahead even for large search budgets.
    for move in islice(frontier, min(64, remaining * 4)):
        lower, _ = violation_interval(claim, move[1])
        counts["priority_evaluations"] += 1
        if lower > 0 and _within_premise(claim.bound.assumption, move[1]):
            yield move
            return
        pending.append(move)
    yield from pending
    yield from frontier


def _seed_frontier(initial, claim, budget, portfolio, guided, counts, max_order):
    yield from (("input", graph) for graph in initial)
    if portfolio:
        seen = set(initial)

        def additional():
            for family, graph in structured_graphs(max_order, claim.bound.assumption):
                if graph not in seen:
                    seen.add(graph)
                    yield f"family_{family}", graph

        candidates = additional()
        if guided:
            candidates = _guided_seeds(claim, candidates, counts)
        yield from islice(candidates, min(96, max(1, budget // 4)))


def search(claim, initial, *, seed=42, budget=1000, beam=8, profile="portfolio-v2",
           max_order=MAX_EXACT_ORDER):
    """Spend a fixed number of deterministic, unique labelled graph evaluations."""
    if profile not in PROFILES:
        raise ValueError("unknown active refutation profile")
    portfolio = profile != "mutation-v1"
    guided = profile == "guided-v3"
    if (type(seed) is not int or type(budget) is not int or not 1 <= budget <= 100_000
            or type(beam) is not int or not 1 <= beam <= 64
            or type(max_order) is not int or not 1 <= max_order <= MAX_EXACT_ORDER
            or (not initial and not portfolio)
            or any(type(g) is not ExplicitGraph or g.n > max_order for g in initial)):
        raise ValueError("invalid active refutation graph inputs or budget")
    initial = sorted(set(initial), key=lambda graph: (graph.n, graph.edges))
    schema = GUIDED_SCHEMA if guided else PORTFOLIO_SCHEMA if portfolio else SCHEMA
    assumption = claim.bound.assumption
    rng = random.Random(seed)
    visited = set()
    counts = Counter()
    levels = []
    frontier = _seed_frontier(initial, claim, budget, portfolio, guided, counts, max_order)
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
                    witness = certify_witness(claim, graph, origin=f"{schema} seed={seed}, operator={operator}")
                    replay_witness(claim, witness)
                    return _report(schema, claim, initial, seed, beam, budget, counts, len(visited), levels, witness, max_order)
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
        if portfolio:
            frontier = _portfolio_frontier(winners, assumption, visited, rng, max_order)
            if guided:
                frontier = _guided_mutations(claim, frontier, counts, budget - len(visited))
        else:
            frontier = [mutation for _, graph in winners for mutation in _mutations(graph, assumption, max_order)]
            rng.shuffle(frontier)
    return _report(schema, claim, initial, seed, beam, budget, counts, len(visited), levels, None, max_order)


def _report(schema, claim, initial, seed, beam, budget, counts, evaluations, levels, witness, max_order):
    from .graph_claims import digest

    counts = dict(counts)
    metrics = {"priority_evaluations": counts.pop("priority_evaluations", 0)} if schema == GUIDED_SCHEMA else {}
    if max_order != MAX_EXACT_ORDER:
        metrics["max_order"] = max_order
    return {"schema": schema, "candidate_id": claim.id, "seed": seed, "budget": budget, "beam": beam,
            "initial_sha256": digest([g.to_dict() for g in initial]),
            "evaluations": evaluations, "counts": counts, "levels": levels, **metrics,
            "status": "REFUTED" if witness else "NO_REFUTATION_OBSERVED", "witness": witness}
