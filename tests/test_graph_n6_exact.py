"""Exact six-vertex finite proof certificates, dual algorithms and falsifications."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from axiom.graph_claims import GraphStatement
from axiom.graph_checker import reference_properties
from axiom.graph_n6_exact import (
    N, LABELED_GRAPHS, SUPPORTED_TEMPLATES, DEFAULT_TEMPLATES,
    _facts_reference, _facts_discovery, check_n6_certificate,
    investigate_n6, research_n6, audit_n6, save_n6,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def full_campaign():
    return research_n6(list(DEFAULT_TEMPLATES) + ["edges_le_vertices"])


def test_correct_graph_space_size_and_two_independent_property_oracles():
    assert N == 6
    assert LABELED_GRAPHS == 2 ** (N * (N - 1) // 2) == 32768
    for mask in [0, 1, 3, 15, 63, 123, 511, 6143, 16383, 32767]:
        primary = _facts_discovery(mask)
        second = _facts_reference(mask)
        generic = reference_properties(N, mask)
        assert primary == second
        for property_name in primary:
            assert primary[property_name] == generic[property_name]


def test_exhaustive_certificates_and_real_counterexample(full_campaign):
    assert full_campaign["complete"] is True
    assert full_campaign["labelled_graph_space"] == 32768
    assert full_campaign["counts"] == {
        "PROVED_IN_SUPPORTED_FRAGMENT": len(DEFAULT_TEMPLATES),
        "REFUTED": 1,
    }
    assert full_campaign["formal_lean_verification"] == "NOT_PERFORMED"
    assert full_campaign["all_order_generalization"] == "NOT_PROVED"
    for finding in full_campaign["findings"]:
        assert finding["statement"]["n"] == N
        assert finding["labelled_graphs_checked"] == 32768
        assert finding["proof_scope"].endswith("exactly n=6 vertices")
        assert finding["originality"] == "NOT_ASSESSED"
        assert finding["all_order_generalization"] == "NOT_PROVED"
        if finding["status"] == "PROVED_IN_SUPPORTED_FRAGMENT":
            cert = finding["certificate"]
            assert cert is not None and cert["vacuous"] is False
            assert cert["labelled_graphs_checked"] == 32768
            assert cert["assumption_satisfying"] > 0
            assert finding["counterexample"] is None
            assert check_n6_certificate(finding["statement"], cert)
        else:
            assert finding["statement"]["template"] == "edges_le_vertices"
            assert finding["certificate"] is None
            assert finding["counterexample"]["n"] == N
            assert len(finding["counterexample"]["edges"]) > N


def test_exact_research_audit_and_non_mutating_report(full_campaign):
    snapshot = copy.deepcopy(full_campaign)
    result = audit_n6(full_campaign)
    assert result["audit"] == "ACCEPTED"
    assert result["exact_order"] == N
    assert result["labelled_graphs_per_statement"] == 32768
    assert result["formal_lean_verification"] == "NOT_PERFORMED"
    assert full_campaign == snapshot


def test_counterexample_rejected_as_certificate():
    statement = GraphStatement(6, "edges_le_vertices").to_dict()
    finding = investigate_n6("edges_le_vertices")
    assert finding["status"] == "REFUTED"
    assert finding["counterexample"] is not None
    assert finding["certificate"] is None
    forged = {
        "schema": "axiom.graph.n6.exact_certificate.v1",
        "method": "exhaustive_all_labelled_simple_graphs",
        "statement_sha256": "f" * 64,
        "order": 6,
        "labelled_graphs_checked": 32768,
        "assumption_satisfying": 32768,
        "vacuous": False,
        "proof_scope": "ALL labelled simple graphs with exactly n=6 vertices",
        "formal_lean_verification": "NOT_PERFORMED",
    }
    with pytest.raises(ValueError):
        check_n6_certificate(statement, forged)


def test_reject_altered_proof_metadata_and_scope(full_campaign):
    proven = next(f for f in full_campaign["findings"]
                  if f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT")
    stmt = proven["statement"]
    cert = proven["certificate"]
    for changes in [
        {"order": 5}, {"labelled_graphs_checked": 1024},
        {"labelled_graphs_checked": 32767},
        {"proof_scope": "for all n"}, {"formal_lean_verification": "FORMALLY_VERIFIED"},
        {"statement_sha256": "a" * 64}, {"vacuous": True},
        {"assumption_satisfying": cert["assumption_satisfying"] - 1},
    ]:
        bad = dict(cert, **changes)
        with pytest.raises(ValueError):
            check_n6_certificate(stmt, bad)
    other_order = GraphStatement(5, stmt["template"]).to_dict()
    with pytest.raises(ValueError):
        check_n6_certificate(other_order, cert)


def test_reject_duplicate_unsupported_or_malformed_claims():
    for names in [
        [], ["handshake", "handshake"], ["clique_le_chromatic"],
        ["handshake"] * 10, ["handshake", None],
    ]:
        with pytest.raises(ValueError):
            research_n6(names)
    with pytest.raises(ValueError):
        investigate_n6("clique_le_chromatic")
    for mask in [-1, 32768, True]:
        with pytest.raises(ValueError):
            _facts_reference(mask)
    with pytest.raises(ValueError):
        check_n6_certificate(GraphStatement(6, "handshake").to_dict(), {})


def test_report_tampering_and_false_generalization_fail_closed(tmp_path):
    report = research_n6(["handshake"])
    assert audit_n6(report)["audit"] == "ACCEPTED"
    corrupted = copy.deepcopy(report)
    corrupted["findings"][0]["all_order_generalization"] = "PROVED_FOR_ALL_N"
    with pytest.raises(ValueError, match="independent exhaustive replay"):
        audit_n6(corrupted)
    corrupted = copy.deepcopy(report)
    corrupted["findings"][0]["certificate"]["labelled_graphs_checked"] = 5
    with pytest.raises(ValueError):
        audit_n6(corrupted)
    corrupted = copy.deepcopy(report)
    corrupted["configuration"]["order"] = 7
    with pytest.raises(ValueError):
        audit_n6(corrupted)


def test_cli_runs_and_independently_audits_saved_exact_n6_report(tmp_path):
    output = tmp_path / "n6.json"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    command = [sys.executable, "-m", "axiom"]

    def cli(*args):
        return subprocess.run(command + list(args),
                              text=True, capture_output=True, env=env)

    run = cli("graph-n6-run", "--templates", "handshake", "edges_le_vertices",
              "--output", str(output))
    assert run.returncode == 0, run.stderr
    report = json.loads(output.read_text())
    assert report["counts"] == {
        "PROVED_IN_SUPPORTED_FRAGMENT": 1, "REFUTED": 1}
    accepted = cli("graph-n6-audit", str(output))
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(accepted.stdout)["audit"] == "ACCEPTED"
    result = next(f for f in report["findings"]
                  if f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT")
    cert_file = tmp_path / "proof.json"
    cert_file.write_text(json.dumps({
        "statement": result["statement"], "certificate": result["certificate"]}))
    checked = cli("graph-n6-check-certificate", str(cert_file))
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["labelled_graphs_exhaustively_checked"] == 32768
    assert cli("graph-n6-run", "--templates", "clique_le_chromatic",
               "--output", str(output)).returncode != 0
