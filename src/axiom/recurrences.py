"""Elementary exact order-two integer recurrence and modular period laboratory."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import random
from .recurrence_checker import (SCHEMA,validate_spec,spec_digest,
                                 check_recurrence_certificate)


@dataclass(frozen=True)
class SecondOrderRecurrence:
    a0: int
    a1: int
    p: int
    q: int
    modulus: int

    def __post_init__(self):
        validate_spec(self.to_dict())

    def to_dict(self) -> dict[str,int]:
        return {'a0':self.a0,'a1':self.a1,'p':self.p,'q':self.q,'modulus':self.modulus}

    def terms(self,count: int) -> list[int]:
        if type(count) is not int or not 0<=count<=10_000:
            raise ValueError('invalid recurrence evaluation budget')
        out=[]
        a,b=self.a0,self.a1
        for _ in range(count):
            out.append(a)
            a,b=b,self.p*b+self.q*a
            if b.bit_length()>131_072:
                raise ValueError('unbounded recurrence term growth')
        return out

    def modular_cycle(self) -> dict[str, Any]:
        """Find first state repeat in <=m² transitions, then certify it."""
        m=self.modulus
        current=(self.a0%m,self.a1%m)
        seen={}
        states=[]
        for index in range(m*m+1):
            states.append(list(current))
            if current in seen:
                before=seen[current]
                cert={'schema':SCHEMA,'spec_sha256':spec_digest(self.to_dict()),
                      'preperiod':before,'period':index-before,'states':states}
                if not check_recurrence_certificate(self.to_dict(),cert):
                    raise ArithmeticError('CRITICAL: recurrence certificate verification failed')
                return cert
            seen[current]=index
            a,b=current
            current=(b,(self.p*b+self.q*a)%m)
        raise ArithmeticError('pigeonhole bound violated by deterministic recurrence')


def sequence_campaign(seed: int, budget: int) -> dict[str, Any]:
    if type(seed) is not int or type(budget) is not int or not 1<=budget<=1000:
        raise ValueError('invalid sequence research budget')
    rng=random.Random(seed)
    findings=[]
    for i in range(budget):
        if i==0:
            spec=SecondOrderRecurrence(0,1,1,1,2)  # known Fibonacci benchmark
            origin='KNOWN_BENCHMARK_FIBONACCI_MOD_2'
        elif i==1:
            spec=SecondOrderRecurrence(0,1,1,1,5)
            origin='KNOWN_BENCHMARK_FIBONACCI_MOD_5'
        else:
            spec=SecondOrderRecurrence(rng.randint(-5,5),rng.randint(-5,5),
                   rng.randint(-3,3),rng.randint(-3,3),rng.randint(2,32))
            origin='GENERATED_FROM_BOUNDED_GRAMMAR'
        certificate=spec.modular_cycle()
        findings.append({'ordinal':i,'origin':origin,'specification':spec.to_dict(),
                         'status':'PROVED_IN_SUPPORTED_FRAGMENT',
                         'certificate':certificate,'checker':'stdlib_finite_state_recurrence_checker',
                         'claim':'eventual period of the ordered consecutive-residue state, not integer sequence',
                         'originality':'NOT_ASSESSED'})
    return {'schema':'axiom.recurrence.campaign.v1','seed':seed,'budget':budget,
            'algorithm':'first_repeated_modular_pair','findings':findings,
            'claim_scope':'for all n>=preperiod, pair state at n+period equals pair state at n (mod modulus)',
            'formal_verification':'NOT_EXECUTED'}


def audit_sequence_campaign(report: dict) -> bool:
    if (not isinstance(report,dict) or report.get('schema')!='axiom.recurrence.campaign.v1' or
            type(report.get('seed')) is not int or type(report.get('budget')) is not int or
            not 1<=report['budget']<=1000):
        raise ValueError('invalid sequence research report')
    rebuilt=sequence_campaign(report['seed'],report['budget'])
    if report!=rebuilt:
        raise ValueError('sequence report does not match deterministic finite-state replay')
    return True
