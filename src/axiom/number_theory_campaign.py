"""SQLite-checkpointed deterministic integer number-theory campaigns.

The campaign stores original statements, bounded experiments and independently
replayable polynomial quotient certificates; no finite test is a universal proof.
"""
from __future__ import annotations
import hashlib
import json
import os
import platform
from pathlib import Path
import resource
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any
import sympy as sp
from .number_theory_engine import (generate_nt, falsify_nt, polynomial_factor_proof,
                                    _witness_values)
from .number_theory_model import NTStatement
from .number_theory_checker import check_nt_certificate

SCHEMA = 'axiom.number_theory.report.v1'
ENGINE_VERSION = '0.4.0'
STATUSES = ('REFUTED','PROVED_IN_SUPPORTED_FRAGMENT','EXPERIMENTALLY_SUPPORTED')
TRACES = {
    'REFUTED':['GENERATED','UNDER_TEST','REFUTED'],
    'PROVED_IN_SUPPORTED_FRAGMENT':['GENERATED','UNDER_TEST','PROOF_CANDIDATE','PROVED_IN_SUPPORTED_FRAGMENT'],
    'EXPERIMENTALLY_SUPPORTED':['GENERATED','UNDER_TEST','EXPERIMENTALLY_SUPPORTED'],
}


def stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _rank(statement: NTStatement) -> float:
    # Transparent subjective heuristic, not a mathematical significance estimate.
    def node_count(e) -> int:
        return 1 + sum(node_count(a) for a in e.args)
    return round(100/(1+node_count(statement.lhs)+node_count(statement.rhs)+len(statement.variables)),4)


def _open_db(path: str) -> sqlite3.Connection:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(target)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS nt_campaigns (
          id TEXT PRIMARY KEY, configuration TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
          duplicates INTEGER NOT NULL DEFAULT 0, created_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS nt_findings (
          campaign_id TEXT NOT NULL REFERENCES nt_campaigns(id),
          candidate_id TEXT NOT NULL, ordinal INTEGER NOT NULL, template TEXT NOT NULL,
          canonical_key TEXT NOT NULL, statement TEXT NOT NULL, status TEXT NOT NULL,
          originality TEXT NOT NULL, ranking_score REAL NOT NULL, history TEXT NOT NULL,
          search TEXT NOT NULL, proof TEXT,
          PRIMARY KEY (campaign_id,candidate_id), UNIQUE (campaign_id,canonical_key));
    ''')
    return db


def audit_nt_finding(finding: dict) -> bool:
    status=finding['status']
    if status not in TRACES or finding['history']!=TRACES[status]:
        raise ValueError('illegal evidence status history')
    if finding['originality']!='NOT_ASSESSED':
        raise ValueError('novelty claim unsupported')
    statement=NTStatement.from_dict(finding['statement'])
    search=finding['search']
    witness=search.get('counterexample')
    if status=='REFUTED':
        if (finding['proof'] is not None or not isinstance(witness,dict) or
                set(witness)!=set(statement.variables) or
                any(type(v) is not int for v in witness.values())):
            raise ValueError('invalid counterexample shape')
        val=_witness_values(statement,witness)
        if val is None or search.get('lhs_value')!=val[0] or search.get('rhs_value')!=val[1]:
            raise ValueError('counterexample does not falsify statement')
    elif status=='PROVED_IN_SUPPORTED_FRAGMENT':
        if witness is not None or not isinstance(finding['proof'],dict):
            raise ValueError('proof record malformed')
        if not check_nt_certificate(finding['statement'],finding['proof']['certificate']):
            raise ValueError('independent certificate was not accepted')
    else:
        if witness is not None or finding['proof'] is not None:
            raise ValueError('experimental result contains fake theorem evidence')
    return True


def audit_nt_report(report: dict) -> dict[str,int]:
    if not isinstance(report,dict) or report.get('schema')!=SCHEMA:
        raise ValueError('invalid research report schema')
    config=report['configuration']
    if (config.get('engine_version')!=ENGINE_VERSION or config.get('campaign')!='elementary_number_theory'):
        raise ValueError('incompatible campaign configuration')
    cid=hashlib.sha256(stable(config).encode()).hexdigest()[:24]
    if report.get('campaign_id')!=cid:
        raise ValueError('invalid campaign identifier')
    generated=generate_nt(config['seed'], config['candidates'])
    progress=report['progress'];cursor=progress['cursor']
    if type(cursor) is not int or not 0<=cursor<=len(generated):
        raise ValueError('invalid cursor')
    expected={}
    for idx, (template,statement) in enumerate(generated[:cursor]):
        key=statement.canonical_key()
        if key not in expected:
            expected[key]=(idx,template,statement.to_dict())
    if len(report['findings'])!=len(expected) or progress['unique_candidates']!=len(expected):
        raise ValueError('missing or extra findings')
    counts={key:0 for key in STATUSES}
    for finding,(key,(ordinal,template,stmt)) in zip(report['findings'],expected.items()):
        if (finding['ordinal']!=ordinal or finding['template']!=template or
                finding['statement']!=stmt or
                finding['candidate_id']!=hashlib.sha256(key.encode()).hexdigest() or
                finding['ranking_score']!=_rank(NTStatement.from_dict(stmt))):
            raise ValueError('candidate does not match deterministic generation')
        audit_nt_finding(finding)
        reproduced=falsify_nt(NTStatement.from_dict(stmt),config['lower'],config['upper'],
                              config['max_evals'],config['seed']+ordinal)
        if stable(finding['search'])!=stable(reproduced):
            raise ValueError('bounded evidence differs from independent replay')
        counts[finding['status']]+=1
    if (progress['duplicates_rejected']!=cursor-len(expected) or
            progress['complete']!=(cursor==len(generated)) or
            any(report['counts'].get(k,0)!=v for k,v in counts.items()) or
            any(v!=0 for k,v in report['counts'].items() if k not in counts)):
        raise ValueError('incorrect research totals')
    return counts


def run_nt_campaign(db_path: str, seed: int=42, candidates: int=200,
                    lower: int=-8, upper: int=8, max_evals: int=300,
                    step_limit: int|None=None, report_path: str|None=None) -> dict[str,Any]:
    if (type(seed) is not int or type(candidates) is not int or
            not 1<=candidates<=100_000 or type(step_limit) not in (type(None),int) or
            (step_limit is not None and step_limit<0)):
        raise ValueError('invalid number-theory campaign settings')
    # Preflight search budgets even when all generated statements are duplicates.
    if type(lower) is not int or type(upper) is not int or lower>upper or upper-lower>100_000 or \
            type(max_evals) is not int or not 1<=max_evals<=1_000_000:
        raise ValueError('invalid bounded experiment configuration')
    config={'campaign':'elementary_number_theory','engine_version':ENGINE_VERSION,
            'seed':seed,'candidates':candidates,'lower':lower,'upper':upper,
            'max_evals':max_evals}
    cid=hashlib.sha256(stable(config).encode()).hexdigest()[:24]
    generated=generate_nt(seed,candidates)
    begin=time.perf_counter()
    with _open_db(db_path) as db:
        db.execute('INSERT OR IGNORE INTO nt_campaigns (id,configuration,cursor,duplicates,created_utc) VALUES (?,?,0,0,?)',
                   (cid,stable(config),datetime.now(timezone.utc).isoformat()))
        db.commit()
        row=db.execute('SELECT configuration,cursor,duplicates FROM nt_campaigns WHERE id=?',(cid,)).fetchone()
        if row[0]!=stable(config):
            raise RuntimeError('campaign identifier collision')
        cursor,duplicates=int(row[1]),int(row[2]);previous=cursor
        seen={x[0] for x in db.execute('SELECT canonical_key FROM nt_findings WHERE campaign_id=?',(cid,))}
        stop=min(len(generated),cursor+step_limit) if step_limit is not None else len(generated)
        for i in range(cursor,stop):
            template,stmt=generated[i]
            key=stmt.canonical_key()
            if key in seen:
                duplicates+=1
                with db:
                    db.execute('UPDATE nt_campaigns SET cursor=?,duplicates=? WHERE id=?',(i+1,duplicates,cid))
                continue
            search=falsify_nt(stmt,lower,upper,max_evals,seed+i)
            proof=None
            if search['counterexample'] is not None:
                status='REFUTED'
            else:
                proof=polynomial_factor_proof(stmt)
                status='PROVED_IN_SUPPORTED_FRAGMENT' if proof else 'EXPERIMENTALLY_SUPPORTED'
            history=TRACES[status]
            finding={'candidate_id':hashlib.sha256(key.encode()).hexdigest(),
                     'ordinal':i,'template':template,'statement':stmt.to_dict(),
                     'status':status,'originality':'NOT_ASSESSED',
                     'ranking_score':_rank(stmt),'history':history,
                     'search':search,'proof':proof}
            audit_nt_finding(finding)
            with db:
                db.execute('''INSERT INTO nt_findings (campaign_id,candidate_id,ordinal,template,
                           canonical_key,statement,status,originality,ranking_score,history,search,proof)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                           (cid,finding['candidate_id'],i,template,key,stable(stmt.to_dict()),status,
                            'NOT_ASSESSED',finding['ranking_score'],stable(history),stable(search),
                            stable(proof) if proof else None))
                db.execute('UPDATE nt_campaigns SET cursor=?,duplicates=? WHERE id=?',(i+1,duplicates,cid))
            seen.add(key)
        cursor=db.execute('SELECT cursor FROM nt_campaigns WHERE id=?',(cid,)).fetchone()[0]
        findings=[{'candidate_id':r[0],'ordinal':r[1],'template':r[2],
                   'statement':json.loads(r[3]),'status':r[4],'originality':r[5],
                   'ranking_score':r[6],'history':json.loads(r[7]),
                   'search':json.loads(r[8]),'proof':json.loads(r[9]) if r[9] else None}
                  for r in db.execute('''SELECT candidate_id,ordinal,template,statement,status,
                         originality,ranking_score,history,search,proof
                         FROM nt_findings WHERE campaign_id=? ORDER BY ordinal''',(cid,))]
    for item in findings:audit_nt_finding(item)
    counts={kind:sum(item['status']==kind for item in findings) for kind in STATUSES}
    duration=time.perf_counter()-begin
    report={'schema':SCHEMA,'campaign_id':cid,'configuration':config,
            'progress':{'cursor':cursor,'candidate_budget':candidates,
                        'complete':cursor==candidates,'duplicates_rejected':duplicates,
                        'unique_candidates':len(findings)},
            'counts':counts,'findings':findings,
            'measurement':{'execution_seconds':round(duration,6),
                           'candidate_positions_per_second':round((cursor-previous)/duration,2) if duration else None,
                           'peak_process_rss_kb_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                               if platform.system()=='Linux' else None},
            'environment':{'python':platform.python_version(),'sympy':sp.__version__,
                           'platform':platform.platform(),
                           'checker':'stdlib_number_theory_polynomial_factor',
                           'lean':'NOT_EXECUTED'},
            'originality_policy':'NOT_ASSESSED: no literature search'}
    audit_nt_report(report)
    if report_path:
        target=Path(report_path);target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix(target.suffix+'.tmp')
        tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        os.replace(tmp,target)
    return report
