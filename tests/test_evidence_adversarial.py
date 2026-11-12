"""Negative report tampering and independent witness-validation coverage."""
import copy
import pytest
from axiom.evidence import audit_report
from axiom.research import run_campaign


def test_report_search_evidence_tampering_rejected(tmp_path):
    report = run_campaign(str(tmp_path / 'r.db'), seed=21, candidates=45, domain='mixed')
    sample = copy.deepcopy(report)
    sample['findings'][0]['search']['tested'] += 1
    with pytest.raises(ValueError, match='search evidence'):
        audit_report(sample)


def test_report_formal_verification_forgery_rejected(tmp_path):
    report = run_campaign(str(tmp_path / 'r.db'), seed=21, candidates=45, domain='mixed')
    sample = copy.deepcopy(report)
    sample['findings'][0]['status'] = 'FORMALLY_VERIFIED'
    sample['findings'][0]['history'].append('FORMALLY_VERIFIED')
    with pytest.raises(ValueError, match='evidence-state'):
        audit_report(sample)


def test_report_counterexample_forgery_rejected(tmp_path):
    report = run_campaign(str(tmp_path / 'r.db'), seed=21, candidates=45, domain='mixed')
    sample = copy.deepcopy(report)
    f = next(x for x in sample['findings'] if x['status'] == 'REFUTED')
    for v in f['search']['counterexample']:
        f['search']['counterexample'][v] = 10**40
    with pytest.raises(ValueError, match='refutation'):
        audit_report(sample)
