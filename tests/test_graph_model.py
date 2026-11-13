import itertools
import random
import pytest
from axiom.graph_model import SimpleGraph, edge_positions, isomorphism_representatives
from axiom.graph_invariants import graph_properties
from axiom.graph_checker import reference_properties


def test_typed_invalid_graphs():
    for n,mask in [(True,0),(-1,0),(8,0),(3,-1),(3,8),(3,False),(3,1.0)]:
        with pytest.raises(ValueError):SimpleGraph.from_mask(n,mask)
    for edges in [((0,0),),((0,3),),((1,0),),((0,1),(0,1)),
                  ((1,2),(0,1)),([0,1],),((0,True),)]:
        with pytest.raises(ValueError):SimpleGraph(3,edges)
    with pytest.raises(ValueError):SimpleGraph.from_dict({'n':3,'edges':[(0,1)]})
    with pytest.raises(ValueError):SimpleGraph.from_dict({'n':3,'edges':[[0,1]],'extra':0})


def test_all_unlabeled_graph_class_counts():
    assert [len(isomorphism_representatives(n)) for n in range(6)]==[1,1,2,4,11,34]
    with pytest.raises(ValueError):isomorphism_representatives(6)


def test_edge_encoding_serialization_and_permutation_invariance():
    for n in range(6):
        positions=edge_positions(n)
        for mask in range(1<<len(positions)):
            g=SimpleGraph.from_mask(n,mask)
            assert g.mask==mask
            assert SimpleGraph.from_dict(g.to_dict())==g
            if n<=4:
                k=g.canonical_key()
                for perm in itertools.permutations(range(n)):
                    assert g.relabel(tuple(perm)).canonical_key()==k
                for h in [g.relabel(tuple(reversed(range(n))))]:
                    assert h.canonical_key()==k


def test_invariants_independent_oracle_all_small_graphs():
    for n in range(6):
        for mask in range(1<<len(edge_positions(n))):
            g=SimpleGraph.from_mask(n,mask)
            assert graph_properties(g)==reference_properties(n,mask)


def test_oracle_random_larger_graphs():
    rng=random.Random(1203)
    for n in (6,7):
        samples={0,(1<<len(edge_positions(n)))-1}
        samples.update(rng.randrange(1<<len(edge_positions(n))) for _ in range(25))
        for mask in samples:
            assert graph_properties(SimpleGraph.from_mask(n,mask))==reference_properties(n,mask)


def test_graph_examples():
    # Edgeless empty graph has chi=0 and no connected components.
    z=graph_properties(SimpleGraph.from_mask(0,0))
    assert z['chromatic']==0 and z['components']==0 and not z['connected']
    # C5 has chromatic number 3 and clique number 2.
    cycle=SimpleGraph(5,((0,1),(0,4),(1,2),(2,3),(3,4)))
    p=graph_properties(cycle)
    assert p['triangles']==0 and not p['bipartite'] and p['chromatic']==3
    assert p['clique']==2 and p['independence']==2 and p['matching']==2
    complete=SimpleGraph.from_mask(5,(1<<len(edge_positions(5)))-1)
    q=graph_properties(complete)
    assert q['chromatic']==5 and q['clique']==5 and q['independence']==1
    assert q['triangles']==10 and q['matching']==2 and q['degree_sum']==20


def test_networkx_independent_isomorphism_oracle_if_available():
    nx=pytest.importorskip('networkx')
    rng=random.Random(909)
    for n in range(1,6):
        for _ in range(25):
            a=SimpleGraph.from_mask(n,rng.randrange(1<<len(edge_positions(n))))
            b=a.relabel(tuple(rng.sample(range(n),n)))
            def nxg(g):
                obj=nx.Graph();obj.add_nodes_from(range(g.n));obj.add_edges_from(g.edges)
                return obj
            assert nx.is_isomorphic(nxg(a),nxg(b))
            assert a.canonical_key()==b.canonical_key()
            assert nx.number_connected_components(nxg(a))==graph_properties(a)['components']
