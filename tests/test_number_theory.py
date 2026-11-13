"""Adversarial, mathematical, reproducibility and status gates for v0.4."""
from __future__ import annotations
import copy
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from axiom.mathematics import V,C,add,sub,mul,power,Expr
from axiom.number_theory_model import NTStatement
from axiom.number_theory_checker import (check_nt_certificate, validate_statement,
                                         CertificateError, digest)
from axiom.number_theory_engine import (generate_nt, polynomial_factor_proof,
                                        falsify_nt, _witness_values)
from axiom.number_theory_campaign import (run_nt_campaign, audit_nt_report,
                                          audit_nt_finding)
from axiom.number_theory_lean import (build_nt_lean_source, verify_nt_with_lean,
                                      verify_nt_record_integrity)
from axiom.lean_backend import LeanBackendError


def factor():
    x=V('x')
    return NTStatement(sub(x,C(1)),sub(power(x,2),C(1)),'divides',('x',))


def congruence():
    x=V('x')
    return NTStatement(power(add(x,C(7)),2), power(x,2),'congruent',('x',),7)


def false_division():
    x=V('x')
    return NTStatement(x,add(power(x,2),C(1)),'divides',('x',))


def test_zero_divisor_has_correct_integer_semantics():
    assert NTStatement(C(0),C(0),'divides',('x',)).holds({'x':-12})
    assert not NTStatement(C(0),C(3),'divides',('x',)).holds({'x':0})
    assert NTStatement(C(-2),C(6),'divides',('x',)).holds({'x':0})
    assert not NTStatement(C(4),C(6),'divides',('x',)).holds({'x':0})
    assert polynomial_factor_proof(NTStatement(C(0),C(0),'divides',('x',)))
    assert polynomial_factor_proof(NTStatement(C(0),C(1),'divides',('x',))) is None


@pytest.mark.parametrize('modulus', [0,-1,True,None,2.5,2**32])
def test_congruence_modulus_invalid(modulus):
    with pytest.raises(ValueError):
        NTStatement(V('x'),C(0),'congruent',('x',),modulus)


def test_malformed_types_bounds_and_unknown_variables():
    with pytest.raises(ValueError):NTStatement(V('x'),C(0),'divides',('y',))
    with pytest.raises(ValueError):NTStatement(V('x'),C(0),'divides',('x','x'))
    with pytest.raises(ValueError):NTStatement(V('x'),C(0),'divides',('x',),bounds=(('x',2,1),))
    with pytest.raises(ValueError):NTStatement(V('x'),C(0),'divides',('x',),bounds=(('x',0,1),('x',0,1)))
    with pytest.raises(ValueError):NTStatement.from_dict({'x':True})
    malformed=factor().to_dict();malformed['variables']=['y']
    with pytest.raises(CertificateError):validate_statement(malformed)


def test_positive_modulus_and_negative_residues():
    a=NTStatement(C(-15),C(1),'congruent',('x',),8)
    assert a.holds({'x':0})
    b=NTStatement(C(-14),C(1),'congruent',('x',),8)
    assert not b.holds({'x':0})
    assert polynomial_factor_proof(a)
    assert polynomial_factor_proof(b) is None


def test_factor_and_congruence_have_sound_certificates():
    for statement in (factor(), congruence(),
                      NTStatement(C(-3),C(12),'divides',('x',))):
        p=polynomial_factor_proof(statement)
        assert p and check_nt_certificate(statement.to_dict(),p['certificate'])
        for n in range(-30,31):
            assert statement.holds({'x':n})


def test_forged_quotient_and_mutated_statement_rejected():
    statement=factor();proof=polynomial_factor_proof(statement)['certificate']
    fake=copy.deepcopy(proof);fake['quotient'][0][1]+=1
    with pytest.raises(CertificateError):check_nt_certificate(statement.to_dict(),fake)
    altered=copy.deepcopy(statement.to_dict());altered['rhs']['args'][1]['value']=2
    with pytest.raises(CertificateError):check_nt_certificate(altered,proof)
    bad=copy.deepcopy(proof);bad['quotient'].append(bad['quotient'][0])
    with pytest.raises(CertificateError):check_nt_certificate(statement.to_dict(),bad)
    bad=copy.deepcopy(proof);bad['extra']='trick'
    with pytest.raises(CertificateError):check_nt_certificate(statement.to_dict(),bad)


def test_integer_polynomial_witness_rejects_non_integral_quotient():
    t=NTStatement(C(4),mul(C(2),V('x')),'divides',('x',))
    assert polynomial_factor_proof(t) is None
    # At x=1, 4 does not divide 2.
    assert falsify_nt(t,-10,10,21,10)['counterexample'] is not None


def test_invalid_exponent_or_oversized_coefficient():
    with pytest.raises(ValueError):power(V('x'),-1)
    statement=NTStatement(C(2**5000),C(0),'divides',('x',))
    assert polynomial_factor_proof(statement) is None
    with pytest.raises(CertificateError):validate_statement(statement.to_dict())


def test_independent_counterexample_and_minimization():
    stmt=false_division()
    result=falsify_nt(stmt,-8,8,100,42)
    witness=result['counterexample']
    assert witness and witness['x']==0
    assert result['lhs_value']==0 and result['rhs_value']==1
    assert _witness_values(stmt,witness)==(0,1)
    assert result['minimization']['globally_minimal'] is False


def test_search_limited_to_bounds_and_no_false_promotion():
    t=NTStatement(V('x'),C(0),'congruent',('x',),3,(('x',0,0),))
    r=falsify_nt(t,-6,6,100,5)
    assert r['tested']==1 and r['exhaustive'] and r['counterexample'] is None
    assert polynomial_factor_proof(t) is None  # bounded evidence not promoted
    assert t.holds({'x':0})
    with pytest.raises(ValueError):t.holds({'x':1})


def test_true_integer_valued_polynomial_but_incomplete_proof_fragment():
    x=V('x')
    t=NTStatement(power(x,2),x,'congruent',('x',),2)
    assert polynomial_factor_proof(t) is None  # x(x-1)/2 is not in Z[x]
    r=falsify_nt(t,-100,100,201,23)
    assert r['exhaustive'] and r['counterexample'] is None


def test_deterministic_generator_and_false_claims():
    a=generate_nt(13,75)
    b=generate_nt(13,75)
    assert a==b
    assert any(polynomial_factor_proof(s) for _,s in a)
    assert any(falsify_nt(s,-5,5,121,19)['counterexample'] for _,s in a)
    with pytest.raises(ValueError):generate_nt(1,0)


def test_replay_and_resume_identical_report_except_measurement(tmp_path):
    db=str(tmp_path/'checkpoint.sqlite3')
    a=run_nt_campaign(db,seed=53,candidates=80,max_evals=75,step_limit=23)
    assert a['progress']['cursor']==23 and not a['progress']['complete']
    b=run_nt_campaign(db,seed=53,candidates=80,max_evals=75)
    fresh=run_nt_campaign(str(tmp_path/'fresh.sqlite3'),seed=53,candidates=80,max_evals=75)
    assert b['progress']==fresh['progress']
    assert b['findings']==fresh['findings']
    assert audit_nt_report(b)==b['counts']


def test_replay_falsifies_tampered_proof_and_fake_status(tmp_path):
    r=run_nt_campaign(str(tmp_path/'a.sqlite3'),candidates=70,max_evals=80)
    proof=next(f for f in r['findings'] if f['proof'])
    altered=copy.deepcopy(r)
    fake=next(f for f in altered['findings'] if f['candidate_id']==proof['candidate_id'])
    fake['proof']['certificate']['quotient']=[[[0]*len(fake['statement']['variables']),123]]
    with pytest.raises((ValueError,CertificateError)):audit_nt_report(altered)
    forged=copy.deepcopy(r)
    sample=forged['findings'][0]
    sample['status']='FORMALLY_VERIFIED'
    with pytest.raises(ValueError):audit_nt_report(forged)
    changed=copy.deepcopy(r)
    changed['findings'][0]['search']['tested']+=1
    with pytest.raises(ValueError):audit_nt_report(changed)
    db=str(tmp_path/'a.sqlite3')
    import sqlite3
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE nt_findings SET status=? WHERE candidate_id=?',('FORMALLY_VERIFIED',proof['candidate_id']))
    with pytest.raises(ValueError):run_nt_campaign(db,candidates=70,max_evals=80)


def test_reject_fake_campaign_statistics(tmp_path):
    a=run_nt_campaign(str(tmp_path/'db.sqlite3'),seed=4,candidates=60,max_evals=100)
    b=copy.deepcopy(a);b['counts']['REFUTED']+=1
    with pytest.raises(ValueError):audit_nt_report(b)
    b=copy.deepcopy(a);b['campaign_id']='unknown'
    with pytest.raises(ValueError):audit_nt_report(b)


def test_lean_source_binds_exact_statement_and_no_unsafe_constructs():
    for statement in (factor(),congruence()):
        certificate=polynomial_factor_proof(statement)['certificate']
        source=build_nt_lean_source(statement.to_dict(),certificate)
        assert 'import Mathlib.Tactic.Ring' in source['source']
        assert '  refine ⟨' in source['source'] and '  ring' in source['source']
        assert 'sorry' not in source['source'] and 'native_decide' not in source['source']
        assert source['statement_sha256']==digest(statement.to_dict())
        if statement.relation=='congruent':
            assert f'({statement.modulus} : Int) ∣' in source['source']
        else:
            assert ' ∣ ' in source['source']


def test_lean_unavailable_cannot_promote_proof(tmp_path):
    stmt=factor()
    from axiom.lean_backend import TOOLCHAIN,MATHLIB_REV
    (tmp_path/'lean-toolchain').write_text(TOOLCHAIN)
    (tmp_path/'lakefile.toml').write_text(f'[[require]]\nname = "mathlib"\nscope = "leanprover-community"\nrev = "{MATHLIB_REV}"\n')
    cert=polynomial_factor_proof(stmt)['certificate']
    with patch('axiom.number_theory_lean.shutil.which',return_value=None):
        out=verify_nt_with_lean(stmt.to_dict(),cert,project_root=tmp_path)
    assert out['status']=='LEAN_UNAVAILABLE' and out['accepted'] is False
    assert verify_nt_record_integrity(out)
    broken=copy.deepcopy(out);broken['source']+='\nsorry\n'
    with pytest.raises(LeanBackendError):verify_nt_record_integrity(broken)


def test_cli_separate_circuit(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    db=tmp_path/'cli.db'; report=tmp_path/'report.json'
    environment={**os.environ,'PYTHONPATH':str(repo/'src')+os.pathsep+os.environ.get('PYTHONPATH','')}
    proc=subprocess.run([sys.executable,'-m','axiom','nt-run','--db',str(db),'--report',str(report),
                         '--candidates','30','--seed','13'],cwd=repo,env=environment,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    audited=subprocess.run([sys.executable,'-m','axiom','nt-audit',str(report)],
                           cwd=repo,env=environment,capture_output=True,text=True)
    assert audited.returncode==0,audited.stderr


@pytest.mark.parametrize('seed',range(6))
def test_generated_witnesses_recheck_and_proofs_hold_random_points(seed):
    rng=random.Random(seed)
    for _,stmt in generate_nt(seed,50):
        search=falsify_nt(stmt,-8,8,40,seed)
        if search['counterexample'] is not None:
            assert _witness_values(stmt,search['counterexample']) is not None
            assert polynomial_factor_proof(stmt) is None
        else:
            proof=polynomial_factor_proof(stmt)
            if proof:
                assert check_nt_certificate(stmt.to_dict(),proof['certificate'])
                for _ in range(10):
                    env={v:rng.randint(-1000,1000) for v in stmt.variables}
                    if stmt.assumption_holds(env):
                        assert stmt.holds(env)
