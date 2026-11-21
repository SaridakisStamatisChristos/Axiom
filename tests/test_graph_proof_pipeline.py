from copy import deepcopy

import pytest

from axiom import graph_discovery
from axiom.graph_claims import digest
from axiom.graph_proof_beam import KNOWN_QUEUE
from axiom.graph_proof_pipeline import audit_composed_dispatch, dispatch_composed


def test_beam_selection_precedes_holdout_and_replays_exact_handoff(tmp_path, monkeypatch):
    # Deterministic historical-cohort fixture. The CI campaign uses the real
    # independently replayed historical database instead.
    historical = set(range(64)) | {(1 << 21) - 1}
    monkeypatch.setattr(graph_discovery, "_source", lambda *_: (
        "fixture", historical, {}, {}, set()))
    from axiom import graph_proof_beam

    calls = []
    beam, sample = graph_proof_beam.candidate_beam, graph_discovery.sample_stratum

    def before_holdout(training, width):
        assert not calls or calls[-1] == "holdout"
        assert set(training) == {5, 6, 7}
        calls.append("selection")
        return beam(training, width)

    def after_selection(*args):
        assert calls and "selection" in calls
        calls.append("holdout")
        return sample(*args)

    monkeypatch.setattr(graph_proof_beam, "candidate_beam", before_holdout)
    monkeypatch.setattr(graph_discovery, "sample_stratum", after_selection)
    params = (tmp_path / "source", tmp_path / "ledger", "opt-in")
    report = graph_discovery.run_campaign(*params, proof_beam=4, holdout_budget=8, max_candidates=1)
    assert report["selection_used_holdout_data"] is False
    opportunities = report["proof_beam"]["trials"]
    assert any(item["queue"] == KNOWN_QUEUE for item in opportunities)
    assert all(3 <= len(item["statement"]["bound"]["lhs"]) <= 4 for item in opportunities)
    assert not (historical & {mask for _, mask in graph_discovery._pairs(report)})
    dispatch = dispatch_composed(*params, project_root=tmp_path)
    assert any(result["derivation"] and result["derivation"]["derived"]
               for result in dispatch["results"] if result["provenance"]["queue"] == KNOWN_QUEUE)
    assert audit_composed_dispatch(*params, dispatch) == dispatch
    damaged = deepcopy(dispatch)
    attempt = damaged["results"][-1]
    attempt["provenance"]["selection_used_holdout_data"] = True
    attempt["record_sha256"] = digest({k: v for k, v in attempt.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="source-replayed"):
        audit_composed_dispatch(*params, damaged)
