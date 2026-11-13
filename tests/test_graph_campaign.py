import copy
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
import pytest
from axiom.graph_campaign import (run_graph_campaign,audit_graph_report,
                                  audit_graph_finding,generate_graph_candidates)


def run(tmp_path,**opts):
    return run_graph_campaign(str(tmp_path/'graphs.sqlite3'),
                              seed=42,candidates=75,max_order=6,search_budget=64,
                              **opts)


def test_campaign_results_and_evidence_replay(tmp_path):
    r=run(tmp_path)
    assert audit_graph_report(r)==r['counts']
    assert r['progress']['cursor']==75 and r['progress']['complete']
    assert r['counts']['REFUTED']>0 and r['counts']['PROVED_IN_SUPPORTED_FRAGMENT']>0
    assert r['counts']['EXPERIMENTALLY_SUPPORTED']>0
    assert r['progress']['unique_candidates']+r['progress']['duplicates_rejected']==75
    assert any(f['origin']=='KNOWN_BENCHMARK' for f in r['findings'])
    assert all(f['originality']=='NOT_ASSESSED' for f in r['findings'])


def test_checkpoint_resume_byte_semantics(tmp_path):
    one=run_graph_campaign(str(tmp_path/'a.sqlite3'),seed=51,candidates=90,max_order=6,
                           search_budget=75,step_limit=27)
    assert one['progress']['cursor']==27 and not one['progress']['complete']
    two=run_graph_campaign(str(tmp_path/'a.sqlite3'),seed=51,candidates=90,max_order=6,
                           search_budget=75)
    fresh=run_graph_campaign(str(tmp_path/'fresh.sqlite3'),seed=51,candidates=90,max_order=6,
                             search_budget=75)
    assert two['counts']==fresh['counts']
    assert two['findings']==fresh['findings']
    assert audit_graph_report(two)==two['counts']


def test_tampered_checkpoint_and_report_rejected(tmp_path):
    r=run_graph_campaign(str(tmp_path/'db.sqlite3'),seed=42,candidates=30,max_order=5,
                         step_limit=20)
    with sqlite3.connect(tmp_path/'db.sqlite3') as db:
        row=db.execute('SELECT campaign_id, canonical_key, finding_json FROM graph_findings LIMIT 1').fetchone()
        altered=json.loads(row[2]);altered['status']='FORMALLY_VERIFIED'
        db.execute('UPDATE graph_findings SET finding_json=? WHERE campaign_id=? AND canonical_key=?',
                   (json.dumps(altered),row[0],row[1]))
    with pytest.raises(ValueError):
        run_graph_campaign(str(tmp_path/'db.sqlite3'),seed=42,candidates=30,max_order=5)
    good=run_graph_campaign(str(tmp_path/'clean.sqlite3'),seed=42,candidates=30,max_order=5)
    bad=copy.deepcopy(good);bad['findings'].pop()
    with pytest.raises(ValueError):audit_graph_report(bad)
    bad=copy.deepcopy(good);bad['counts']['REFUTED']+=1
    with pytest.raises(ValueError):audit_graph_report(bad)
    bad=copy.deepcopy(good)
    certified=next(x for x in bad['findings'] if x['proof'])
    certified['proof']['certificate']['statement_sha256']='0'*64
    with pytest.raises(ValueError):audit_graph_report(bad)


def test_deterministic_generator_and_invalid_limits():
    assert generate_graph_candidates(10,40,7)==generate_graph_candidates(10,40,7)
    assert generate_graph_candidates(10,40,7)!=generate_graph_candidates(11,40,7)
    for opts in [dict(candidates=0),dict(max_order=8),dict(search_budget=0),
                 dict(step_limit=-2),dict(seed=3.4)]:
        with pytest.raises(ValueError):
            run_graph_campaign(':memory:',**opts)


def test_command_line_graph_run_audit_and_witness(tmp_path):
    base=[sys.executable,'-m','axiom']
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).parents[1]/'src'))
    target=tmp_path/'report.json'
    cmd=base+['graph-run','--seed','42','--candidates','35','--max-order','5',
              '--search-budget','60','--db',str(tmp_path/'g.sqlite3'),'--report',str(target)]
    p=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert p.returncode==0,p.stderr
    assert json.loads(target.read_text())['progress']['complete']
    out=subprocess.run(base+['graph-audit',str(target)],capture_output=True,text=True,env=env)
    assert out.returncode==0,out.stderr
    report=json.loads(target.read_text());w=next(x for x in report['findings'] if x['proof'])
    cert=tmp_path/'cert.json';cert.write_text(json.dumps({'statement':w['statement'],'certificate':w['proof']['certificate']}))
    checked=subprocess.run(base+['graph-check-certificate',str(cert)],capture_output=True,text=True,env=env)
    assert checked.returncode==0,checked.stderr
    cert.write_text('{}')
    failed=subprocess.run(base+['graph-check-certificate',str(cert)],capture_output=True,text=True,env=env)
    assert failed.returncode!=0
