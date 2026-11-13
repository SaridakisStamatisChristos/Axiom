"""Finite combinatorics: exact edge-count distributions of simple graphs.

For n vertices there are M=binom(n,2) possible independent undirected
edges. The number of labelled simple graphs with exactly k edges is C(M,k).
The checker *also* enumerates all 2**M masks to validate the evidence, so
an incorrect formula or corrupted histogram cannot be promoted as a result.
All certificates are explicitly about a fixed n<=5, not about a general Lean
or theorem-prover derivation of the binomial theorem.
"""
from __future__ import annotations
from math import comb
from .graph_model import edge_positions
from .graph_claims import digest

SCHEMA='axiom.graph.edge_count_distribution.v1'


def edge_count_histogram(n:int) -> dict:
    if type(n) is not int or not 0<=n<=5:
        raise ValueError('exact combinatorial histogram limited to n<=5')
    slots=len(edge_positions(n))
    values=[comb(slots,k) for k in range(slots+1)]
    return {'schema':SCHEMA,'order':n,'possible_edges':slots,
            'counts_by_number_of_edges':values,'total_labelled_graphs':sum(values),
            'originality':'KNOWN_COMBINATORIAL_IDENTITY','formal_verification':'NOT_PERFORMED',
            'statement_sha256':digest(['fixed_order_graph_edge_histogram',n])}


def check_edge_count_histogram(evidence:dict) -> bool:
    if type(evidence) is not dict or set(evidence)!={
        'schema','order','possible_edges','counts_by_number_of_edges',
        'total_labelled_graphs','originality','formal_verification','statement_sha256'}:
        raise ValueError('malformed finite graph histogram evidence')
    n=evidence['order']
    if type(n) is not int or not 0<=n<=5:
        raise ValueError('unsupported graph order')
    slots=len(edge_positions(n))
    if evidence['schema']!=SCHEMA or evidence['possible_edges']!=slots or \
            evidence['originality']!='KNOWN_COMBINATORIAL_IDENTITY' or \
            evidence['formal_verification']!='NOT_PERFORMED' or \
            evidence['statement_sha256']!=digest(['fixed_order_graph_edge_histogram',n]):
        raise ValueError('graph combinatorics certificate metadata invalid')
    # The verifying program enumerates every graph. No assumption about the
    # correctness of the producer's binomial-coefficient formula is needed.
    observed=[0]*(slots+1)
    for edge_mask in range(1<<slots):
        observed[edge_mask.bit_count()]+=1
    if type(evidence['counts_by_number_of_edges']) is not list or \
            any(type(c) is not int for c in evidence['counts_by_number_of_edges']) or \
            evidence['counts_by_number_of_edges']!=observed or \
            type(evidence['total_labelled_graphs']) is not int or \
            evidence['total_labelled_graphs']!=(1<<slots):
        raise ValueError('binomial distribution contradicted by exhaustive enumeration')
    return True
