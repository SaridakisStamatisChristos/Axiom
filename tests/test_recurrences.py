from __future__ import annotations
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from axiom.recurrences import SecondOrderRecurrence, sequence_campaign, audit_sequence_campaign
from axiom.recurrence_checker import (check_recurrence_certificate,
                                      RecurrenceCertificateError)


@pytest.mark.parametrize(('modulus','period'),[(1,1),(2,3),(3,8),(5,20),(7,16),(10,60)])
def test_known_fibonacci_pisano_periods(modulus,period):
    fib=SecondOrderRecurrence(0,1,1,1,modulus)
    cert=fib.modular_cycle()
    assert cert['preperiod']==0 and cert['period']==period
    assert check_recurrence_certificate(fib.to_dict(),cert)


def test_finite_state_eventual_period_after_nonempty_preperiod():
    rec=SecondOrderRecurrence(1,1,0,0,3)
    cert=rec.modular_cycle()
    assert cert['preperiod']==2 and cert['period']==1
    assert check_recurrence_certificate(rec.to_dict(),cert)
    assert rec.terms(6)==[1,1,0,0,0,0]


def test_modular_certificates_survive_direct_recurrence_replay():
    for seed in range(10):
        report=sequence_campaign(seed,30)
        for row in report['findings']:
            spec=row['specification']; cert=row['certificate']
            assert check_recurrence_certificate(spec,cert)
            original=SecondOrderRecurrence(**spec).terms(200)
            m=spec['modulus'];start=cert['preperiod'];period=cert['period']
            for n in range(start,199-period):
                assert original[n]%m==original[n+period]%m
                assert original[n+1]%m==original[n+period+1]%m


def test_certificate_tampering_fails_closed():
    r=SecondOrderRecurrence(0,1,1,1,5)
    cert=r.modular_cycle()
    forged=copy.deepcopy(cert);forged['period']-=1
    with pytest.raises(RecurrenceCertificateError):check_recurrence_certificate(r.to_dict(),forged)
    forged=copy.deepcopy(cert);forged['states'][3][0]=(forged['states'][3][0]+1)%5
    with pytest.raises(RecurrenceCertificateError):check_recurrence_certificate(r.to_dict(),forged)
    forged=copy.deepcopy(cert);forged['states'].append(cert['states'][-1])
    with pytest.raises(RecurrenceCertificateError):check_recurrence_certificate(r.to_dict(),forged)
    forged=copy.deepcopy(cert);forged['spec_sha256']='a'*64
    with pytest.raises(RecurrenceCertificateError):check_recurrence_certificate(r.to_dict(),forged)


@pytest.mark.parametrize('modulus',[0,-1,True,3.5,65])
def test_modulus_rejected(modulus):
    with pytest.raises(RecurrenceCertificateError):SecondOrderRecurrence(0,1,1,1,modulus)


def test_recurrence_budget_constraints():
    r=SecondOrderRecurrence(0,1,1,1,2)
    with pytest.raises(ValueError):r.terms(-1)
    with pytest.raises(ValueError):r.terms(10001)
    with pytest.raises(ValueError):sequence_campaign(1,0)
    with pytest.raises(RecurrenceCertificateError):SecondOrderRecurrence(2**300,0,1,1,2)


def test_deterministic_report_replay_and_tampered_claim():
    report=sequence_campaign(55,30)
    assert audit_sequence_campaign(report)
    bad=copy.deepcopy(report);bad['findings'][0]['certificate']['period']+=1
    with pytest.raises(ValueError):audit_sequence_campaign(bad)
    bad=copy.deepcopy(report);bad['formal_verification']='FORMALLY_VERIFIED'
    with pytest.raises(ValueError):audit_sequence_campaign(bad)


def test_cli_recurrence_run_and_audit(tmp_path):
    root=Path(__file__).resolve().parents[1]
    env={**os.environ,'PYTHONPATH':str(root/'src')+os.pathsep+os.environ.get('PYTHONPATH','')}
    output=tmp_path/'sequence.json'
    a=subprocess.run([sys.executable,'-m','axiom','nt-sequence-run','--budget','12',
                      '--report',str(output)],cwd=root,env=env,capture_output=True,text=True)
    assert a.returncode==0,a.stderr
    b=subprocess.run([sys.executable,'-m','axiom','nt-sequence-audit',str(output)],
                     cwd=root,env=env,capture_output=True,text=True)
    assert b.returncode==0,b.stderr
