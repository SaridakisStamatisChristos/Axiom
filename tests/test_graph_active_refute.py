import json
from pathlib import Path

import pytest

from axiom.graph_active_refute import search
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import replay_witness
from axiom.graph_relations import AffineRelation


@pytest.mark.parametrize("profile", ["mutation-v1", "portfolio-v2"])
def test_mutation_finds_triangle_from_a_satisfying_path_and_replays(profile):
    path = ExplicitGraph(3, ((0, 1), (1, 2)))
    no_triangles = AffineRelation.normalized({"triangles": 1}, 0, "CONNECTED")
    first = search(no_triangles, [path], seed=1729, budget=30, beam=2, profile=profile)
    assert first == search(no_triangles, [path], seed=1729, budget=30, beam=2, profile=profile)
    assert first["status"] == "REFUTED"
    assert replay_witness(no_triangles, first["witness"])
    assert first["counts"]["input"] == 1


def test_premise_guard_prevents_false_bipartite_witness():
    path = ExplicitGraph(3, ((0, 1), (1, 2)))
    claim = AffineRelation.normalized({"triangles": 1}, 0, "BIPARTITE")
    result = search(claim, [path], seed=2718, budget=30, beam=3)
    assert result["status"] == "NO_REFUTATION_OBSERVED" and result["evaluations"] == 30


def test_seedless_search_finds_dense_and_disconnected_witnesses():
    cases = [
        (AffineRelation.normalized({"clique": 1}, 5, "CONNECTED"), "family_complete"),
        (AffineRelation.normalized(
            {"n": 1, "independence": -1, "matching": -1, "maximum_degree": -1}, 0), "family_clique_union"),
    ]
    for claim, family in cases:
        result = search(claim, [], budget=512)
        assert result["status"] == "REFUTED"
        assert result["witness"]["origin"].endswith(f"operator={family}")
        assert replay_witness(claim, result["witness"])
        assert result["evaluations"] == sum(n for op, n in result["counts"].items()
                                            if op != "outside_premise")
        assert result["evaluations"] <= result["budget"]


def test_active_refutation_cli_can_find_and_replay_a_seedless_equality_witness(tmp_path, monkeypatch, capsys):
    from axiom.__main__ import main

    claim = AffineRelation.normalized({"chromatic": 1}, 2, "BIPARTITE", "=")
    path = tmp_path / "statement.json"
    path.write_text(json.dumps(claim.to_dict()))
    monkeypatch.setattr("sys.argv", ["axiom", "graph-active-refute", str(path), "--budget", "1"])
    main()
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "axiom.graph.active_refutation.v2"
    assert report["evaluations"] == 1
    assert report["witness"]["violated_direction"] == 1
    assert replay_witness(claim, report["witness"])


def test_portfolio_reports_no_witness_for_known_implications():
    directory = Path(__file__).resolve().parents[1] / "research" / "autographforge"
    controls = json.loads((directory / "implication-v1.json").read_bytes())["cases"]
    known = set(json.loads((directory / "implication-v1-expected.json").read_bytes())["known"])
    for name, premise, weights, rhs, relation in controls:
        if name in known:
            claim = AffineRelation.normalized(weights, rhs, premise, relation)
            result = search(claim, [], seed=2718, budget=128)
            assert result["status"] == "NO_REFUTATION_OBSERVED", name
