"""Run only on a genuine installed Lean 4/Mathlib system (never mocked)."""
import os
from pathlib import Path
import subprocess
import tempfile

import pytest

from axiom.lean_backend import _axiom_report, verify_saved_artifact

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(os.getenv('AXIOM_REAL_LEAN') != '1', reason='requires installed pinned Lean 4/Mathlib')


@pytest.mark.parametrize('name', ('example_identity.json', 'example_sos.json'))
def test_real_checker_replays_known_certified_example(name):
    record = verify_saved_artifact(ROOT / 'research/certificates' / name,
                                   project_root=ROOT, timeout_seconds=240)
    assert record['status'] == 'FORMALLY_VERIFIED', record
    assert record['accepted'] is True
    assert set(record['axioms']).issubset({'propext', 'Classical.choice', 'Quot.sound'})
    assert record['mathlib_revision'] and record['dependency_manifest_sha256']


def test_real_checker_discloses_transitive_sorry_axiom():
    # This deliberately invalid theorem is *never* part of generated AXIOM proofs.
    with tempfile.TemporaryDirectory(prefix='axiom-negative-') as tmp:
        source = Path(tmp) / 'NegativeSorry.lean'
        source.write_text('theorem axiom_negative_sorry : False := by sorry\n'
                          '#print axioms axiom_negative_sorry\n', encoding='utf-8')
        result = subprocess.run(['lake', 'env', 'lean', str(source)], cwd=ROOT,
                                capture_output=True, text=True, timeout=120, check=False)
    if result.returncode == 0:
        axioms = _axiom_report(result.stdout, 'axiom_negative_sorry')
        assert axioms is not None and any('sorryAx' in name for name in axioms)
    else:
        # Explicit rejection from Lean itself also suffices, provided it
        # reports an error rather than an infrastructure failure.
        assert 'sorry' in (result.stdout + result.stderr).lower()
