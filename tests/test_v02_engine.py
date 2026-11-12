"""v0.2 campaign, evidence/status, and minimization tests."""
from axiom.certificate_checker import check_certificate
from axiom.mathematics import C, V, Statement, add, power, sub
from axiom.verification import falsify
from axiom.research import run_campaign


def test_witness_minimization_respects_original_assumptions():
    x = V('x')
    wrong = Statement(x, C(100), '>=', ('x',), (('x', 3, 10),))
    evidence = falsify(wrong, -20, 20, 3, seed=22)
    assert evidence['counterexample'] == {'x': 3}
    assert not wrong.holds(evidence['counterexample'])
    assert evidence['minimization']['globally_minimal'] is False
    assert evidence['search_bounds']['x'] == (3, 10)
    assert falsify(wrong, -20, 1, 3, seed=22)['search_space'] == 0


def test_mixed_campaign_contains_genuine_proof_and_non_proof(tmp_path):
    report = run_campaign(str(tmp_path / 'v02.db'), seed=42, candidates=105,
                          domain='mixed', max_evals=1)
    kinds = {f['template'] for f in report['findings']}
    assert {'multivariate_sum_of_squares', 'finite_interval_inequality',
            'difference_of_squares'} <= kinds
    assert report['configuration']['engine_version'] == '0.2.0'
    assert report['counts']['FORMALLY_VERIFIED'] == 0
    assert report['counts']['EXPERIMENTALLY_SUPPORTED'] > 0
    assert report['counts']['PROVED_IN_SUPPORTED_FRAGMENT'] > 0
    for item in report['findings']:
        if item['status'] == 'PROVED_IN_SUPPORTED_FRAGMENT':
            assert item['history'][-2:] == ['PROOF_CANDIDATE', 'PROVED_IN_SUPPORTED_FRAGMENT']
            assert check_certificate(item['statement'], item['proof']['certificate'])
        elif item['search']['counterexample'] is None:
            assert item['proof'] is None
            assert item['status'] in ('UNRESOLVED', 'EXPERIMENTALLY_SUPPORTED')
        else:
            assert item['status'] == 'REFUTED'
            assert item['proof'] is None


def test_database_proof_tampering_rejected_on_resume(tmp_path):
    import json
    import sqlite3
    import pytest
    db = tmp_path / 'evidence.sqlite3'
    report = run_campaign(str(db), seed=24, candidates=40)
    proven = next(f for f in report['findings'] if f['status'] == 'PROVED_IN_SUPPORTED_FRAGMENT')
    with sqlite3.connect(db) as connection:
        cur = connection.execute('SELECT proof_evidence FROM findings WHERE candidate_id=?', (proven['candidate_id'],))
        p = json.loads(cur.fetchone()[0])
        p['certificate']['statement_sha256'] = '0' * 64
        connection.execute('UPDATE findings SET proof_evidence=? WHERE candidate_id=?',
                           (json.dumps(p), proven['candidate_id']))
    with pytest.raises(ValueError, match='certificate'):
        run_campaign(str(db), seed=24, candidates=40)


def test_v01_research_history_is_not_reinterpreted(tmp_path):
    from axiom.research import open_db
    db = tmp_path / 'shared.sqlite3'
    with open_db(str(db)) as conn:
        conn.execute("INSERT INTO campaigns(id,configuration,cursor,duplicates,created_utc) VALUES ('legacy','{}',0,0,'2026-01-01')")
        conn.commit()
    report = run_campaign(str(db), seed=10, candidates=12)
    assert report['progress']['complete']
    with open_db(str(db)) as conn:
        assert conn.execute('SELECT count(*) FROM campaigns').fetchone()[0] == 2


def test_full_report_audit_and_provenance_mutation(tmp_path):
    import copy
    import pytest
    from axiom.evidence import audit_report
    db = tmp_path / 'audit.sqlite3'
    report = run_campaign(str(db), seed=16, candidates=55, domain='mixed')
    assert sum(audit_report(report).values()) == report['progress']['unique_candidates']
    mutated = copy.deepcopy(report)
    mutated['findings'][0]['template'] = 'fraud'
    with pytest.raises(ValueError, match='provenance'):
        audit_report(mutated)
    mutated = copy.deepcopy(report)
    mutated['counts']['PROVED_IN_SUPPORTED_FRAGMENT'] += 1
    with pytest.raises(ValueError, match='totals'):
        audit_report(mutated)
