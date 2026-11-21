"""Exercise bounded proof plans, feedback and deterministic record replay."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from axiom.graph_claims import digest
from axiom.graph_proof import PLAN_SCHEMA, audit, prove
from axiom.graph_proof_plans import accepted_plan
from axiom.graph_proof_search import SearchLimits
from axiom.graph_relations import AffineRelation

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "research/proof_engine/proof_plan_targets.json"
OPTIONS = dict(retrieval_limit=5, synthesis_limit=3, split_order=True, induct_edges=True)
MATCHING = {"matching": 5, "edges": -6}


@pytest.mark.parametrize("_name,premise,weights,rhs,expected", json.loads(SUITE.read_text()))
def test_plan_generation_is_bounded_and_replayable(tmp_path, _name, premise, weights, rhs, expected):
    statement = AffineRelation.normalized(weights, rhs, premise).to_dict()
    baseline = prove(statement, project_root=tmp_path, **OPTIONS)
    result = prove(statement, plan_limit=16, project_root=tmp_path, **OPTIONS)
    plans = result["proof_plans"]
    assert baseline["status"] == "SEARCH_EXHAUSTED"
    assert result["schema"] == PLAN_SCHEMA and result["status"] == "LEAN_UNAVAILABLE"
    assert result["derivation"] == baseline["derivation"]
    assert plans["candidates"][0] == [] and plans["accepted_index"] is None
    assert 1 <= len(plans["candidates"]) <= 16
    assert result["derivation"]["nodes"] + len(plans["candidates"]) <= result["search_limits"]["max_nodes"]
    assert all(len(bundle) <= result["search_limits"]["max_lemmas"] for bundle in plans["candidates"])
    assert any(set(expected) <= set(bundle) for bundle in plans["candidates"])
    assert result["generated"]["source"].count('trace "AXIOM_ACCEPTED_PLAN:') == len(plans["candidates"])
    assert audit(baseline) and audit(result)

    altered = deepcopy(result)
    altered["proof_plans"]["candidates"].reverse()
    altered["record_sha256"] = digest({k: v for k, v in altered.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(altered)


def test_plan_limits_and_precedence(tmp_path):
    claim = AffineRelation.normalized(MATCHING, 0).to_dict()
    baseline = prove(claim, project_root=tmp_path)
    nodes = baseline["derivation"]["nodes"]
    for extra in (0, 1):
        result = prove(claim, plan_limit=16, limits=SearchLimits(max_nodes=nodes + extra),
                       project_root=tmp_path)
        assert len(result["proof_plans"]["candidates"]) == extra
        assert (result["generated"] is not None) == bool(extra)
        if not extra:
            assert result["reason"] == "NODE_BUDGET_EXHAUSTED"
        assert audit(result)
    for invalid in (True, -1, 17):
        with pytest.raises(ValueError, match="invalid proof plan limit"):
            prove(claim, plan_limit=invalid)

    witness = prove(AffineRelation.normalized({"clique": 1}, 1).to_dict(), plan_limit=16,
                    project_root=tmp_path)
    assert witness["status"] == "COUNTEREXAMPLE" and not witness["proof_plans"]["candidates"]
    assert witness["generated"] is None and audit(witness)

    known = AffineRelation.normalized({"matching": 1, "edges": -1}, 0).to_dict()
    expected = prove(known, project_root=tmp_path)
    result = prove(known, plan_limit=16, project_root=tmp_path)
    assert result["generated"] == expected["generated"] and not result["proof_plans"]["candidates"]
    assert audit(result)


@pytest.mark.parametrize("log", ["", "AXIOM_ACCEPTED_PLAN:3\n",
                                 "AXIOM_ACCEPTED_PLAN:1\nAXIOM_ACCEPTED_PLAN:2\n"])
def test_feedback_requires_exactly_one_valid_index(log):
    with pytest.raises(ValueError, match="invalid Lean proof-plan feedback"):
        accepted_plan(log, 3)


@pytest.mark.skipif(os.environ.get("AXIOM_REAL_LEAN") != "1", reason="requires pinned Lean and Mathlib")
def test_lean_backtracks_and_reports_only_completed_plans():
    statement = AffineRelation.normalized(MATCHING, 0).to_dict()
    rejected = prove(statement, plan_limit=1, project_root=ROOT)
    assert rejected["status"] == "LEAN_REJECTED" and rejected["kernel"]["lean_kernel_executed"]
    assert rejected["proof_plans"]["accepted_index"] is None
    assert "AXIOM proof plans exhausted" in rejected["kernel"]["stdout"]
    assert "AXIOM_ACCEPTED_PLAN:" not in rejected["kernel"]["stdout"]
    assert audit(rejected)

    verified = prove(statement, plan_limit=2, project_root=ROOT)
    assert verified["status"] == "FORMALLY_VERIFIED" and verified["kernel"]["lean_kernel_executed"]
    assert verified["proof_plans"]["accepted_index"] == 1
    assert verified["proof_plans"]["candidates"] == [[], ["matching_le_edges"]]
    assert audit(verified)
    tampered = deepcopy(verified)
    tampered["proof_plans"]["accepted_index"] = 0
    tampered["record_sha256"] = digest({k: v for k, v in tampered.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="deterministic replay"):
        audit(tampered)

    # A true kernel result must include the expected feedback marker even
    # when a caller recomputes both public digests.
    missing = deepcopy(verified)
    missing["kernel"]["stdout"] = missing["kernel"]["stdout"].replace("AXIOM_ACCEPTED_PLAN:1\n", "")
    missing["kernel"]["stdout_sha256"] = sha256(missing["kernel"]["stdout"].encode()).hexdigest()
    missing["record_sha256"] = digest({k: v for k, v in missing.items() if k != "record_sha256"})
    with pytest.raises(ValueError, match="invalid Lean proof-plan feedback"):
        audit(missing)
