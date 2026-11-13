"""Tests of Lean input safety and outcome parsing. Fake-process runs are NOT kernel verification."""
import copy
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from axiom.certificate_checker import CertificateError
from axiom.lean_backend import (LEAN_VERSION, MATHLIB_REV, TOOLCHAIN, LeanBackendError,
                                _axiom_report, build_lean_source, verify_with_lean,
                                verify_record_integrity, verify_saved_artifact)
from axiom.mathematics import C, V, Statement, add, mul, power
from axiom.verification import inequality_proof, polynomial_proof


def identity():
    x = V('x')
    return Statement(power(add(x, C(3)), 2),
                     add(add(power(x, 2), mul(C(6), x)), C(9)), '==', ('x',))


def sos():
    x, y = V('x'), V('y')
    stmt = Statement(add(power(add(x, C(-3)), 2), power(add(y, C(2)), 2)),
                     C(0), '>=', ('x','y'))
    return stmt


def temp_project(tmp_path):
    (tmp_path / 'lean-toolchain').write_text(TOOLCHAIN + '\n')
    (tmp_path / 'lakefile.toml').write_text('name = "AXIOM"\nversion = "0.3.0"\n'
                                             '[[require]]\nname = "mathlib"\nscope = "leanprover-community"\nrev = "v4.35.0"\n')
    return tmp_path


def test_identity_source_translates_exact_statement_and_audits_axioms():
    stmt = identity()
    certificate = polynomial_proof(stmt)['certificate']
    result = build_lean_source(stmt.to_dict(), certificate)
    assert result['source_sha256'] and result['statement_sha256'] == certificate['statement_sha256']
    assert 'theorem axiom_' in result['source']
    assert '(x : Int)' in result['source']
    assert ' := by\n  ring\n' in result['source']
    assert 'import Mathlib.Tactic.Ring' in result['source']
    assert '#print axioms ' + result['theorem'] in result['source']
    assert result['toolchain'] == TOOLCHAIN


def test_sos_proof_source_has_independent_square_equality():
    stmt = sos()
    proof = inequality_proof(stmt)
    assert proof is not None
    result = build_lean_source(stmt.to_dict(), proof['certificate'])
    assert 'have hs0' in result['source'] and 'have hs1' in result['source']
    assert 'sq_nonneg' in result['source']
    assert 'have hcert' in result['source']
    assert 'nlinarith [hs0, hs1]' in result['source']
    assert result['imports'] == ['Mathlib.Tactic.Ring', 'Mathlib.Tactic.Linarith']


def test_bound_assumptions_are_preserved_without_switching_domains():
    stmt = Statement(add(V('x'), C(0)), V('x'), '==', ('x',), (('x', -7, 10),))
    result = build_lean_source(stmt.to_dict(), polynomial_proof(stmt)['certificate'])
    assert '(h0 : (-7 : Int) ≤ x ∧ x ≤ (10 : Int))' in result['source']
    assert result['assumptions'] == [('x', -7, 10)]


def test_false_and_tampered_certificate_produce_no_source():
    stmt = identity()
    cert = polynomial_proof(stmt)['certificate']
    bad = copy.deepcopy(cert)
    bad['lhs_coefficients'][0][1] += 1
    with pytest.raises(LeanBackendError):
        build_lean_source(stmt.to_dict(), bad)
    bad = copy.deepcopy(stmt.to_dict())
    bad['lhs']['args'][0]['args'][1]['value'] = 99
    with pytest.raises(LeanBackendError):
        build_lean_source(bad, cert)


def test_parser_rejects_missing_duplicate_and_forbidden_transitive_axioms():
    theorem = 'axiom_abcdef0123456789'
    assert _axiom_report(f"/tmp/file.lean:17:0: info: '{theorem}' does not depend on any axioms", theorem) == []
    assert _axiom_report(f"'{theorem}' depends on axioms: [propext, Classical.choice]", theorem) == ['propext', 'Classical.choice']
    assert _axiom_report(f"'{theorem}' depends on axioms: [sorryAx]", theorem) == ['sorryAx']
    assert _axiom_report(f"'{theorem}' depends on axioms: [other.custom]", theorem) == ['other.custom']
    assert _axiom_report(f"'{theorem}' does not depend on any axioms\n'{theorem}' does not depend on any axioms", theorem) is None
    assert _axiom_report('', theorem) is None


def test_without_lean_remains_pending_and_record_replays(tmp_path):
    stmt = identity()
    root = temp_project(tmp_path)
    with patch('axiom.lean_backend.shutil.which', return_value=None):
        record = verify_with_lean(stmt.to_dict(), polynomial_proof(stmt)['certificate'], project_root=root)
    assert not record['accepted'] and record['status'] == 'LEAN_UNAVAILABLE'
    assert verify_record_integrity(record)
    damaged = copy.deepcopy(record)
    damaged['source'] += '\nsorry\n'
    with pytest.raises(LeanBackendError):
        verify_record_integrity(damaged)


def test_missing_toolchain_and_version_mismatch_rejected(tmp_path):
    stmt = identity()
    cert = polynomial_proof(stmt)['certificate']
    r = verify_with_lean(stmt.to_dict(), cert, project_root=tmp_path)
    assert r['status'] == 'CONFIGURATION_MISSING' and not r['accepted']
    root = temp_project(tmp_path)
    with patch('axiom.lean_backend.shutil.which', return_value='/usr/bin/lake'), \
         patch('axiom.lean_backend._dependency_manifest', return_value={'manifest_sha256':'f' * 64,'mathlib_revision':'e' * 40}), \
         patch('axiom.lean_backend.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'Lean (version 4.10.0, test)', '')):
        r = verify_with_lean(stmt.to_dict(), cert, project_root=root)
    assert r['status'] == 'VERSION_MISMATCH' and not r['accepted']


def test_mocked_subprocess_outcomes_are_not_formal_external_execution(tmp_path):
    stmt = identity()
    cert = polynomial_proof(stmt)['certificate']
    root = temp_project(tmp_path)
    name = build_lean_source(stmt.to_dict(), cert)['theorem']
    version = subprocess.CompletedProcess([], 0, f'Lean (version {LEAN_VERSION}, test)', '')
    def run_case(stdout, stderr='', code=0):
        with patch('axiom.lean_backend.shutil.which', return_value='/fake/lake'), \
             patch('axiom.lean_backend._dependency_manifest', return_value={'manifest_sha256':'f' * 64,'mathlib_revision':'e' * 40}), \
             patch('axiom.lean_backend.subprocess.run', side_effect=[version, subprocess.CompletedProcess([], code, stdout, stderr)]):
            return verify_with_lean(stmt.to_dict(), cert, project_root=root)
    good = run_case(f"/tmp/test.lean:12:0: info: '{name}' does not depend on any axioms\n")
    assert good['accepted'] and good['status'] == 'FORMALLY_VERIFIED'
    assert verify_record_integrity(good)
    forbidden = run_case(f"'{name}' depends on axioms: [sorryAx]")
    assert forbidden['status'] == 'UNTRUSTED_AXIOMS' and not forbidden['accepted']
    no_audit = run_case('no axiom audit output')
    assert no_audit['status'] == 'AXIOM_AUDIT_MISSING' and not no_audit['accepted']
    errors = run_case(f"'{name}' does not depend on any axioms", stderr='warning: admit')
    assert errors['status'] == 'CHECKER_FAILED' and not errors['accepted']
    failure = run_case(f"'{name}' does not depend on any axioms", code=1)
    assert failure['status'] == 'CHECKER_FAILED' and not failure['accepted']


def test_timeout_and_input_limits(tmp_path):
    stmt = sos()
    root = temp_project(tmp_path)
    cert = inequality_proof(stmt)['certificate']
    with patch('axiom.lean_backend.shutil.which', return_value='/usr/bin/lake'), \
         patch('axiom.lean_backend._dependency_manifest', return_value={'manifest_sha256':'f' * 64,'mathlib_revision':'e' * 40}), \
         patch('axiom.lean_backend.subprocess.run', side_effect=subprocess.TimeoutExpired(['lake'], timeout=0.01)):
        result = verify_with_lean(stmt.to_dict(), cert, project_root=root)
    assert result['status'] == 'CHECKER_TIMEOUT' and not result['accepted']
    with pytest.raises(LeanBackendError):
        verify_with_lean(stmt.to_dict(), cert, project_root=root, timeout_seconds=0)
    with pytest.raises(LeanBackendError):
        verify_with_lean(stmt.to_dict(), cert, project_root=root, max_memory_mb=1024)


def test_saved_artifact_round_trip_without_installed_lean(tmp_path):
    stmt = identity()
    cert = polynomial_proof(stmt)['certificate']
    root = temp_project(tmp_path)
    artifact = tmp_path / 'identity.json'
    artifact.write_text(json.dumps({'statement': stmt.to_dict(), 'certificate': cert}))
    with patch('axiom.lean_backend.shutil.which', return_value=None):
        evidence = verify_saved_artifact(artifact, project_root=root)
    assert evidence['status'] == 'LEAN_UNAVAILABLE'
