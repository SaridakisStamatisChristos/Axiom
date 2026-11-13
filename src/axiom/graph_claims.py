"""Closed typed grammar for fixed-order finite simple-graph statements.

A claim quantifies universally over ALL labelled simple graphs with exactly n
vertices. An assumption restricts those graphs; it does not restrict n. The
optional integer k only applies to parameterized templates. The graph order is
part of the logical statement, so a proof for n=5 says nothing about n=6.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Any
from .graph_model import MAX_VERTICES

# (antecedent, relationship): null means all finite simple graphs of fixed n.
TEMPLATES: dict[str, tuple[str | None, str]] = {
    'handshake': (None, 'sum degrees = 2|E|'),
    'degree_bound': (None, 'maximum degree <= n-1 for n>0'),
    'clique_le_chromatic': (None, 'omega <= chi'),
    'chromatic_le_delta_plus_one': (None, 'chi <= Delta+1'),
    'independence_times_chromatic': (None, 'alpha*chi >= n'),
    'triangle_upper_bound': (None, 'triangles <= C(n,3)'),
    'matching_upper_bound': (None, '2*nu <= n'),
    'bipartite_no_triangles': ('bipartite', 'triangles = 0'),
    'bipartite_chromatic_bound': ('bipartite', 'chi <= 2'),
    'forest_bipartite': ('forest', 'bipartite'),
    'forest_edge_count': ('forest', '|E| = n-components'),
    'tree_edge_count': ('tree', '|E| = n-1'),
    'connected_edge_lower_bound': ('connected', '|E| >= n-1'),
    'connected_tree_claim': ('connected', 'tree'),
    'triangle_free_is_bipartite': ('triangle_free', 'bipartite'),
    'chromatic_le_clique': (None, 'chi <= omega'),
    'connected_edges_ge_n': ('connected', '|E| >= n'),
    'edges_le_vertices': (None, '|E| <= n'),
    'triangles_le_edges': (None, 'triangles <= |E|'),
    'no_triangles_implies_forest': ('triangle_free', 'forest'),
    'chromatic_ge_max_degree': (None, 'chi >= Delta'),
    'alpha_plus_clique_bound': (None, 'alpha+omega <= n+1'),
    'connected_has_chromatic_ge_two': ('connected_nonempty_edges', 'chi >= 2'),
    'edges_le_n_plus_k': (None, '|E| <= n+k'),
    'bipartite_independence_at_least_k': ('bipartite', 'alpha >= k'),
}
PARAMETERIZED = {'edges_le_n_plus_k', 'bipartite_independence_at_least_k'}


def stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(stable(value).encode('ascii')).hexdigest()


@dataclass(frozen=True)
class GraphStatement:
    n: int
    template: str
    k: int = 0

    def __post_init__(self) -> None:
        if type(self.n) is not int or not 0 <= self.n <= MAX_VERTICES:
            raise ValueError('statement graph order must be 0..7')
        if type(self.template) is not str or self.template not in TEMPLATES:
            raise ValueError('unsupported graph statement template')
        if type(self.k) is not int or not -3 <= self.k <= 7:
            raise ValueError('invalid integer template parameter')
        if self.template not in PARAMETERIZED and self.k != 0:
            raise ValueError('parameter not applicable to this graph statement')

    def to_dict(self) -> dict[str, Any]:
        return {'quantifier': 'forall_finite_simple_graphs_of_exact_order',
                'n': self.n, 'template': self.template, 'k': self.k,
                'assumption': TEMPLATES[self.template][0],
                'claim': TEMPLATES[self.template][1]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'GraphStatement':
        if (type(data) is not dict or
                set(data) != {'quantifier', 'n', 'template', 'k', 'assumption', 'claim'} or
                data.get('quantifier') != 'forall_finite_simple_graphs_of_exact_order'):
            raise ValueError('invalid graph statement structure')
        x = cls(data['n'], data['template'], data['k'])
        if x.to_dict() != data:
            raise ValueError('graph statement semantics were altered')
        return x

    def canonical_key(self) -> str:
        return stable([self.n, self.template, self.k])


def holds(statement: GraphStatement, p: dict[str, int | bool]) -> tuple[bool, bool]:
    """Return (assumptions_satisfied, conclusion_satisfied).

    This declarative interpreter is shared by discovery and reference checking;
    the actual invariants are computed independently in the two subsystems.
    """
    if type(p.get('n')) is not int or p['n'] != statement.n:
        raise ValueError('graph order mismatch')
    t = statement.template
    a = TEMPLATES[t][0]
    applicable = (a is None or (bool(p.get('connected')) and p['edges'] > 0
                                    if a == 'connected_nonempty_edges' else bool(p[a])))
    n, m = p['n'], p['edges']
    if t == 'handshake': ok = p['degree_sum'] == 2*m
    elif t == 'degree_bound': ok = p['maximum_degree'] <= max(0, n-1)
    elif t == 'clique_le_chromatic': ok = p['clique'] <= p['chromatic']
    elif t == 'chromatic_le_delta_plus_one': ok = p['chromatic'] <= p['maximum_degree']+1
    elif t == 'independence_times_chromatic': ok = p['independence']*p['chromatic'] >= n
    elif t == 'triangle_upper_bound': ok = 6*p['triangles'] <= n*(n-1)*(n-2) if n>=3 else p['triangles']==0
    elif t == 'matching_upper_bound': ok = 2*p['matching'] <= n
    elif t == 'bipartite_no_triangles': ok = p['triangles']==0
    elif t == 'bipartite_chromatic_bound': ok = p['chromatic']<=2
    elif t == 'forest_bipartite': ok = p['bipartite']
    elif t == 'forest_edge_count': ok = m==n-p['components']
    elif t == 'tree_edge_count': ok = m==n-1
    elif t == 'connected_edge_lower_bound': ok = m>=n-1
    elif t == 'connected_tree_claim': ok = p['tree']
    elif t == 'triangle_free_is_bipartite': ok = p['bipartite']
    elif t == 'chromatic_le_clique': ok = p['chromatic']<=p['clique']
    elif t == 'connected_edges_ge_n': ok = m>=n
    elif t == 'edges_le_vertices': ok = m<=n
    elif t == 'triangles_le_edges': ok = p['triangles']<=m
    elif t == 'no_triangles_implies_forest': ok = p['forest']
    elif t == 'chromatic_ge_max_degree': ok = p['chromatic']>=p['maximum_degree']
    elif t == 'alpha_plus_clique_bound': ok = p['independence']+p['clique']<=n+1
    elif t == 'connected_has_chromatic_ge_two': ok = p['chromatic']>=2
    elif t == 'edges_le_n_plus_k': ok = m<=n+statement.k
    elif t == 'bipartite_independence_at_least_k': ok = p['independence']>=statement.k
    else: raise ValueError('invalid template')
    return bool(applicable), bool(ok)
