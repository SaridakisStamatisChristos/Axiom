"""Independent stdlib graph witness and finite-exhaustion certificate checker.

This module does not import or call the graph discovery invariant engine.
Every finite proof is rechecked over ALL labelled graphs with the exact n.
Thus 'proved' is always scoped to finite graph order n<=5, never to all n.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
from .graph_model import SimpleGraph, edge_positions
from .graph_claims import GraphStatement, holds, digest

CERT_SCHEMA = 'axiom.graph.exhaustive_finite.v1'
PROOF_N_LIMIT = 5


@lru_cache(maxsize=6000)
def reference_properties(n: int, mask: int) -> dict:
    pairs = edge_positions(n)
    if type(mask) is not int or not 0<=mask<(1<<len(pairs)):
        raise ValueError('invalid reference graph mask')
    edges = tuple(p for i,p in enumerate(pairs) if mask>>i&1)
    adj = [[False]*n for _ in range(n)]
    degree = [0]*n
    for a,b in edges:
        adj[a][b] = adj[b][a] = True
        degree[a]+=1;degree[b]+=1
    components = 0
    visited=set()
    for s in range(n):
        if s not in visited:
            components+=1
            queue=[s];visited.add(s)
            for v in queue:
                for u in range(n):
                    if adj[v][u] and u not in visited:
                        queue.append(u);visited.add(u)
    bip = any(all(not adj[a][b] or (bool(group>>a&1) != bool(group>>b&1))
                  for a,b in edges) for group in range(1<<n))
    tri = sum(1 for a,b,c in combinations(range(n),3)
              if adj[a][b] and adj[a][c] and adj[b][c])
    independence,clique = 0,0
    for subset in range(1<<n):
        vs=[i for i in range(n) if subset>>i&1]
        size=len(vs)
        if all(not adj[a][b] for a,b in combinations(vs,2)):
            independence=max(independence,size)
        if all(adj[a][b] for a,b in combinations(vs,2)):
            clique=max(clique,size)
    # Independent coloring oracle: natural vertex order, branch-and-bound over
    # palette labels. This is deliberately distinct from the degree-ordered
    # graph discovery implementation.
    chromatic=0
    if n:
        colors=[-1]*n
        def assign(v:int, palette:int) -> bool:
            if v==n:return True
            for c in range(palette):
                if all(not adj[v][u] or colors[u]!=c for u in range(v)):
                    colors[v]=c
                    if assign(v+1,palette):
                        colors[v]=-1
                        return True
            colors[v]=-1
            return False
        for num_colors in range(1,n+1):
            if assign(0,num_colors):
                chromatic=num_colors;break
    # Independent matching oracle: enumerate k-edge combinations directly.
    matching=0
    for size in range(n//2,0,-1):
        if any(len({v for edge in combo for v in edge})==2*size
               for combo in combinations(edges,size)):
            matching=size;break
    # A finite graph is a forest iff every component is a tree; via DFS count.
    forest = len(edges)==n-components
    connected=n>0 and components==1
    return {'n':n,'edges':len(edges),'degree_sum':sum(degree),
            'maximum_degree':max(degree,default=0),'components':components,
            'connected':connected,'tree':connected and forest,'forest':forest,
            'bipartite':bip,'triangles':tri,'triangle_free':tri==0,
            'clique':clique,'independence':independence,'chromatic':chromatic,
            'matching':matching}


def check_graph_witness(statement_data: dict, graph_data: dict) -> bool:
    statement=GraphStatement.from_dict(statement_data)
    g=SimpleGraph.from_dict(graph_data)
    if g.n!=statement.n:
        raise ValueError('witness has wrong graph order')
    applicable,correct=holds(statement,reference_properties(g.n,g.mask))
    if not applicable or correct:
        raise ValueError('witness is not a valid counterexample')
    return True


def check_finite_certificate(statement_data: dict, certificate: dict) -> bool:
    statement=GraphStatement.from_dict(statement_data)
    n=statement.n
    if n>PROOF_N_LIMIT:
        raise ValueError('finite certificate may only prove n<=5')
    if type(certificate) is not dict or set(certificate)!={
        'schema','method','statement_sha256','order','labelled_graphs_checked',
        'assumption_satisfying','vacuous','search_scope'}:
        raise ValueError('finite graph certificate shape rejected')
    count=1<<len(edge_positions(n))
    if (certificate['schema']!=CERT_SCHEMA or
            certificate['method']!='exhaustive_all_labelled_simple_graphs' or
            certificate['statement_sha256']!=digest(statement_data) or
            type(certificate['order']) is not int or certificate['order']!=n or
            type(certificate['labelled_graphs_checked']) is not int or
            certificate['labelled_graphs_checked']!=count or
            certificate['search_scope']!='ALL graphs of exactly n vertices; no claim for other n'):
        raise ValueError('graph certificate metadata rejected')
    satisfying=0
    for mask in range(count):
        applies,valid=holds(statement,reference_properties(n,mask))
        if applies:
            satisfying+=1
            if not valid:
                raise ValueError('finite theorem falsified by an independently checked graph')
    if (type(certificate['assumption_satisfying']) is not int or
            certificate['assumption_satisfying']!=satisfying or
            type(certificate['vacuous']) is not bool or
            certificate['vacuous']!=(satisfying==0)):
        raise ValueError('graph certificate coverage mismatch')
    return True


def build_finite_certificate(statement_data: dict) -> dict:
    """Only invoked after conjecture search; checker independently re-enumerates."""
    statement=GraphStatement.from_dict(statement_data)
    if statement.n>PROOF_N_LIMIT:
        raise ValueError('cannot build finite proof for n>5')
    satisfying=0
    for mask in range(1<<len(edge_positions(statement.n))):
        applies,correct=holds(statement,reference_properties(statement.n,mask))
        if applies:
            satisfying+=1
            if not correct:
                raise ValueError('counterexample invalidates proposed finite proof')
    cert={'schema':CERT_SCHEMA,'method':'exhaustive_all_labelled_simple_graphs',
          'statement_sha256':digest(statement_data),'order':statement.n,
          'labelled_graphs_checked':1<<len(edge_positions(statement.n)),
          'assumption_satisfying':satisfying,'vacuous':satisfying==0,
          'search_scope':'ALL graphs of exactly n vertices; no claim for other n'}
    check_finite_certificate(statement_data,cert)
    return cert
