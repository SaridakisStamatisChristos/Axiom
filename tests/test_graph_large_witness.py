from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from axiom.graph_checker import reference_properties
from axiom.graph_corpus import FEATURES, cheap_features, ingest, screen, summarize
from axiom.graph_explicit import ExplicitGraph
from axiom.graph_large_witness import certify_witness, minimize_witness, replay_witness
from axiom.graph_model import SimpleGraph
from axiom.graph_proof import audit, prove
from axiom.graph_relations import AffineRelation

FIXTURE = Path(__file__).resolve().parents[1] / "research" / "autographforge" / "larger-witnesses-v1.json"


@pytest.mark.parametrize("name", ["grotzsch", "barbell"])
def test_large_witness_native_proof_and_independent_replay(name):
    case = json.loads(FIXTURE.read_bytes())[name]
    claim = AffineRelation.from_dict(case["statement"])
    graph = ExplicitGraph.from_dict(case["graph"])
    assert graph.n > 7
    assert ExplicitGraph.from_graph6(graph.graph6()) == graph
    witness = certify_witness(claim, graph, origin=case["origin"])
    assert witness["left_hand_side"] == case["observed_lhs"]
    assert witness["right_hand_side"] == case["rhs"]
    result = prove(case["statement"], external_witness=witness, witness_order=0)
    assert result["status"] == "COUNTEREXAMPLE" and result["external_witness"] == witness
    audit(result)
    assert replay_witness(claim, witness)
    for key, tampered in (("graph_sha256", "00"), ("violated_direction", 100),
                          ("checked_properties", {**witness["checked_properties"], "matching": 0})):
        with pytest.raises(ValueError):
            replay_witness(claim, {**witness, key: tampered})
    altered = deepcopy(witness)
    altered["graph"]["edges"].pop()
    with pytest.raises(ValueError):
        replay_witness(claim, altered)
    wrong_premise = AffineRelation.normalized(dict(claim.bound.terms), claim.bound.upper, "BIPARTITE")
    with pytest.raises(ValueError):
        replay_witness(wrong_premise, witness)
    minimized = minimize_witness(claim, graph)
    assert (minimized.n, len(minimized.edges)) <= (graph.n, len(graph.edges))
    assert minimize_witness(claim, minimized) == minimized


def test_graph6_rejects_bad_padding_and_preserves_isolates():
    graph = ExplicitGraph.from_dict({"n": 64, "edges": [[63, 0], [62, 63]]})
    assert ExplicitGraph.from_graph6(">>graph6<<" + graph.graph6() + "\n") == graph
    for invalid in ("@?", "A~", "~???", "", "A!?"):
        with pytest.raises(ValueError):
            ExplicitGraph.from_graph6(invalid)


def test_vectorized_features_match_independent_exact_oracle():
    pytest.importorskip("numpy")
    graphs = [SimpleGraph.from_mask(n, mask) for n in range(5)
              for mask in range(1 << (n * (n - 1) // 2))]
    graph6 = [ExplicitGraph(graph.n, graph.edges).graph6() for graph in graphs]
    expected = [tuple(reference_properties(graph.n, graph.mask)[name] for name in FEATURES)
                for graph in graphs]
    assert cheap_features(graph6) == expected


def test_cross_split_duplicates_rollback_and_missing_features_are_counted(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    pytest.importorskip("networkx")
    monkeypatch.setattr("axiom.graph_corpus._canonicalize", lambda lines, _: lines)
    db = tmp_path / "corpus.sqlite"
    source = tmp_path / "input.g6"
    source.write_text("?\n@\n")
    ingest(db, source, sys.executable, family="dev", origin="test")
    initial = summarize(db)
    assert initial["unique_graph_count"] == 2
    ingest(db, source, sys.executable, family="dev", origin="test")
    assert summarize(db) == initial
    source.write_text("?\nA?\n")
    with pytest.raises(ValueError, match="another split"):
        ingest(db, source, sys.executable, family="final-set", origin="test", split="final")
    assert summarize(db, split="final")["unique_graph_count"] == 0
    assert summarize(db) == initial
    expensive = AffineRelation.normalized({"matching": 1, "n": -1}, 0)
    report = screen(db, expensive, 0)
    assert sum(row["missing_features"] for row in report["coverage_by_order"].values()) == 2
    assert screen(db, expensive, 2)["exact_graphs"] == 2
