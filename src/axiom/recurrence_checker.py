"""Standalone exact checker of modular eventual-periodicity certificates.

For u[n+2]=p*u[n+1]+q*u[n] (n>=0), the transition of state
(u[n],u[n+1]) modulo m is deterministic. A repeated pair at indices s
and s+t therefore establishes state periodicity for ALL n>=s by induction.
The checker independently validates every stored state transition; it has no
SymPy or discovery-engine dependencies. Not a Lean-kernel proof.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA = 'axiom.recurrence.finite_state_certificate.v1'
SPEC_FIELDS = {'a0','a1','p','q','modulus'}
CERT_FIELDS = {'schema','spec_sha256','preperiod','period','states'}
MAX_MODULUS = 64
MAX_PARAM_BITS = 256


class RecurrenceCertificateError(ValueError):
    """Invalid, incomplete or excessive modular recurrence certificate."""


def validate_spec(spec: Any) -> dict:
    if not isinstance(spec,dict) or set(spec)!=SPEC_FIELDS:
        raise RecurrenceCertificateError('invalid recurrence specification')
    if any(type(v) is not int or v.bit_length()>MAX_PARAM_BITS for v in spec.values()):
        raise RecurrenceCertificateError('unsupported coefficient type or bit size')
    if not 1<=spec['modulus']<=MAX_MODULUS:
        raise RecurrenceCertificateError('modulus must be in [1,64]')
    return spec


def spec_digest(spec: dict) -> str:
    validate_spec(spec)
    return hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def check_recurrence_certificate(spec: Any,certificate: Any) -> bool:
    s=validate_spec(spec)
    if not isinstance(certificate,dict) or set(certificate)!=CERT_FIELDS:
        raise RecurrenceCertificateError('malformed recurrence certificate')
    if certificate['schema']!=SCHEMA or certificate['spec_sha256']!=spec_digest(spec):
        raise RecurrenceCertificateError('certificate not bound to the specified recurrence')
    before,period,states=certificate['preperiod'],certificate['period'],certificate['states']
    m=s['modulus']
    if (type(before) is not int or type(period) is not int or before<0 or period<1 or
            not isinstance(states,list) or len(states)!=before+period+1 or
            len(states)>m*m+1):
        raise RecurrenceCertificateError('invalid cycle indices or state count')
    for row in states:
        if (not isinstance(row,list) or len(row)!=2 or
                any(type(v) is not int or not 0<=v<m for v in row)):
            raise RecurrenceCertificateError('noncanonical residue pair')
    if states[0]!=[s['a0']%m,s['a1']%m]:
        raise RecurrenceCertificateError('incorrect initial modular state')
    # Require first-repeated-state canonical certificate, preventing arbitrary
    # claims about shorter periods and nondeterministic traces.
    known={}
    for i,row in enumerate(states):
        key=tuple(row)
        if i==len(states)-1:
            if key not in known or known[key]!=before:
                raise RecurrenceCertificateError('no matching first repeated state')
        elif key in known:
            raise RecurrenceCertificateError('duplicate state prior to recorded cycle')
        else:
            known[key]=i
        if i+1<len(states):
            a,b=row
            expected=[b,(s['p']*b+s['q']*a)%m]
            if states[i+1]!=expected:
                raise RecurrenceCertificateError('state transition does not follow recurrence')
    return True
