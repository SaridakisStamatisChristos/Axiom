"""Adversarial negative tests for the independent, stdlib-only proof checker."""
import copy
import json
import os
import subprocess
import sys
import pytest
from axiom.certificate_checker import CertificateError, check_certificate
from axiom.mathematics import C, V, Statement, add, mul, power, sub
from axiom.verification import polynomial_proof, inequality_proof, proof_search


def identity():
    x = V('x')
    return Statement(power(add(x, C(3)), 2),
                     add(add(power(x, 2), mul(C(6), x)), C(9)), '==', ('x',))


def test_valid_standalone_certificate_and_mutations(tmp_path):
    statement = identity()
    proof = polynomial_proof(statement)
    cert = proof['certificate']
    assert check_certificate(statement.to_dict(), cert)
    artifact = tmp_path / 'certificate.json'
    artifact.write_text(json.dumps({'statement': statement.to_dict(), 'certificate': cert}))
    checker = os.path.join(os.path.dirname(__file__), '..', 'src', 'axiom', 'certificate_checker.py')
    result = subprocess.run([sys.executable, checker, str(artifact)], capture_output=True, text=True)
    assert result.returncode == 0 and 'ACCEPTED' in result.stdout
    altered = copy.deepcopy(statement.to_dict())
    altered['rhs']['args'][1]['value'] = 10
    with pytest.raises(CertificateError):
        check_certificate(altered, cert)
    for mutation in ('statement_sha256', 'variables', 'rhs_coefficients'):
        bad = copy.deepcopy(cert)
        bad[mutation] = 'untrue' if mutation == 'statement_sha256' else []
        with pytest.raises(CertificateError):
            check_certificate(statement.to_dict(), bad)
    bad = copy.deepcopy(cert)
    bad['rhs_coefficients'][0][1] += 1
    with pytest.raises(CertificateError):
        check_certificate(statement.to_dict(), bad)
    artifact.write_text(json.dumps({'statement': altered, 'certificate': cert}))
    rejected = subprocess.run([sys.executable, checker, str(artifact)], capture_output=True, text=True)
    assert rejected.returncode != 0 and 'REJECTED' in rejected.stderr


def test_quadratic_and_multivariate_sos():
    x, y = V('x'), V('y')
    for stmt in [
        Statement(power(sub(x, C(5)), 2), C(0), '>=', ('x',)),
        Statement(C(0), add(power(add(x, C(2)), 2), C(3)), '<=', ('x',)),
        Statement(add(power(sub(x, C(2)), 2), power(add(y, C(5)), 2)), C(0), '>=', ('x', 'y')),
        Statement(C(25), C(3), '>=', ('x',)),
    ]:
        proof = inequality_proof(stmt)
        assert proof and proof['certificate']['method'] == 'sum_of_squares'
        assert check_certificate(stmt.to_dict(), proof['certificate'])
        forged = copy.deepcopy(proof['certificate'])
        forged['constant'] += 1
        with pytest.raises(CertificateError):
            check_certificate(stmt.to_dict(), forged)


def test_false_and_unsupported_inequalities_never_proved():
    x = V('x')
    assert proof_search(Statement(x, C(0), '>=', ('x',))) is None
    assert proof_search(Statement(sub(power(x, 2), C(1)), C(0), '>=', ('x',))) is None
    assert proof_search(Statement(mul(x, sub(C(8), x)), C(0), '>=', ('x',), (('x', 0, 8),))) is None
    assert proof_search(Statement(power(x, 3), C(0), '>=', ('x',))) is None


def test_reject_malformed_and_resource_excess(tmp_path):
    stmt = identity().to_dict()
    cert = polynomial_proof(identity())['certificate']
    for bad in [None, [], {'schema': cert['schema']}, {**cert, 'secret_ax': 'allowed'},
                {**cert, 'method': 'verified_by_Lean'}, {**cert, 'lhs_coefficients': [[[0], 0]]}]:
        with pytest.raises(CertificateError):
            check_certificate(stmt, bad)
    massive = copy.deepcopy(stmt)
    massive['lhs'] = {'op':'const', 'value': 2**5000, 'args': []}
    with pytest.raises(CertificateError):
        check_certificate(massive, cert)


def test_no_sympy_import_in_standalone_checker():
    import pathlib
    p = pathlib.Path(__file__).parent.parent / 'src/axiom/certificate_checker.py'
    code = p.read_text()
    assert 'import sympy' not in code
    assert 'from .verification' not in code


def test_randomized_quadratic_sos_never_disagrees_with_exact_samples():
    import random
    rng = random.Random(2048)
    x, y = V('x'), V('y')
    for _ in range(120):
        a, b = rng.randrange(0, 5), rng.randrange(0, 5)
        dx, dy = rng.randrange(-5, 6), rng.randrange(-5, 6)
        c = rng.randrange(-6, 7)
        lhs = add(add(mul(C(a), power(add(x, C(dx)), 2)),
                      mul(C(b), power(add(y, C(dy)), 2))), C(c))
        statement = Statement(lhs, C(0), '>=', ('x', 'y'))
        proof = inequality_proof(statement)
        if proof is not None:
            assert check_certificate(statement.to_dict(), proof['certificate'])
            for _ in range(12):
                assert statement.holds({'x': rng.randrange(-12, 13),
                                        'y': rng.randrange(-12, 13)})
