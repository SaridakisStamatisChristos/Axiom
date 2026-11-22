from itertools import combinations
import json
from pathlib import Path

import pytest

from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import exact_properties
from axiom.graph_model import SimpleGraph
from axiom.graph_transfer import InvariantValues, TransferStatement, check, replay

FIXTURES = Path(__file__).resolve().parents[1] / "research" / "autographforge"


def test_source_targets_normalize_and_domain_guards_reject_weakened_statements():
    source = json.loads((FIXTURES / "typed-literature-v1.json").read_bytes())
    assert len(source) == 6
    for data in source.values():
        parsed = TransferStatement.from_dict(data)
        assert TransferStatement.from_dict(parsed.to_dict()) == parsed
    with pytest.raises(ValueError, match="positive denominator"):
        TransferStatement.from_dict({**source["TXG-1"], "predicates": ["connected"]})
    with pytest.raises(ValueError, match="no-isolates"):
        TransferStatement.from_dict({**source["AGF-1"], "predicates": ["bipartite"]})
    k2 = ExplicitGraph(2, ((0, 1),))
    txg1 = TransferStatement.from_dict(source["TXG-1"])
    evidence = check(txg1, k2)
    assert (evidence["status"], evidence["left"], evidence["right"]) == ("COUNTEREXAMPLE", "2", "1")
    assert replay(txg1, evidence)
    with pytest.raises(ValueError, match="does not replay"):
        replay(txg1, {**evidence, "right": "2"})


def test_exact_transfer_invariants_against_independent_small_graph_enumeration():
    for n in range(5):
        for mask in range(1 << (n * (n - 1) // 2)):
            graph = ExplicitGraph(n, SimpleGraph.from_mask(n, mask).edges)
            values = InvariantValues(graph)
            assert values.independence == exact_properties(graph)["independence"]
            matchings = []
            covers = []
            for size in range(len(graph.edges) + 1):
                for group in combinations(graph.edges, size):
                    vertices = {v for edge in group for v in edge}
                    if len(vertices) == n:
                        covers.append(size)
                    if len(vertices) == size * 2 and all(a in vertices or b in vertices for a, b in graph.edges):
                        matchings.append(size)
            assert values.minimum_maximal_matching == min(matchings)
            if covers:
                assert values.edge_cover == min(covers)
            else:
                with pytest.raises(ValueError, match="isolated"):
                    _ = values.edge_cover
