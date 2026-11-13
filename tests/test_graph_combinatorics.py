import copy
from math import comb
import pytest
from axiom.graph_combinatorics import edge_count_histogram,check_edge_count_histogram
from axiom.graph_model import isomorphism_representatives


def test_all_small_edge_count_distributions_exact():
    for n in range(6):
        e=edge_count_histogram(n)
        assert check_edge_count_histogram(e)
        m=n*(n-1)//2
        assert e['counts_by_number_of_edges']==[comb(m,k) for k in range(m+1)]
        assert e['total_labelled_graphs']==2**m
    assert len(isomorphism_representatives(5))==34


def test_mutated_distributions_fail_independent_check():
    e=edge_count_histogram(5)
    for key,value in [('order',6),('possible_edges',12),('total_labelled_graphs',999),
                      ('statement_sha256','fake'),('formal_verification','FORMALLY_VERIFIED')]:
        bad=copy.deepcopy(e);bad[key]=value
        with pytest.raises(ValueError):check_edge_count_histogram(bad)
    bad=copy.deepcopy(e);bad['counts_by_number_of_edges'][4]+=1
    with pytest.raises(ValueError):check_edge_count_histogram(bad)


def test_out_of_fragment_graph_histogram():
    for n in (6,-1,True,3.5):
        with pytest.raises(ValueError):edge_count_histogram(n)
