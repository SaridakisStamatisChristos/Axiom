"""Finite undirected loop-free graphs with exact, label-independent canonicalization.

Vertices are 0..n-1. The bit at position k in a graph mask corresponds to
pair (i,j) in lexicographic order, i<j. No multigraphs or implicit vertices.
For vertex-isomorphism canonicalization the order is grouped by degree;
permutations within equal-degree blocks are then searched exactly.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product
from typing import Any

MAX_VERTICES = 7  # bounded exhaustive/sampling research, not general large-graph support


@lru_cache(maxsize=None)
def edge_positions(n: int) -> tuple[tuple[int, int], ...]:
    if type(n) is not int or not 0 <= n <= MAX_VERTICES:
        raise ValueError('graph order must be an integer from 0 through 7')
    return tuple((i, j) for i in range(n) for j in range(i + 1, n))


@dataclass(frozen=True)
class SimpleGraph:
    n: int
    edges: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        edge_positions(self.n)
        if type(self.edges) is not tuple:
            raise ValueError('edges must be a tuple')
        prior = (-1, -1)
        for e in self.edges:
            if (type(e) is not tuple or len(e) != 2 or
                    type(e[0]) is not int or type(e[1]) is not int or
                    not 0 <= e[0] < e[1] < self.n or e <= prior):
                raise ValueError('edges must be unique ordered pairs, sorted lexicographically')
            prior = e

    @classmethod
    def from_mask(cls, n: int, mask: int) -> 'SimpleGraph':
        positions = edge_positions(n)
        if type(mask) is not int or not 0 <= mask < (1 << len(positions)):
            raise ValueError('edge mask outside the finite simple-graph domain')
        return cls(n, tuple(e for idx, e in enumerate(positions) if mask & (1 << idx)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SimpleGraph':
        if (not isinstance(data, dict) or set(data) != {'n', 'edges'} or
                type(data['edges']) is not list):
            raise ValueError('invalid graph serialization')
        if any(type(x) is not list or len(x) != 2 for x in data['edges']):
            raise ValueError('invalid serialized edge pair')
        return cls(data['n'], tuple(tuple(e) for e in data['edges']))

    def to_dict(self) -> dict[str, Any]:
        return {'n': self.n, 'edges': [list(e) for e in self.edges]}

    @property
    def mask(self) -> int:
        positions = {p: i for i, p in enumerate(edge_positions(self.n))}
        return sum(1 << positions[e] for e in self.edges)

    @property
    def degrees(self) -> tuple[int, ...]:
        a = [0] * self.n
        for i, j in self.edges:
            a[i] += 1
            a[j] += 1
        return tuple(a)

    def adjacency(self) -> tuple[int, ...]:
        a = [0] * self.n
        for i, j in self.edges:
            a[i] |= 1 << j
            a[j] |= 1 << i
        return tuple(a)

    def canonical_mask(self) -> int:
        """Exact isomorphism code, independent of original vertex labels.

        Any isomorphism preserves degree. Therefore it suffices to put vertices
        in nondecreasing degree order and permute only within equal-degree blocks.
        The least adjacency mask over these orderings is a canonical invariant.
        """
        degrees = self.degrees
        classes = [tuple(i for i in range(self.n) if degrees[i] == d)
                   for d in sorted(set(degrees))]
        adj = self.adjacency()
        best: int | None = None
        for chunks in product(*(permutations(c) for c in classes)):
            order = [v for chunk in chunks for v in chunk]
            mask, bit = 0, 1
            for i in range(self.n):
                for j in range(i + 1, self.n):
                    if adj[order[i]] & (1 << order[j]):
                        mask |= bit
                    bit <<= 1
            if best is None or mask < best:
                best = mask
        return 0 if best is None else best

    def canonical_key(self) -> str:
        return f'{self.n}:{self.canonical_mask()}'

    def relabel(self, order: tuple[int, ...]) -> 'SimpleGraph':
        """Order lists old vertex labels for the new labels 0..n-1."""
        if (type(order) is not tuple or len(order) != self.n or
                any(type(x) is not int for x in order) or sorted(order) != list(range(self.n))):
            raise ValueError('invalid vertex permutation')
        old_to_new = {v: idx for idx, v in enumerate(order)}
        new_edges = [tuple(sorted((old_to_new[i], old_to_new[j]))) for i, j in self.edges]
        return SimpleGraph(self.n, tuple(sorted(new_edges)))


def isomorphism_representatives(n: int) -> list[SimpleGraph]:
    """Enumerate all unlabeled simple graphs for small fixed n exactly."""
    if n > 5:
        raise ValueError('exhaustive isomorphism representative generation limited to n<=5')
    seen = set()
    result = []
    for mask in range(1 << len(edge_positions(n))):
        g = SimpleGraph.from_mask(n, mask)
        code = g.canonical_mask()
        if code not in seen:
            seen.add(code)
            result.append(g)
    return result
