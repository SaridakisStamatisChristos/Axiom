"""Independent source-binding audit; does not simulate real kernel execution."""
from __future__ import annotations
import copy
import json
import pytest
from axiom.number_theory_campaign import run_nt_campaign
from axiom.number_theory_lean import (verify_nt_report,audit_nt_lean_report)
from axiom.lean_backend import LeanBackendError


def test_audit_pending_records_cannot_claim_verified(tmp_path):
    from unittest.mock import patch
    report=run_nt_campaign(str(tmp_path/'db.sqlite3'),candidates=35,max_evals=100)
    results=tmp_path/'formal'
    with patch('axiom.number_theory_lean.shutil.which',return_value=None):
        summary=verify_nt_report(report,project_root=tmp_path.parents[0],output_dir=results,limit=3)
    assert summary['attempted']==3
    assert summary['formally_verified']==0
    checked=audit_nt_lean_report(report,results,expected_attempts=3)
    assert checked['formally_verified']==0
    with pytest.raises(LeanBackendError):
        audit_nt_lean_report(report,results,expected_attempts=3,require_verified=True)
    with pytest.raises(LeanBackendError):
        audit_nt_lean_report(report,results,expected_attempts=4)


def test_batch_source_binding_and_summary_forgeries_rejected(tmp_path):
    from unittest.mock import patch
    report=run_nt_campaign(str(tmp_path/'db.sqlite3'),candidates=30,max_evals=100)
    dest=tmp_path/'out'
    with patch('axiom.number_theory_lean.shutil.which',return_value=None):
        summary=verify_nt_report(report,project_root=tmp_path,output_dir=dest,limit=2)
    assert audit_nt_lean_report(report,dest,expected_attempts=2)
    key=summary['results'][0]['candidate_id'][:24]
    path=dest/(key+'.json')
    original=json.loads(path.read_text())
    damaged=copy.deepcopy(original)
    damaged['source']+='\nby sorry\n'
    path.write_text(json.dumps(damaged))
    with pytest.raises(LeanBackendError):audit_nt_lean_report(report,dest)
    path.write_text(json.dumps(original))
    total=dest/'summary.json'
    data=json.loads(total.read_text());data['formally_verified']=500
    total.write_text(json.dumps(data))
    with pytest.raises(LeanBackendError):audit_nt_lean_report(report,dest)
