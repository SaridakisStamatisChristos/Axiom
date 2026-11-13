import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from axiom.formal_campaign import verify_report_proofs
from axiom.research import run_campaign


def test_batch_preserves_unverified_status_without_lean(tmp_path):
    report_file = tmp_path / 'report.json'
    original = run_campaign(str(tmp_path/'campaign.db'), seed=42, candidates=40,
                            domain='mixed', report_path=str(report_file))
    assert original['counts']['PROVED_IN_SUPPORTED_FRAGMENT'] > 0
    output_dir = tmp_path / 'lean_results'
    root = Path(__file__).resolve().parent.parent
    with patch('axiom.lean_backend.shutil.which', return_value=None):
        summary = verify_report_proofs(report_file, project_root=root, output_dir=output_dir, limit=3)
    assert summary['attempted'] == 3 and summary['formally_verified'] == 0
    assert all(x['status'] == 'LEAN_UNAVAILABLE' for x in summary['results'])
    assert all(Path(x['record']).is_file() for x in summary['results'])
    assert json.loads((output_dir/'summary.json').read_text())['formally_verified'] == 0
    assert json.loads(report_file.read_text())['counts'] == original['counts']
    with sqlite3.connect(tmp_path / 'campaign.db') as db:
        assert db.execute("select count(*) from findings where status = 'FORMALLY_VERIFIED'").fetchone()[0] == 0


def test_batch_rejects_corrupted_mathematical_report(tmp_path):
    report_file = tmp_path / 'report.json'
    run_campaign(str(tmp_path/'campaign.db'), candidates=10, report_path=str(report_file))
    report = json.loads(report_file.read_text())
    report['campaign_id'] = 'fake'
    report_file.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        verify_report_proofs(report_file, project_root=tmp_path, output_dir=tmp_path/'out')
    with pytest.raises(ValueError):
        verify_report_proofs(report_file, project_root=tmp_path, output_dir=tmp_path/'out', limit=0)


def test_lean_result_audit_replays_original_campaign_and_binds_candidates(tmp_path):
    from axiom.formal_campaign import audit_formal_report
    report_file = tmp_path / 'report.json'
    source = run_campaign(str(tmp_path/'campaign.db'), seed=42, candidates=40,
                          domain='mixed', report_path=str(report_file))
    output_dir = tmp_path / 'formal'
    root = Path(__file__).resolve().parent.parent
    with patch('axiom.lean_backend.shutil.which', return_value=None):
        verify_report_proofs(report_file, project_root=root, output_dir=output_dir, limit=3)
    checked = audit_formal_report(report_file, result_dir=output_dir)
    assert checked['records_audited'] == 3
    assert checked['formally_verified_in_records'] == 0
    assert checked['external_provenance_authenticated'] is False
    with pytest.raises(ValueError):
        audit_formal_report(report_file, result_dir=output_dir, require_complete=True)
    record = next(p for p in output_dir.glob('*.json') if p.name != 'summary.json')
    forged = json.loads(record.read_text())
    forged['origin_campaign_id'] = 'malicious'
    record.write_text(json.dumps(forged))
    with pytest.raises(ValueError):
        audit_formal_report(report_file, result_dir=output_dir)
