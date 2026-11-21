from copy import deepcopy
import os
from pathlib import Path

import pytest

from axiom import graph_discovery
from axiom.graph_claims import digest
from axiom.graph_proof_beam import KNOWN_QUEUE
from axiom.graph_proof import HINT_ATTEMPT_SCHEMA, PLAN_SCHEMA, prove
from axiom.graph_proof_hints import HINT_SCHEMA
from axiom.graph_proof_pipeline import (
    CAMPAIGN_HINT_SCHEMA, PROFILE_SCHEMA, audit_composed_dispatch, dispatch_composed,
)
from axiom.graph_relations import AffineRelation


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


def test_extended_campaign_replays_strategies_and_statement_bound_hints(tmp_path, monkeypatch):
    historical = set(range(64)) | {(1 << 21) - 1}
    monkeypatch.setattr(graph_discovery, "_source", lambda *_: (
        "fixture", historical, {}, {}, set()))
    params = (tmp_path / "source", tmp_path / "ledger", "extended")
    report = graph_discovery.run_campaign(*params, proof_beam=8, holdout_budget=8, max_candidates=2)
    selected = report["trials"] + report["proof_beam"]["trials"]
    target = next(trial for trial in selected if AffineRelation.from_dict(trial["statement"]).bound.terms
                  == (("edges", -1), ("matching", 1), ("triangles", -1)))
    key = digest(target["statement"])
    manifest = {"schema": CAMPAIGN_HINT_SCHEMA, "hints": [
        {"schema": HINT_SCHEMA, "statement_sha256": key, "plans": [["matching_le_edges"]]},
    ]}
    project_root = Path(__file__).resolve().parents[1] if os.environ.get("AXIOM_REAL_LEAN") == "1" else tmp_path
    result = dispatch_composed(*params, proof_profile="extended", proof_hints=manifest,
                               project_root=project_root)
    assert result["schema"] == PROFILE_SCHEMA
    assert result["proof_configuration"]["hints"] == manifest
    assert [attempt["statement"] for attempt in result["results"]] == [trial["statement"] for trial in selected]
    hinted, = (a for a in result["results"] if a["schema"] == HINT_ATTEMPT_SCHEMA)
    assert hinted["statement_sha256"] == key
    assert hinted["proof_plans"]["candidates"][:2] == [[], ["matching_le_edges"]]
    assert hinted["proof_hints"]["hint_indices"][:2] == [None, 0]
    assert not hinted["derivation"]["derived"]
    if project_root != tmp_path:
        assert hinted["status"] == "FORMALLY_VERIFIED" and hinted["proof_plans"]["accepted_index"] == 1
    else:
        assert hinted["status"] == "LEAN_UNAVAILABLE"
    assert all(a["schema"] == PLAN_SCHEMA for a in result["results"] if a is not hinted)
    assert audit_composed_dispatch(*params, result) == result

    changed = deepcopy(result)
    changed["proof_configuration"]["timeout_seconds"] += 1
    with pytest.raises(ValueError, match="differs from discovery proof configuration"):
        audit_composed_dispatch(*params, changed)
    changed = deepcopy(result)
    changed["proof_configuration"]["hints"] = None
    with pytest.raises(ValueError, match="differs from discovery proof configuration"):
        audit_composed_dispatch(*params, changed)

    changed = deepcopy(result)
    changed["results"][result["results"].index(hinted)] = prove(
        target["statement"], provenance=hinted["provenance"],
        external_witness=target["counterexample"], project_root=tmp_path)
    with pytest.raises(ValueError, match="differs from discovery proof configuration"):
        audit_composed_dispatch(*params, changed)

    for invalid in (
        {"schema": CAMPAIGN_HINT_SCHEMA, "hints": [
            {**manifest["hints"][0], "statement_sha256": "0" * 64},
        ]},
        {"schema": CAMPAIGN_HINT_SCHEMA, "hints": manifest["hints"] * 2},
    ):
        with pytest.raises(ValueError, match="unique selected statement"):
            dispatch_composed(*params, proof_profile="extended", proof_hints=invalid,
                              project_root=tmp_path)
