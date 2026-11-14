"""Graph Lean v0.15: scope, source binding, real-kernel nonpromotion safeguards."""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from axiom.graph_n6_exact import research_n6
from axiom.graph_lean import (
    SUPPORTED, LeanBackendError, build_graph_lean_source,
    verify_graph_with_lean, audit_graph_lean_record, save_record,
)
from axiom.graph_research_executor import execute_graph_research


@pytest.fixture(scope="module")
def source():
    report = research_n6(["handshake"])
    finding = report["findings"][0]
    assert finding["status"] == "PROVED_IN_SUPPORTED_FRAGMENT"
    return finding["statement"], finding["certificate"]


def test_closed_graph_encoding_and_nonvacuous_source(source):
    statement, certificate = source
    generated = build_graph_lean_source(statement, certificate)
    assert generated["statement"]["n"] == 6
    assert generated["scope"].startswith("ALL labelled simple graphs with exactly n=6")
    assert generated["all_order_generalization"] == "NOT_PROVED"
    assert "bit mask 14" in generated["source"]
    assert "bit mask 15" not in generated["source"]
    assert "degreeSum mask = 2 * edgeCount mask" in generated["source"]
    assert "#print axioms AxiomGraphN6." not in generated["source"]  # unqualified *inside* namespace
    assert "#print axioms axiom_graph_n6_" in generated["source"]
    assert "sorry" not in generated["source"]
    assert "native_decide" not in generated["source"]


def test_malformed_certificate_and_changed_statement_are_rejected(source):
    statement, certificate = source
    bogus = copy.deepcopy(certificate)
    bogus["labelled_graphs_checked"] = 32767
    with pytest.raises(LeanBackendError):
        build_graph_lean_source(statement, bogus)
    bogus = copy.deepcopy(statement)
    bogus["n"] = 7
    with pytest.raises(LeanBackendError):
        build_graph_lean_source(bogus, certificate)
    bogus = copy.deepcopy(statement)
    bogus["template"] = "edges_le_vertices"
    with pytest.raises(LeanBackendError):
        build_graph_lean_source(bogus, certificate)


def test_no_lean_is_not_formal_proof(source, tmp_path, monkeypatch):
    statement, certificate = source
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    (tmp_path / "lakefile.toml").write_text((Path(__file__).resolve().parents[1] / "lakefile.toml").read_text())
    monkeypatch.setattr(shutil, "which", lambda _: None)
    record = verify_graph_with_lean(statement, certificate, project_root=tmp_path)
    assert record["status"] == "LEAN_UNAVAILABLE"
    assert record["accepted"] is False
    assert audit_graph_lean_record(record)
    forged = copy.deepcopy(record)
    forged["status"] = "FORMALLY_VERIFIED"
    forged["accepted"] = True
    with pytest.raises(LeanBackendError):
        audit_graph_lean_record(forged)
    forged = copy.deepcopy(record)
    forged["source"] += "\nsorry"
    with pytest.raises(LeanBackendError):
        audit_graph_lean_record(forged)
    path = tmp_path / "record.json"
    save_record(record, path)
    assert json.loads(path.read_text())["source_sha256"] == record["source_sha256"]


def test_orchestrator_validates_budget_before_auditing(tmp_path):
    for bad in (0, 8, True, "3"):
        with pytest.raises(ValueError):
            execute_graph_research(str(tmp_path / "missing.db"),
                                   str(tmp_path / "output"), max_proofs=bad)
    with pytest.raises(ValueError):
        execute_graph_research(str(tmp_path / "missing.db"),
                               str(tmp_path / "output"), timeout_seconds=0)
