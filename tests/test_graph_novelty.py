from copy import deepcopy
import json
from pathlib import Path

import pytest

from axiom.graph_affine import check_conjecture
from axiom.graph_checker import reference_properties
from axiom.graph_model import edge_positions
from axiom.graph_novelty import NoveltyFilter, dominates, verify_direction
from axiom.graph_relations import AffineRelation

FIXTURES = Path(__file__).resolve().parents[1] / "research" / "autographforge"


def read(name):
    return json.loads((FIXTURES / name).read_bytes())


def test_certified_filter_catches_all_six_bipartite_variants_and_replays(monkeypatch):
    claims = [AffineRelation.from_dict(row["statement"]) for row in read("discovery-v7.json").values()
              if row["statement"]["relation"] == "="
              and row["statement"]["bound"]["assumption"] == "BIPARTITE"
              and row["statement"]["bound"]["lhs"][0]["symbol"] == "chromatic"
              and {"seed": 1729, "lane": "OPEN_PROOF_TARGET"} in row["selections"]]
    assert len(claims) == 6
    run = NoveltyFilter()
    assert all(run.classify(claim) for claim in claims)
    evidence = run.report()
    monkeypatch.setattr("axiom.graph_novelty._propose", lambda _: pytest.fail("solver ran in audit"))
    replay = NoveltyFilter(evidence)
    assert all(replay.classify(claim) for claim in claims)
    assert replay.report() == evidence
    bad = deepcopy(evidence)
    bad["decisions"][claims[0].id]["directions"][0]["support"][0][1] += 1
    with pytest.raises(ValueError, match="novelty"):
        NoveltyFilter(bad).classify(claims[0])


def test_cross_premise_implications_and_seeded_false_controls():
    cases = read("implication-v1.json")["cases"]
    labels = read("implication-v1-expected.json")
    run = NoveltyFilter()
    outcomes = {}
    for name, premise, weights, rhs, relation in cases:
        claim = AffineRelation.normalized(weights, rhs, premise, relation)
        outcomes[name] = run.classify(claim)
        if name in labels["false_witnesses"]:
            order, edges = labels["false_witnesses"][name]
            positions = edge_positions(order)
            mask = sum(1 << positions.index(tuple(edge)) for edge in edges)
            graph = reference_properties(order, mask)
            assert any(applies and not valid for applies, valid, _ in
                       (check_conjecture(side, graph) for side in claim.inequalities()))
            assert not outcomes[name]
    assert sum(outcomes[key] for key in labels["known"]) / len(labels["known"]) >= 0.95


def test_fractional_certificates_and_scope_guard():
    claim = AffineRelation.normalized({"matching": 1, "n": -1}, 0)
    valid = [["nonnegative_n", 1, 2], ["retrieved_twice_matching_le_order", 1, 2]]
    assert verify_direction(claim.bound, valid)
    assert not verify_direction(claim.bound, [valid[0], valid[1], valid[1]])
    assert not verify_direction(claim.bound, [valid[0], [valid[1][0], -1, 2]])
    all_graphs = AffineRelation.normalized({"n": 1, "edges": -1}, 1)
    assert not verify_direction(all_graphs.bound, [["connected_edge_bound", 1, 1]])
    a = AffineRelation.normalized({"edges": 1, "clique": -1}, 4, "BIPARTITE")
    b = AffineRelation.normalized({"edges": 1, "chromatic": -1, "triangles": 2}, 4, "BIPARTITE")
    w = AffineRelation.normalized({"edges": 1, "clique": -1}, 4, "TRIANGLE_FREE")
    assert dominates(a, b) and dominates(b, a)
    assert dominates(w, a) and not dominates(a, w)
