"""Exact combinatorial invariants for tiny simple undirected graphs.

Exponential search is intentional: this is a bounded mathematical reference
engine, not a general-purpose approximate graph optimizer.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
from .graph_model import SimpleGraph


def components(g: SimpleGraph) -> tuple[tuple[int, ...], ...]:
    adj = g.adjacency()
    seen, blocks = set(), []
    for start in range(g.n):
        if start in seen:
            continue
        todo = [start]
        seen.add(start)
        comp = []
        while todo:
            v = todo.pop()
            comp.append(v)
            for w in range(g.n):
                if (adj[v] & (1 << w)) and w not in seen:
                    seen.add(w)
                    todo.append(w)
        blocks.append(tuple(sorted(comp)))
    return tuple(blocks)


def bipartite(g: SimpleGraph) -> bool:
    adj = g.adjacency()
    color = [-1] * g.n
    for root in range(g.n):
        if color[root] != -1:
            continue
        color[root] = 0
        queue = [root]
        for v in queue:
            for u in range(g.n):
                if not (adj[v] & (1 << u)):
                    continue
                if color[u] == color[v]:
                    return False
                if color[u] == -1:
                    color[u] = color[v] ^ 1
                    queue.append(u)
    return True


def forest(g: SimpleGraph) -> bool:
    parent = list(range(g.n))
    def find(a: int) -> int:
        while a != parent[a]:
            a = parent[a]
        return a
    for a, b in g.edges:
        x, y = find(a), find(b)
        if x == y:
            return False
        parent[x] = y
    return True


def triangles(g: SimpleGraph) -> int:
    adj = g.adjacency()
    count = 0
    for a, b, c in combinations(range(g.n), 3):
        if (adj[a] & (1 << b) and adj[a] & (1 << c) and adj[b] & (1 << c)):
            count += 1
    return count


def _max_subset(g: SimpleGraph, connected_pairs: bool) -> int:
    adj = g.adjacency()
    for size in range(g.n, 0, -1):
        for group in combinations(range(g.n), size):
            if all(bool(adj[u] & (1 << v)) == connected_pairs
                   for u, v in combinations(group, 2)):
                return size
    return 0


def chromatic(g: SimpleGraph) -> int:
    if g.n == 0:
        return 0
    adj = g.adjacency()
    # High-degree vertices first speeds exact backtracking.
    order = sorted(range(g.n), key=lambda v: (-g.degrees[v], v))
    assignment = [-1] * g.n
    def can_color(pos: int, palette: int) -> bool:
        if pos == g.n:
            return True
        v = order[pos]
        forbidden = {assignment[w] for w in range(g.n)
                     if adj[v] & (1 << w) and assignment[w] != -1}
        for color in range(palette):
            if color not in forbidden:
                assignment[v] = color
                if can_color(pos + 1, palette):
                    assignment[v] = -1
                    return True
        assignment[v] = -1
        return False
    for k in range(1, g.n + 1):
        if can_color(0, k):
            return k
    raise ArithmeticError('graph coloring search failed on a finite graph')


def matching_number(g: SimpleGraph) -> int:
    adj = g.adjacency()
    @lru_cache(maxsize=None)
    def recurse(unused: int) -> int:
        if unused == 0:
            return 0
        low = unused & -unused
        vertex = low.bit_length() - 1
        rest = unused ^ low
        best = recurse(rest)
        available = rest & adj[vertex]
        while available:
            bit = available & -available
            available ^= bit
            best = max(best, 1 + recurse(rest ^ bit))
        return best
    return recurse((1 << g.n) - 1)


def graph_properties(g: SimpleGraph) -> dict[str, int | bool]:
    comp = components(g)
    connected = g.n > 0 and len(comp) == 1
    acyclic = forest(g)
    chi = chromatic(g)
    return {
        'n': g.n,
        'edges': len(g.edges),
        'degree_sum': sum(g.degrees),
        'maximum_degree': max(g.degrees, default=0),
        'components': len(comp),
        'connected': connected,
        'tree': connected and acyclic,
        'forest': acyclic,
        'bipartite': bipartite(g),
        'triangles': triangles(g),
        'triangle_free': triangles(g) == 0,
        'clique': _max_subset(g, True),
        'independence': _max_subset(g, False),
        'chromatic': chi,
        'matching': matching_number(g),
    }
