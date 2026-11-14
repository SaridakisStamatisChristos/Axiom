"""AXIOM v0.16: historical coverage reconstruction and nonduplicative series."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from axiom.graph_campaign import _sample_masks
from axiom.graph_claims import GraphStatement
from axiom.graph_nonduplicate import (
    _configuration, _novel_masks, _sampled_masks, audit_iteration,
    run_iteration, _trial,
)


def test_historical_sample_replay_is_exact():
    original = {
        "method": "BOUNDED_LABELLED_GRAPH_SEARCH",
        "search_budget": 40, "seed": 42, "graph_order": 7,
        "structures_checked": 40, "labelled_graph_space": 1 << 21,
    }
    assert _sampled_masks(original, 7) == set(_sample_masks(7, 42, 40))
    corrupted = dict(original, structures_checked=39)
    with pytest.raises(ValueError):
        _sampled_masks(corrupted, 7)


def test_novel_mask_sequence_never_revisits_historical_graphs():
    forbidden = set(_sample_masks(7, 42, 256))
    first = _novel_masks("task:handshake", 42, 0, 256, forbidden)
    assert len(first) == len(set(first)) == 256
    assert not forbidden.intersection(first)
    second = _novel_masks("task:handshake", 42, 1, 256, forbidden | set(first))
    assert not set(second).intersection(set(first) | forbidden)
    assert first == _novel_masks("task:handshake", 42, 0, 256, forbidden)


def test_no_graph_sample_survivor_can_be_promoted():
    stmt = GraphStatement(7, "handshake").to_dict()
    task = {"task_id": "fixture:handshake", "statement_id": "fixture:statement",
            "action": "EXTEND_BOUNDED_FALSIFICATION", "statement": stmt}
    cfg = _configuration(0, 13, 8, 1)
    h = {"source_records": [], "distinct_historical_masks": 0,
         "historical_masks_sha256": "a" * 64}
    record = _trial(task, "b" * 64, cfg, set(), h)
    assert record["status"] == "SURVIVED_BOUNDED_SEARCH"
    assert record["formal_lean_verification"] == "NOT_PERFORMED"
    assert record["exhaustive"] is False


def test_invalid_budgets_fail_before_source_access(tmp_path):
    for overrides in ({"iteration": True}, {"iteration": 65},
                      {"search_budget": 0}, {"search_budget": 513},
                      {"task_limit": 0}, {"seed": -1}):
        params = {"iteration": 0, "seed": 42, "search_budget": 8, "task_limit": 2}
        params.update(overrides)
        with pytest.raises(ValueError):
            run_iteration(str(tmp_path / "absent.sqlite3"), str(tmp_path), **params)


def test_dual_oracle_refutation_does_not_depend_on_single_evaluator(monkeypatch):
    import axiom.graph_nonduplicate as module
    stmt = GraphStatement(7, "edges_le_vertices").to_dict()
    task = {"task_id": "fixture:false-edges", "statement_id": "fixture:false",
            "action": "EXTEND_BOUNDED_FALSIFICATION", "statement": stmt}
    cfg = _configuration(0, 42, 16, 1)
    h = {"source_records": [], "distinct_historical_masks": 0,
         "historical_masks_sha256": "a" * 64}
    record = _trial(task, "b" * 64, cfg, set(), h)
    assert record["status"] == "REFUTED"
    assert record["independent_discovery_crosscheck"] is True

    def false_discovery(n, mask):
        from axiom.graph_checker import reference_properties
        props = dict(reference_properties(n, mask))
        props["edges"] = 0  # Contradict the reference finding on purpose.
        return props

    monkeypatch.setattr(module, "_discovery_properties", false_discovery)
    with pytest.raises(ValueError, match="independent graph oracles disagree"):
        _trial(task, "b" * 64, cfg, set(), h)
