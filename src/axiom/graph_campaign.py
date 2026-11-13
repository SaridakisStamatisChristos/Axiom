"""Reproducible, SQLite-checkpointed finite-graph discovery and falsification.

Proof is issued only for fully and INDEPENDENTLY enumerated fixed orders n<=5.
No amount of bounded search for n>5 is permitted to promote a statement.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import platform
import random
import resource
import sqlite3
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from .graph_model import SimpleGraph, edge_positions, isomorphism_representatives
from .graph_invariants import graph_properties
from .graph_claims import GraphStatement, TEMPLATES, PARAMETERIZED, stable, digest, holds
from .graph_checker import (PROOF_N_LIMIT, check_finite_certificate,
                            build_finite_certificate, check_graph_witness)

SCHEMA = 'axiom.graph.campaign.v1'
ENGINE_VERSION = '0.5.0'
STATUSES = ('PROVED_IN_SUPPORTED_FRAGMENT', 'REFUTED', 'EXPERIMENTALLY_SUPPORTED')
HISTORIES = {
    'PROVED_IN_SUPPORTED_FRAGMENT': ['GENERATED','UNDER_TEST','PROOF_CANDIDATE','PROVED_IN_SUPPORTED_FRAGMENT'],
    'REFUTED': ['GENERATED','UNDER_TEST','REFUTED'],
    'EXPERIMENTALLY_SUPPORTED': ['GENERATED','UNDER_TEST','EXPERIMENTALLY_SUPPORTED'],
}
BENCHMARKS = (
    (5,'handshake',0),
    (5,'triangle_free_is_bipartite',0),
    (5,'chromatic_le_clique',0),
    (4,'tree_edge_count',0),
    (5,'chromatic_le_delta_plus_one',0),
    (6,'triangles_le_edges',0),
    (6,'handshake',0),
)


def _validate_config(seed: int, candidates: int, max_order: int,
                     search_budget: int, step_limit: int | None) -> None:
    if (type(seed) is not int or type(candidates) is not int or
            not 1<=candidates<=10_000 or type(max_order) is not int or
            not 0<=max_order<=7 or type(search_budget) is not int or
            not 1<=search_budget<=2_048 or
            (step_limit is not None and (type(step_limit) is not int or step_limit<0))):
        raise ValueError('invalid bounded graph campaign configuration')


def generate_graph_candidates(seed: int, candidates: int, max_order: int) -> list[tuple[str, GraphStatement]]:
    _validate_config(seed,candidates,max_order,128,None)
    rng=random.Random(seed)
    labels=tuple(TEMPLATES)
    results=[]
    for ordinal in range(candidates):
        if ordinal < len(BENCHMARKS) and BENCHMARKS[ordinal][0]<=max_order:
            n,template,k=BENCHMARKS[ordinal]
            origin='KNOWN_BENCHMARK'
        else:
            n=rng.randrange(max_order+1)
            template=rng.choice(labels)
            k=rng.randint(-3,7) if template in PARAMETERIZED else 0
            origin='GENERATED_FROM_FINITE_GRAPH_GRAMMAR'
        results.append((origin,GraphStatement(n,template,k)))
    return results


@lru_cache(maxsize=8192)
def _discovery_properties(n:int,mask:int) -> dict:
    return graph_properties(SimpleGraph.from_mask(n,mask))


@lru_cache(maxsize=None)
def _representatives(n:int) -> tuple[SimpleGraph,...]:
    return tuple(isomorphism_representatives(n))


def _sample_masks(n:int,seed:int,budget:int) -> tuple[int,...]:
    total=1<<len(edge_positions(n))
    pairs=edge_positions(n)
    ids={p:i for i,p in enumerate(pairs)}
    def mask_of(edges):
        return sum(1<<ids[tuple(sorted(edge))] for edge in edges)
    paths=[(i,i+1) for i in range(n-1)]
    cycles=paths+([(0,n-1)] if n>=3 else [])
    star=[(0,i) for i in range(1,n)]
    half=[(i,j) for i in range(n//2) for j in range(n//2,n)]
    landmarks=[0,total-1,mask_of(paths),mask_of(cycles),mask_of(star),mask_of(half)]
    rng=random.Random(seed)
    chosen=[];seen=set()
    for mask in landmarks:
        if mask not in seen and len(chosen)<min(budget,total):
            chosen.append(mask);seen.add(mask)
    while len(chosen)<min(budget,total):
        mask=rng.randrange(total)
        if mask not in seen:
            chosen.append(mask);seen.add(mask)
    return tuple(chosen)


def scan_graph_statement(statement: GraphStatement, search_budget:int, seed:int) -> dict[str,Any]:
    if type(search_budget) is not int or not 1<=search_budget<=2048 or type(seed) is not int:
        raise ValueError('invalid graph search budget')
    n=statement.n
    if n<=PROOF_N_LIMIT:
        graphs=_representatives(n)
        method='EXHAUSTIVE_ISOMORPHISM_CLASSES'
    else:
        graphs=tuple(SimpleGraph.from_mask(n,m) for m in _sample_masks(n,seed,search_budget))
        method='BOUNDED_LABELLED_GRAPH_SEARCH'
    sampled=0
    failures=[]
    for g in graphs:
        applies,correct=holds(statement,_discovery_properties(n,g.mask))
        sampled+=int(applies)
        if applies and not correct:
            failures.append(g)
    witness=None
    if failures:
        # Smaller edge count first, deterministic encoding second. Always check
        # the exact original claim using independent graph invariant algorithms.
        winner=min(failures,key=lambda x:(len(x.edges),x.mask))
        witness=winner.to_dict()
        check_graph_witness(statement.to_dict(),witness)
    return {'method':method,'graph_order':n,'seed':seed,'search_budget':search_budget,
            'labelled_graph_space':1<<len(edge_positions(n)),
            'structures_checked':len(graphs),'assumption_satisfying_structures':sampled,
            'counterexample':witness,
            'scope':'all isomorphism classes of order n' if n<=PROOF_N_LIMIT
                    else 'bounded explicit labelled graphs; NOT exhaustive'}


def rank_graph_statement(stmt:GraphStatement) -> float:
    # Explicit subjective heuristic only; no claim of originality or significance.
    return round(100/(1+stmt.n+int(stmt.template in PARAMETERIZED)),4)


def _make_finding(ordinal:int,origin:str,stmt:GraphStatement,config:dict) -> dict:
    search=scan_graph_statement(stmt,config['search_budget'],config['seed']+ordinal)
    witness=search['counterexample']
    proof=None
    if witness is not None:
        status='REFUTED'
    elif stmt.n<=PROOF_N_LIMIT:
        cert=build_finite_certificate(stmt.to_dict())
        status='PROVED_IN_SUPPORTED_FRAGMENT'
        proof={'certificate':cert,'method':'exhaustive_all_labelled_simple_graphs',
               'checker':'axiom.graph_checker.check_finite_certificate',
               'formal_verification':'NOT_PERFORMED'}
    else:
        status='EXPERIMENTALLY_SUPPORTED'
    return {'ordinal':ordinal,'origin':origin,'candidate_id':digest(stmt.to_dict()),
            'statement':stmt.to_dict(),'status':status,
            'originality':'NOT_ASSESSED','score':rank_graph_statement(stmt),
            'history':HISTORIES[status],'search':search,'proof':proof}


def audit_graph_finding(finding:dict) -> bool:
    if type(finding) is not dict or set(finding)!={
        'ordinal','origin','candidate_id','statement','status','originality','score','history','search','proof'}:
        raise ValueError('invalid graph finding shape')
    statement=GraphStatement.from_dict(finding['statement'])
    status=finding['status']
    if (status not in HISTORIES or finding['history']!=HISTORIES[status] or
            finding['originality']!='NOT_ASSESSED' or
            finding['candidate_id']!=digest(statement.to_dict()) or
            finding['score']!=rank_graph_statement(statement)):
        raise ValueError('graph provenance, ranking, or state invalid')
    search=finding['search']
    if type(search) is not dict:
        raise ValueError('invalid graph search evidence')
    witness=search.get('counterexample')
    if status=='REFUTED':
        if witness is None or finding['proof'] is not None:
            raise ValueError('refutation evidence missing or contradictory')
        check_graph_witness(statement.to_dict(),witness)
    elif status=='PROVED_IN_SUPPORTED_FRAGMENT':
        if (statement.n>PROOF_N_LIMIT or witness is not None or
                type(finding['proof']) is not dict or
                set(finding['proof'])!={'certificate','method','checker','formal_verification'} or
                finding['proof']['method']!='exhaustive_all_labelled_simple_graphs' or
                finding['proof']['checker']!='axiom.graph_checker.check_finite_certificate' or
                finding['proof']['formal_verification']!='NOT_PERFORMED'):
            raise ValueError('unsupported finite proof claim')
        check_finite_certificate(statement.to_dict(),finding['proof']['certificate'])
    else:
        if statement.n<=PROOF_N_LIMIT or witness is not None or finding['proof'] is not None:
            raise ValueError('invalid experimental status; possible false promotion')
    return True


def audit_graph_report(report:dict) -> dict[str,int]:
    if type(report) is not dict or report.get('schema')!=SCHEMA:
        raise ValueError('invalid graph report schema')
    c=report['configuration']
    if (type(c) is not dict or set(c)!={'campaign','engine_version','seed','candidates','max_order','search_budget'} or
            c['campaign']!='finite_simple_graph_discovery' or c['engine_version']!=ENGINE_VERSION):
        raise ValueError('unsupported graph campaign metadata')
    _validate_config(c['seed'],c['candidates'],c['max_order'],c['search_budget'],None)
    if report.get('campaign_id')!=digest(c)[:24]:
        raise ValueError('graph campaign ID mismatch')
    positions=generate_graph_candidates(c['seed'],c['candidates'],c['max_order'])
    p=report['progress'];cursor=p['cursor']
    if type(cursor) is not int or not 0<=cursor<=len(positions):
        raise ValueError('invalid graph checkpoint position')
    unique={}
    for i,(origin,stmt) in enumerate(positions[:cursor]):
        unique.setdefault(stmt.canonical_key(),(i,origin,stmt))
    if len(report['findings'])!=len(unique):
        raise ValueError('graph findings missing or duplicated')
    counts={s:0 for s in STATUSES}
    for observed,(i,origin,stmt) in zip(report['findings'],unique.values()):
        if observed['ordinal']!=i or observed['origin']!=origin or observed['statement']!=stmt.to_dict():
            raise ValueError('graph finding not generated by reproducible grammar')
        audit_graph_finding(observed)
        expect=_make_finding(i,origin,stmt,c)
        if stable(observed)!=stable(expect):
            raise ValueError('graph search or proof evidence differs from deterministic replay')
        counts[observed['status']]+=1
    if (p['unique_candidates']!=len(unique) or p['duplicates_rejected']!=cursor-len(unique) or
            p['complete']!=(cursor==len(positions)) or
            report['counts']!=counts):
        raise ValueError('graph campaign counters invalid')
    meas=report.get('measurement')
    if (type(meas) is not dict or type(meas.get('elapsed_seconds')) not in (float,int) or
            meas['elapsed_seconds']<0 or type(meas.get('rss_kib')) is not int or meas['rss_kib']<=0):
        raise ValueError('malformed resource measurements')
    return counts


def _open_db(path:str) -> sqlite3.Connection:
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(target)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS graph_campaigns (
        id TEXT PRIMARY KEY, configuration TEXT NOT NULL, cursor INTEGER NOT NULL,
        duplicates INTEGER NOT NULL, created_utc TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS graph_findings (
        campaign_id TEXT NOT NULL REFERENCES graph_campaigns(id),
        canonical_key TEXT NOT NULL, candidate_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
        finding_json TEXT NOT NULL, PRIMARY KEY (campaign_id, canonical_key),
        UNIQUE (campaign_id, candidate_id));
    ''')
    return db


def run_graph_campaign(db_path:str,*,seed:int=42,candidates:int=240,
                       max_order:int=6,search_budget:int=128,
                       step_limit:int|None=None,report_path:str|None=None) -> dict:
    _validate_config(seed,candidates,max_order,search_budget,step_limit)
    config={'campaign':'finite_simple_graph_discovery','engine_version':ENGINE_VERSION,
            'seed':seed,'candidates':candidates,'max_order':max_order,'search_budget':search_budget}
    cid=digest(config)[:24]
    positions=generate_graph_candidates(seed,candidates,max_order)
    tic=time.perf_counter()
    with _open_db(db_path) as db:
        db.execute('INSERT OR IGNORE INTO graph_campaigns VALUES (?,?,0,0,?)',
                   (cid,stable(config),datetime.now(timezone.utc).isoformat()))
        db.commit()
        rec=db.execute('SELECT configuration,cursor,duplicates FROM graph_campaigns WHERE id=?',(cid,)).fetchone()
        if rec[0]!=stable(config):raise ValueError('campaign hash collision')
        cursor,duplicates=int(rec[1]),int(rec[2])
        if not 0<=cursor<=candidates:raise ValueError('invalid persisted graph cursor')
        seen={key for (key,) in db.execute('SELECT canonical_key FROM graph_findings WHERE campaign_id=?',(cid,))}
        # Fail closed on resume: verify every persisted finding against its source
        # before appending new research.
        expected={}
        for i,(origin,stmt) in enumerate(positions[:cursor]):
            expected.setdefault(stmt.canonical_key(),(i,origin,stmt))
        if duplicates!=cursor-len(expected) or set(expected)!=seen:
            raise ValueError('inconsistent persisted graph checkpoint coverage')
        for (key,payload) in db.execute('SELECT canonical_key,finding_json FROM graph_findings WHERE campaign_id=?',(cid,)):
            finding=json.loads(payload)
            if key!=GraphStatement.from_dict(finding['statement']).canonical_key():
                raise ValueError('tampered graph DB statement key')
            audit_graph_finding(finding)
            i,origin,stmt=expected[key]
            if finding!=_make_finding(i,origin,stmt,config):
                raise ValueError('persisted finding differs from deterministic source replay')
        stop=min(candidates,cursor+step_limit) if step_limit is not None else candidates
        for i in range(cursor,stop):
            origin,stmt=positions[i]
            key=stmt.canonical_key()
            if key in seen:
                duplicates+=1
                with db:
                    db.execute('UPDATE graph_campaigns SET cursor=?,duplicates=? WHERE id=?',(i+1,duplicates,cid))
                continue
            finding=_make_finding(i,origin,stmt,config)
            audit_graph_finding(finding)
            with db:
                db.execute('INSERT INTO graph_findings VALUES (?,?,?,?,?)',
                           (cid,key,finding['candidate_id'],i,stable(finding)))
                db.execute('UPDATE graph_campaigns SET cursor=?,duplicates=? WHERE id=?',(i+1,duplicates,cid))
            seen.add(key)
        row=db.execute('SELECT cursor,duplicates FROM graph_campaigns WHERE id=?',(cid,)).fetchone()
        cursor,duplicates=row
        findings=[json.loads(x[0]) for x in db.execute(
            'SELECT finding_json FROM graph_findings WHERE campaign_id=? ORDER BY ordinal',(cid,))]
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('SQLite graph database failed integrity check')
    counts={s:sum(x['status']==s for x in findings) for s in STATUSES}
    report={'schema':SCHEMA,'campaign_id':cid,'configuration':config,
            'progress':{'cursor':cursor,'unique_candidates':len(findings),
                        'duplicates_rejected':duplicates,'complete':cursor==candidates},
            'counts':counts,'findings':findings,
            'measurement':{'elapsed_seconds':round(time.perf_counter()-tic,6),
                           'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                           'python_version':platform.python_version(),
                           'sqlite_version':sqlite3.sqlite_version,
                           'process_platform':sys.platform},
            'originality_policy':'NOT_ASSESSED',
            'proof_scope':'all labelled simple graphs of the EXACT fixed n only, with n<=5',
            'lean_formal_verification':'NOT_PERFORMED'}
    audit_graph_report(report)
    if report_path is not None:
        target=Path(report_path);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return report
