"""AXIOM v0.9: bounded cross-order conjecture transfer, no false theorems."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from axiom.graph_checker import check_graph_witness
from axiom.graph_frontier import (
    load_graph_sources, frontier_plan, research_frontier,
    audit_frontier, run_frontier)

ROOT = Path(__file__).parents[1]
SOURCES = [
    str(ROOT / "research/graphs/v05_baseline_report.json"),
    str(ROOT / "research/graphs/v05_scale_report.json")]


@pytest.fixture(scope="module")
def historical():
    return load_graph_sources(SOURCES)


@pytest.fixture(scope="module")
def six(historical):
    return research_frontier(historical, seed=42, target_order=6,
                             search_budget=256, max_candidates=24)


@pytest.fixture(scope="module")
def seven(historical):
    return research_frontier(historical, seed=42, target_order=7,
                             search_budget=256, max_candidates=24)


def test_all_probes_replayed_and_no_universal_proofs(six, historical):
    summary = audit_frontier(six, historical)
    assert summary["audit"] == "ACCEPTED"
    assert summary["proofs_at_target_order"] == 0
    assert six["candidate_count"] > 0
    assert six["source_proof_scope"] == "original finite graph theorems hold at exactly n=5"
    assert six["novelty"] == "NOT_ASSESSED"
    for finding in six["findings"]:
        assert finding["statement"]["n"] == 6
        assert finding["proof"] is None
        assert finding["status"] in {"REFUTED", "EXPERIMENTALLY_SUPPORTED"}
        assert finding["formal_lean_verification"] == "NOT_PERFORMED"
        assert finding["logical_implication_from_n5"] is False
        assert finding["generalization_to_all_orders"] == "NOT_PROVED"
        assert finding["source_proofs"]
        assert all(item["proven_scope"] == "exact order n=5 only"
                   for item in finding["source_proofs"])
        if finding["status"] == "REFUTED":
            assert check_graph_witness(finding["statement"],
                                       finding["search"]["counterexample"])
        else:
            assert finding["search"]["counterexample"] is None
            assert finding["search"]["scope"].startswith("bounded explicit labelled")
    assert six["counts"]["REFUTED"] >= 1


def test_order_seven_is_independent_scope(seven, historical):
    assert audit_frontier(seven, historical)["audit"] == "ACCEPTED"
    assert seven["candidate_count"] > 0
    assert all(f["statement"]["n"] == 7 and f["proof"] is None
               for f in seven["findings"])
    assert seven["campaign_id"] != research_frontier(
        historical, seed=42, target_order=6,
        search_budget=256, max_candidates=24)["campaign_id"]


def test_deterministic_replay(six, historical):
    assert six == research_frontier(
        historical, seed=42, target_order=6,
        search_budget=256, max_candidates=24)


def test_bounded_search_enforced_and_no_false_promotion(six, historical):
    forged = copy.deepcopy(six)
    forged["findings"][0]["status"] = "PROVED_IN_SUPPORTED_FRAGMENT"
    with pytest.raises(ValueError, match="independent deterministic replay"):
        audit_frontier(forged, historical)
    forged = copy.deepcopy(six)
    forged["findings"][0]["logical_implication_from_n5"] = True
    with pytest.raises(ValueError):
        audit_frontier(forged, historical)
    forged = copy.deepcopy(six)
    forged["findings"][0]["search"]["method"] = "EXHAUSTIVE_ISOMORPHISM_CLASSES"
    with pytest.raises(ValueError):
        audit_frontier(forged, historical)


def test_counterexample_tampering_rejected(six, historical):
    failures = [i for i, x in enumerate(six["findings"]) if x["status"] == "REFUTED"]
    assert failures
    forged = copy.deepcopy(six)
    idx = failures[0]
    forged["findings"][idx]["search"]["counterexample"] = None
    with pytest.raises(ValueError):
        audit_frontier(forged, historical)


def test_missing_and_partial_sources_rejected(tmp_path):
    fake = json.loads(Path(SOURCES[0]).read_text())
    fake["progress"]["complete"] = False
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(fake))
    with pytest.raises(ValueError):
        load_graph_sources([str(path)])
    with pytest.raises(ValueError):
        load_graph_sources([])
    with pytest.raises((OSError, ValueError)):
        load_graph_sources([str(tmp_path / "missing.json")])


def test_unobserved_priority_and_redundant_budget_filter(historical):
    plan = frontier_plan(historical, target_order=6,
                         search_budget=256, max_candidates=200)
    assert plan
    observed = [p["selection_reason"] for p in plan]
    if "UNTESTED_TARGET_ORDER" in observed:
        first_repeat = next((i for i, x in enumerate(observed)
                             if x != "UNTESTED_TARGET_ORDER"), len(observed))
        assert all(x == "UNTESTED_TARGET_ORDER" for x in observed[:first_repeat])
    assert all(p["prior_target_evidence"] == [] or
               max(x["search_budget"] for x in p["prior_target_evidence"]) < 256
               for p in plan)
    small_plan = frontier_plan(historical, target_order=6,
                               search_budget=128, max_candidates=200)
    assert len(small_plan) <= len(plan)
    # None of the already refuted exact targets may be re-proposed.
    by_family = {(p["statement"]["template"], p["statement"]["k"])
                 for p in plan}
    for source in historical:
        for finding in source["findings"]:
            if finding["statement"]["n"] == 6 and finding["status"] == "REFUTED":
                key = (finding["statement"]["template"], finding["statement"]["k"])
                assert key not in by_family


def test_invalid_config_and_source_tampering(historical):
    for kwargs in [
        {"target_order": 5},
        {"target_order": 8},
        {"search_budget": 0},
        {"max_candidates": 0},
    ]:
        with pytest.raises(ValueError):
            research_frontier(historical, **kwargs)
    report = copy.deepcopy(historical[0])
    report["findings"][0]["originality"] = "NOVEL"
    with pytest.raises(ValueError):
        research_frontier([report])


def test_cli_produces_independently_auditable_evidence(tmp_path):
    output = tmp_path / "n6.json"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    base = [sys.executable, "-m", "axiom"]

    run = subprocess.run(base + [
        "graph-frontier-run", "--target-order", "6",
        "--search-budget", "256", "--max-candidates", "8",
        "--output", str(output), *SOURCES],
        capture_output=True, text=True, env=env)
    assert run.returncode == 0, run.stderr
    report = json.loads(output.read_text())
    assert report["candidate_count"] == 8
    audit = subprocess.run(base + [
        "graph-frontier-audit", str(output), *SOURCES],
        capture_output=True, text=True, env=env)
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout)["audit"] == "ACCEPTED"
    report["findings"][0]["formal_lean_verification"] = "FORMALLY_VERIFIED"
    output.write_text(json.dumps(report))
    failed = subprocess.run(base + [
        "graph-frontier-audit", str(output), *SOURCES],
        capture_output=True, text=True, env=env)
    assert failed.returncode != 0


def test_preserved_ci_research_digest_and_explicit_refutations(six, seven, historical):
    """A durable release ledger must match fully recomputed mathematical evidence."""
    import hashlib
    from axiom.graph_claims import GraphStatement, digest

    ledger = json.loads((ROOT / "research/graphs/v09_results_summary.json").read_text())
    assert ledger["schema"] == "axiom.graph.frontier.research_release_summary.v1"
    assert ledger["target_order_proofs"] == 0
    assert ledger["novelty"] == "NOT_ASSESSED"
    expected_sources = {x["campaign_id"]: x["sha256"]
                        for x in ledger["source_reports"]}
    assert expected_sources == {r["campaign_id"]: digest(r) for r in historical}
    totals = {"candidates": 0, "refuted": 0, "surviving": 0}
    for record, report in zip(ledger["reports"], (six, seven)):
        assert report["configuration"]["max_candidates"] == 24  # actual set below quota
        assert report["candidate_count"] <= 24
        assert report["configuration"]["target_order"] == record["order"]
        assert record["campaign_id"] == report["campaign_id"]
        file_content = json.dumps(report, indent=2, sort_keys=True) + "\n"
        assert hashlib.sha256(file_content.encode()).hexdigest() == record["report_sha256"]
        assert record["candidates"] == report["candidate_count"]
        assert record["refuted"] == report["counts"]["REFUTED"]
        assert (record["experimentally_supported_not_proved"] ==
                report["counts"]["EXPERIMENTALLY_SUPPORTED"])
        totals["candidates"] += record["candidates"]
        totals["refuted"] += record["refuted"]
        totals["surviving"] += record["experimentally_supported_not_proved"]
    assert totals == {"candidates": 39, "refuted": 3, "surviving": 36}
    assert len(ledger["refutations"]) == 3
    for counterexample in ledger["refutations"]:
        statement = GraphStatement(
            counterexample["order"], counterexample["template"],
            counterexample["k"])
        n = counterexample["order"]
        assert len(counterexample["witness_edges"]) == counterexample["observed_edge_count"]
        assert counterexample["observed_edge_count"] > n + counterexample["k"]
        assert counterexample["claimed_max_edges"] == n + counterexample["k"]
        assert check_graph_witness(statement.to_dict(),
                                   {"n": n, "edges": counterexample["witness_edges"]})
