import copy
import pytest
from axiom.graph_claims import GraphStatement, TEMPLATES
from axiom.graph_checker import (build_finite_certificate,check_finite_certificate,
                                 check_graph_witness,reference_properties)
from axiom.graph_campaign import scan_graph_statement
from axiom.graph_model import SimpleGraph


def test_statement_typed_grammar_rejects_unsupported():
    for v in [GraphStatement(5,'handshake',0).to_dict()]:
        assert GraphStatement.from_dict(v).to_dict()==v
    for args in [(8,'handshake'),(True,'handshake'),(5,'invalid'),(5,'handshake',1),
                 (5,'edges_le_n_plus_k',100)]:
        with pytest.raises(ValueError):GraphStatement(*args)
    x=GraphStatement(5,'handshake').to_dict();x['claim']='graph is always complete'
    with pytest.raises(ValueError):GraphStatement.from_dict(x)


def test_finite_handshake_proof_and_vacuity_label():
    for n in range(6):
        stmt=GraphStatement(n,'handshake')
        cert=build_finite_certificate(stmt.to_dict())
        assert check_finite_certificate(stmt.to_dict(),cert)
        assert cert['labelled_graphs_checked']==2**(n*(n-1)//2)
        assert cert['assumption_satisfying']==cert['labelled_graphs_checked']
    v=GraphStatement(0,'tree_edge_count').to_dict()
    cert=build_finite_certificate(v)
    assert cert['vacuous'] and cert['assumption_satisfying']==0


def test_false_graph_claims_rejected_by_independent_checker():
    for template in ['triangle_free_is_bipartite','chromatic_le_clique',
                     'connected_tree_claim','connected_edges_ge_n']:
        s=GraphStatement(5,template)
        scan=scan_graph_statement(s,100,42)
        witness=scan['counterexample']
        assert witness is not None
        assert check_graph_witness(s.to_dict(),witness)
        with pytest.raises(ValueError):build_finite_certificate(s.to_dict())
        assert scan['method']=='EXHAUSTIVE_ISOMORPHISM_CLASSES'
    c5=GraphStatement(5,'triangle_free_is_bipartite').to_dict()
    bad=SimpleGraph.from_mask(5,0).to_dict()
    with pytest.raises(ValueError):check_graph_witness(c5,bad)


def test_no_finite_to_universal_promotion():
    stmt=GraphStatement(6,'handshake')
    scan=scan_graph_statement(stmt,100,99)
    assert scan['counterexample'] is None
    assert scan['structures_checked']==100
    with pytest.raises(ValueError):build_finite_certificate(stmt.to_dict())
    fabricated={'schema':'axiom.graph.exhaustive_finite.v1','method':'exhaustive_all_labelled_simple_graphs',
                'statement_sha256':'fake','order':6,'labelled_graphs_checked':2**15,
                'assumption_satisfying':2**15,'vacuous':False,
                'search_scope':'ALL graphs of exactly n vertices; no claim for other n'}
    with pytest.raises(ValueError):check_finite_certificate(stmt.to_dict(),fabricated)


def test_certificate_mutations_rejected():
    stmt=GraphStatement(5,'handshake').to_dict()
    original=build_finite_certificate(stmt)
    for field,value in [('statement_sha256','bad'),('labelled_graphs_checked',1023),
                        ('assumption_satisfying',0),('vacuous',True),('order',4),
                        ('method','no-op'),('search_scope','all n'),('schema','bad')]:
        bad=copy.deepcopy(original);bad[field]=value
        with pytest.raises(ValueError):check_finite_certificate(stmt,bad)
    bad=copy.deepcopy(original);bad['extra']=42
    with pytest.raises(ValueError):check_finite_certificate(stmt,bad)


def test_witness_must_match_exact_statement_and_assumptions():
    c5=GraphStatement(5,'chromatic_le_clique').to_dict()
    witness=scan_graph_statement(GraphStatement(5,'chromatic_le_clique'),128,42)['counterexample']
    assert check_graph_witness(c5,witness)
    for mutated in [dict(witness,n=4),dict(witness,edges=[]),dict(witness,edges=witness['edges']+[[0,0]])]:
        with pytest.raises(ValueError):check_graph_witness(c5,mutated)


def test_template_semantics_examples():
    # Exact fixed n can be true but trivially or vacuously so; no importance claim.
    assert len(TEMPLATES)>=20
    for name in ['clique_le_chromatic','chromatic_le_delta_plus_one',
                 'independence_times_chromatic','tree_edge_count','forest_bipartite']:
        assert check_finite_certificate(GraphStatement(5,name).to_dict(),
                      build_finite_certificate(GraphStatement(5,name).to_dict()))


def test_independent_certificate_checker_detects_corrupt_discovery_engine(monkeypatch):
    from axiom import graph_campaign as campaign
    original=campaign._discovery_properties
    def lying_properties(n,mask):
        values=dict(original(n,mask))
        values['bipartite']=True  # makes false C5 implication appear true
        return values
    monkeypatch.setattr(campaign,'_discovery_properties',lying_properties)
    s=GraphStatement(5,'triangle_free_is_bipartite')
    search=campaign.scan_graph_statement(s,100,4)
    assert search['counterexample'] is None
    # Independent checker enumerates all 1024 original graphs, catches C5.
    with pytest.raises(ValueError):build_finite_certificate(s.to_dict())
