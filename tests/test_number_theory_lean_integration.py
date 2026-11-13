"""Requires an actual installed pinned Lean 4 + Mathlib; no mocks."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
from axiom.mathematics import V,C,sub,power,add
from axiom.number_theory_model import NTStatement
from axiom.number_theory_engine import polynomial_factor_proof
from axiom.number_theory_lean import verify_nt_with_lean

pytestmark=pytest.mark.skipif(os.getenv('AXIOM_REAL_LEAN')!='1',
                              reason='actual Lean/Mathlib required')
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('stmt',[
    NTStatement(sub(V('x'),C(1)),sub(power(V('x'),2),C(1)),'divides',('x',)),
    NTStatement(power(add(V('x'),C(7)),2),power(V('x'),2),'congruent',('x',),7),
    NTStatement(C(0),C(0),'divides',('x',)),
])
def test_real_lean_integer_number_theory(stmt):
    cert=polynomial_factor_proof(stmt)['certificate']
    result=verify_nt_with_lean(stmt.to_dict(),cert,project_root=ROOT,timeout_seconds=240)
    assert result['status']=='FORMALLY_VERIFIED',result
    assert result['accepted'] is True
    assert set(result['axioms']).issubset({'propext','Classical.choice','Quot.sound'})
