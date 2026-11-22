from axiom.graph_active_refute import search
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import replay_witness
from axiom.graph_relations import AffineRelation


def test_mutation_finds_triangle_from_a_satisfying_path_and_replays():
    path = ExplicitGraph(3, ((0, 1), (1, 2)))
    no_triangles = AffineRelation.normalized({"triangles": 1}, 0, "CONNECTED")
    first = search(no_triangles, [path], seed=1729, budget=30, beam=2)
    assert first == search(no_triangles, [path], seed=1729, budget=30, beam=2)
    assert first["status"] == "REFUTED"
    assert replay_witness(no_triangles, first["witness"])
    assert first["counts"]["input"] == 1


def test_premise_guard_prevents_false_bipartite_witness():
    path = ExplicitGraph(3, ((0, 1), (1, 2)))
    claim = AffineRelation.normalized({"triangles": 1}, 0, "BIPARTITE")
    result = search(claim, [path], seed=2718, budget=30, beam=3)
    assert result["status"] == "NO_REFUTATION_OBSERVED" and result["evaluations"] == 30
