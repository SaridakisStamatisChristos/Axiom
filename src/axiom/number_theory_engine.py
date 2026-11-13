"""Seeded elementary-number-theory discovery, exact symbolic quotient search and falsification."""
from __future__ import annotations
from itertools import product
from typing import Any
import random
import sympy as sp
from .mathematics import C, V, add, sub, mul, power
from .number_theory_model import NTStatement
from .number_theory_checker import (SCHEMA, check_nt_certificate, validate_statement, digest)
from .certificate_checker import CertificateError
from .verification import _sympy, _boundary_order, _independent_tree_evaluation


def generate_nt(seed: int, budget: int) -> list[tuple[str, NTStatement]]:
    if type(seed) is not int or type(budget) is not int or not 1 <= budget <= 100_000:
        raise ValueError('number-theory candidate budget must be [1, 100000]')
    rng = random.Random(seed)
    x, y = V('x'), V('y')
    result: list[tuple[str, NTStatement]] = []
    for ordinal in range(budget):
        m = rng.randint(2, 17)
        k = rng.choice([t for t in range(-9, 10) if t != 0])
        c = rng.randint(-6, 6)
        mutation = rng.choice([0, 0, 0, 1, -1, m])
        template = ordinal % 10
        if template == 0:
            # (x+k) | ((x+k)(y+c) + δ)
            a = add(x, C(k))
            stmt = NTStatement(a, add(mul(a, add(y, C(c))), C(mutation)), 'divides', ('x','y'))
            label = 'variable_linear_factor'
        elif template == 1:
            stmt = NTStatement(C(m), add(mul(C(m), add(x, C(k))), C(mutation)), 'divides', ('x',))
            label = 'constant_divisor'
        elif template == 2:
            stmt = NTStatement(power(add(x, C(m)), 2), add(power(x, 2), C(mutation)),
                               'congruent', ('x',), m)
            label = 'periodic_square_modulus'
        elif template == 3:
            stmt = NTStatement(power(add(x, C(m)), 3), add(power(x, 3), C(mutation)),
                               'congruent', ('x',), m)
            label = 'periodic_cube_modulus'
        elif template == 4:
            a = sub(x, y)
            stmt = NTStatement(a, add(sub(power(x, 2), power(y, 2)), C(mutation)),
                               'divides', ('x','y'))
            label = 'difference_of_squares_factor'
        elif template == 5:
            stmt = NTStatement(x, add(power(x, 2), C(k if mutation else 0)),
                               'divides', ('x',))
            label = 'zero_divisor_boundary'
        elif template == 6:
            stmt = NTStatement(x, add(x, C(m*k+mutation)), 'congruent', ('x',), m)
            label = 'congruence_translation'
        elif template == 7:
            stmt = NTStatement(add(mul(C(m), x), mul(C(k), y)),
                               add(mul(C(k), y), C(mutation)), 'congruent', ('x','y'), m)
            label = 'linear_congruence_cancellation'
        elif template == 8:
            stmt = NTStatement(C(0), C(0 if mutation == 0 else mutation), 'divides', ('x',))
            label = 'zero_divisor_semantics'
        else:
            # True on the recorded finite assumption x=0, not globally true. No
            # polynomial quotient exists for m>=2, so cannot promote to proof.
            stmt = NTStatement(x, C(0), 'congruent', ('x',), m, (('x', 0, 0),))
            label = 'finite_assumption_not_global_proof'
        result.append((label, stmt))
    return result


def polynomial_factor_proof(statement: NTStatement) -> dict[str, Any] | None:
    """Only returns a sound Z-polynomial factor witness; not a complete solver."""
    try:
        validate_statement(statement.to_dict())
    except CertificateError:
        return None
    names = tuple(statement.variables)
    symbols = {n: sp.Symbol(n, integer=True) for n in names}
    generators = [symbols[n] for n in names]
    if statement.relation == 'divides':
        dividend = _sympy(statement.rhs, symbols)
        divisor = _sympy(statement.lhs, symbols)
    else:
        dividend = _sympy(statement.lhs, symbols) - _sympy(statement.rhs, symbols)
        divisor = sp.Integer(statement.modulus)
    target = sp.Poly(dividend, *generators, domain=sp.QQ)
    by = sp.Poly(divisor, *generators, domain=sp.QQ)
    if by.is_zero:
        if not target.is_zero:
            return None
        quotient = sp.Poly(0, *generators, domain=sp.ZZ)
    else:
        quotient, remainder = target.div(by)
        if not remainder.is_zero:
            return None
        if not all(coeff.q == 1 for _, coeff in quotient.terms()):
            return None
    terms = [[list(exponents), int(coefficient)]
             for exponents, coefficient in sorted(quotient.terms()) if coefficient]
    cert = {'schema': SCHEMA, 'statement_sha256': digest(statement.to_dict()),
            'variables': list(names), 'method': 'integer_polynomial_multiple',
            'quotient': terms}
    try:
        check_nt_certificate(statement.to_dict(), cert)
    except CertificateError as exc:
        raise ArithmeticError('CRITICAL: generated NT certificate failed independent checker') from exc
    return {'method': 'integer_polynomial_multiple', 'certificate': cert,
            'checker': {'name': 'axiom.number_theory_checker', 'accepted': True,
                        'trust': 'stdlib_Z_polynomial_factor_identity_not_Lean'},
            'claim_scope': 'universal integer-polynomial divisibility identity',
            'sympy_version': sp.__version__}


def _independent_holds(statement: NTStatement, values: dict[str, int]) -> bool:
    if not statement.assumption_holds(values):
        raise ValueError('witness does not meet assumptions')
    a = _independent_tree_evaluation(statement.lhs, values)
    b = _independent_tree_evaluation(statement.rhs, values)
    if statement.relation == 'congruent':
        return (a - b) % statement.modulus == 0
    return b == 0 if a == 0 else b % a == 0


def _witness_values(statement: NTStatement, env: dict[str, int]) -> tuple[int, int] | None:
    if _independent_holds(statement, env):
        return None
    return (_independent_tree_evaluation(statement.lhs, env),
            _independent_tree_evaluation(statement.rhs, env))


def _minimize(statement: NTStatement, witness: dict[str, int], limits: dict[str, tuple[int,int]],
              budget: int = 80) -> tuple[dict[str,int],int]:
    current = dict(witness)
    names = statement.variables
    probes = 0
    def score(env: dict) -> tuple:
        return (sum(abs(env[x]) for x in names), tuple(abs(env[x]) for x in names),
                tuple(env[x] for x in names))
    improved = True
    while improved and probes < budget:
        improved = False
        for name in names:
            lo, hi = limits[name]
            v = current[name]
            choices = {i for i in (0,1,-1,lo,hi,v//2,-abs(v)//2,abs(v)//2) if lo<=i<=hi}
            if hi-lo<=64:
                choices.update(range(lo,hi+1))
            for n in sorted(choices,key=lambda t:(abs(t),t)):
                trial = dict(current); trial[name] = n
                if score(trial) >= score(current):
                    continue
                if probes >= budget:
                    break
                probes += 1
                if _witness_values(statement,trial) is not None:
                    current=trial; improved=True
    return current,probes


def falsify_nt(statement: NTStatement, lower: int, upper: int,
               max_evals: int, seed: int) -> dict[str, Any]:
    if (type(lower) is not int or type(upper) is not int or lower > upper or
            upper-lower>100_000 or type(max_evals) is not int or
            not 1<=max_evals<=1_000_000 or type(seed) is not int):
        raise ValueError('invalid bounded search budget')
    explicit = {name:(lo,hi) for name,lo,hi in statement.bounds}
    if any(hi-lo>100_000 for lo,hi in explicit.values()):
        raise ValueError('explicit bound exceeds safe search window')
    limits = {name:(max(lower,explicit.get(name,(lower,upper))[0]),
                    min(upper,explicit.get(name,(lower,upper))[1])) for name in statement.variables}
    if any(lo>hi for lo,hi in limits.values()):
        return {'counterexample': None,'tested':0,'search_space':0,'exhaustive':True,
                'search_bounds':limits,'seed':seed,'method':'bounded_integer_enumeration'}
    grids=[_boundary_order(*limits[n],seed+i) for i,n in enumerate(statement.variables)]
    space=1
    for g in grids:space*=len(g)
    checked=0
    for case in product(*grids):
        if checked>=max_evals:break
        env=dict(zip(statement.variables,case)); checked+=1
        if not statement.holds(env):
            if _witness_values(statement,env) is None:
                raise ArithmeticError('CRITICAL: purported NT witness independently passes')
            smaller,probes=_minimize(statement,env,limits)
            values=_witness_values(statement,smaller)
            if values is None:
                raise ArithmeticError('CRITICAL: minimized NT witness fails independent check')
            return {'counterexample':smaller,'lhs_value':values[0], 'rhs_value':values[1],
                    'original_counterexample':env,'minimization':{'method':'coordinate_descent',
                         'probes':probes,'globally_minimal':False},
                    'tested':checked,'search_space':space,'exhaustive':False,
                    'search_bounds':limits,'seed':seed,'method':'bounded_integer_enumeration'}
    return {'counterexample':None,'tested':checked,'search_space':space,
            'exhaustive':checked==space,'search_bounds':limits,'seed':seed,
            'method':'bounded_integer_enumeration'}
