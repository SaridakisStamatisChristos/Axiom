"""Independent stdlib-only checker of universal polynomial divisibility certificates.

No SymPy or conjecture generator; the input is validated from raw JSON and
expanded using the pre-existing standalone coefficient checker. The certificate
proves an identity in Z[variables], and hence the number-theory claim in Z.
This is NOT Lean kernel verification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from .certificate_checker import (CertificateError, _normal_form, _plus, _times,
                                   _scale, _load_coefficients, _integer)

SCHEMA = 'axiom.number_theory.polynomial_factor.v1'
STATEMENT_FIELDS = {'lhs','rhs','relation','variables','modulus','bounds'}
CERT_FIELDS = {'schema','statement_sha256','variables','method','quotient'}


def digest(statement: dict) -> str:
    return hashlib.sha256(json.dumps(statement, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('utf-8')).hexdigest()


def validate_statement(data: Any) -> tuple[tuple[str, ...], dict, dict]:
    if not isinstance(data, dict) or set(data) != STATEMENT_FIELDS:
        raise CertificateError('invalid number theory statement fields')
    names = data['variables']
    if (type(names) is not list or not 1 <= len(names) <= 2 or
            any(type(x) is not str or x not in ('x', 'y') for x in names) or
            len(set(names)) != len(names)):
        raise CertificateError('invalid quantified variables')
    kind, modulus = data['relation'], data['modulus']
    if kind == 'congruent':
        _integer(modulus, positive=True)
        if modulus > 2**31:
            raise CertificateError('modulus exceeds supported limit')
    elif kind == 'divides':
        if modulus is not None:
            raise CertificateError('divides cannot have a modulus')
    else:
        raise CertificateError('unsupported relation')
    bounds = data['bounds']
    if not isinstance(bounds, list) or len(bounds) > 2:
        raise CertificateError('invalid bounds')
    used = set()
    for item in bounds:
        if not isinstance(item, list) or len(item) != 3:
            raise CertificateError('malformed bound')
        n, lo, hi = item
        if type(n) is not str or n not in names or n in used or _integer(lo) > _integer(hi):
            raise CertificateError('contradictory or duplicate bound')
        used.add(n)
    budget = [0]
    left = _normal_form(data['lhs'], tuple(names), budget)
    right = _normal_form(data['rhs'], tuple(names), budget)
    return tuple(names), left, right


def check_nt_certificate(statement: Any, certificate: Any) -> bool:
    names, lhs, rhs = validate_statement(statement)
    if not isinstance(certificate, dict) or set(certificate) != CERT_FIELDS:
        raise CertificateError('malformed number theory certificate')
    if (certificate['schema'] != SCHEMA or
            certificate['method'] != 'integer_polynomial_multiple' or
            certificate['variables'] != list(names) or
            certificate['statement_sha256'] != digest(statement)):
        raise CertificateError('wrong certificate scope, provenance or method')
    quotient = _load_coefficients(certificate['quotient'], len(names))
    if statement['relation'] == 'divides':
        dividend, divisor = rhs, lhs
    else:
        dividend = _plus(lhs, rhs, -1)
        constant = (0,) * len(names)
        divisor = {constant: statement['modulus']}
    if _times(divisor, quotient) != dividend:
        raise CertificateError('proposed polynomial quotient is incorrect')
    return True


def main() -> None:
    p = argparse.ArgumentParser(description='Standalone number-theory certificate checker (not Lean)')
    p.add_argument('artifact', type=Path)
    a = p.parse_args()
    try:
        o = json.loads(a.artifact.read_text(encoding='utf-8'))
        if not isinstance(o, dict) or set(o) != {'statement','certificate'}:
            raise CertificateError('expected statement and certificate')
        check_nt_certificate(o['statement'], o['certificate'])
    except (CertificateError, TypeError, ValueError, RecursionError, KeyError) as exc:
        p.exit(1, f'REJECTED: {exc}\n')
    print('ACCEPTED: integer polynomial factor certificate (not Lean formal verification)')


if __name__ == '__main__':
    main()
