"""Check branch scope, shared budgets and deterministic certificate replay."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from axiom.graph_affine_lean_n3 import run_affine_kernel
from axiom.graph_claims import digest
from axiom.graph_order_split import proof_body
from axiom.graph_proof import SPLIT_SCHEMA, audit, prove
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation
from axiom.graph_universal_lean import PINNED_MATHLIB_SHA, _render_source

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "research/proof_engine/order_split_targets.json"


@pytest.mark.parametrize("_name,premise,weights,rhs,local_fact", json.loads(SUITE.read_text()))
def test_order_partition_extends_synthesis(tmp_path, _name, premise, weights, rhs, local_fact):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    kwargs = dict(project_root=tmp_path, retrieval_limit=5, synthesis_limit=3)
    before = prove(statement, **kwargs)
    after = prove(statement, split_order=True, **kwargs)
    assert before["status"] == "SEARCH_EXHAUSTED"
    assert after["schema"] == SPLIT_SCHEMA and after["status"] == "LEAN_UNAVAILABLE"
    split = after["order_split"]
    assert split["attempted"] and split["initial_derivation"] == before["derivation"]
    assert local_fact in split["positive_facts"]
    assert split["zero_branch"] == ("CONNECTED_IMPOSSIBLE" if premise == "CONNECTED" else "ZERO_INVARIANTS")
    assert after["derivation"]["nodes"] > before["derivation"]["nodes"]
    source = after["generated"]["source"]
    zero, positive = source.split("by_cases hz : n = 0\n", 1)[1].split("  · have hn", 1)
    assert f"have {local_fact}" in positive
    assert f"have {local_fact}" not in zero
    assert audit(before) and audit(after)


def test_order_partition_preserves_counterexamples_and_budget(tmp_path):
    statement = AffineRelation.normalized({"maximum_degree": 1, "n": -1}, -1).to_dict()
    witness = prove(statement, split_order=True, project_root=tmp_path)
    assert witness["status"] == "COUNTEREXAMPLE" and witness["generated"] is None
    assert not witness["order_split"]["attempted"] and audit(witness)
    with pytest.raises(ValueError, match="invalid order split option"):
        prove(statement, split_order=1)

    statement = AffineRelation.normalized({"maximum_degree": 1, "n": -1}, 0).to_dict()
    exhausted = prove(statement, split_order=True, limits=SearchLimits(max_nodes=1), project_root=tmp_path)
    assert exhausted["reason"] == "NODE_BUDGET_EXHAUSTED"
    assert not exhausted["order_split"]["attempted"] and audit(exhausted)

    before = prove(statement, project_root=tmp_path)
    limits = SearchLimits(max_nodes=before["derivation"]["nodes"] + 1)
    during = prove(statement, split_order=True, limits=limits, project_root=tmp_path)
    assert during["reason"] == "NODE_BUDGET_EXHAUSTED" and during["generated"] is None
    assert during["order_split"]["attempted"] and during["derivation"]["nodes"] == limits.max_nodes
    assert audit(during)

    found = prove(statement, split_order=True, project_root=tmp_path)
    bad = deepcopy(found)
    bad["order_split"]["zero_branch"] = "CONNECTED_IMPOSSIBLE"
    bad["record_sha256"] = digest({k: v for k, v in bad.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(bad)


@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
@pytest.mark.parametrize("terms", [
    ("edges", "triangles", "matching", "independence"),
    ("maximum_degree", "clique", "components", "chromatic"),
])
def test_lean_checks_every_empty_invariant(terms):
    claim = AffineRelation.normalized(dict.fromkeys(terms, -1), 0)
    name = "order_split_zero_probe"
    source = _render_source(claim, name, "", proof_body=proof_body(claim, (), ()))
    record = run_affine_kernel(
        {"source": source, "theorem": f"AxiomGraphUniversal.{name}"},
        ROOT, 180, "FORMALLY_VERIFIED", expected_mathlib_revision=PINNED_MATHLIB_SHA,
        retain_logs=True,
    )
    assert record["accepted"], (record["status"], record["stdout"], record["stderr"])
