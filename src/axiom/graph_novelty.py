"""Premise-aware exact certificates for affine graph implication."""
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from itertools import combinations, product
from math import gcd, isfinite
from types import MappingProxyType

from .graph_affine import ASSUMPTIONS, VARIABLES
from .graph_claims import digest, stable
from .graph_proof_search import LemmaSpec
from .graph_relations import _FACTS, _vector

PROFILE = "certified-v1"
STRUCTURAL_PROFILE = "certified-v2"
PROFILES = (PROFILE, STRUCTURAL_PROFILE)
LP_ITERATIONS = 1000
MAX_DENOMINATOR = 4096
UNKNOWN_REASONS = {"LP_UNAVAILABLE", "LP_NO_CERTIFICATE", "LP_LIMIT",
                   "LP_RECONSTRUCTION_FAILED", "LP_NUMERIC_FAILURE"}


def entails(premise, required):
    return premise in ASSUMPTIONS and (
        required in ("ALL", premise) or (premise, required) == ("BIPARTITE", "TRIANGLE_FREE")
    )


@lru_cache(maxsize=len(PROFILES))
def fact_bank(profile=PROFILE):
    if profile not in PROFILES:
        raise ValueError("unknown graph novelty profile")
    from .graph_lemma_retrieval import CLIQUE_INDEPENDENCE_INDEX, INDEX_DIGESTS, describe, indexed_facts
    from .graph_proof import BANK

    rows = {}
    sources = {}

    def add(row, source):
        representative = rows.setdefault((row.premise, row.vector, row.rhs), row)
        sources.setdefault(representative.theorem, []).append(source)

    for row in BANK:
        add(row, {"kind": "lean_base_bank", "declaration": row.theorem})
    for entry in indexed_facts(CLIQUE_INDEPENDENCE_INDEX):
        add(entry.lemma, {"kind": "lean_adapter", **describe(entry)})
    for premise, facts in _FACTS.items():
        for index, (weights, rhs) in enumerate(facts):
            row = LemmaSpec(f"symbolic_{premise.lower()}_{index}", premise, _vector(weights.items()), rhs)
            add(row, {"kind": "legacy_symbolic_bound", "source": "graph_relations._FACTS"})
    for name in VARIABLES:
        row = LemmaSpec(f"nonnegative_{name}", "ALL", _vector(((name, -1),)), 0)
        add(row, {"kind": "typed_natural_nonnegativity", "invariant": name})
    if profile == STRUCTURAL_PROFILE:
        from .graph_novelty_facts import STRUCTURAL_FACTS

        for name, premise, weights, rhs, justification in STRUCTURAL_FACTS:
            row = LemmaSpec(name, premise, _vector(weights.items()), rhs)
            add(row, {"kind": "mathematical_argument", "justification": justification})
    bank = {row.theorem: row for row in sorted(rows.values(), key=lambda row: row.theorem)}
    manifest = {"profile": profile, "fact_index": CLIQUE_INDEPENDENCE_INDEX,
                "fact_index_sha256": INDEX_DIGESTS[CLIQUE_INDEPENDENCE_INDEX],
                "variable_order": VARIABLES, "budget": {"closure_rows": 2, "closure_multiplier": 3,
                "lp_iterations": LP_ITERATIONS, "denominator_limit": MAX_DENOMINATOR},
                "premise_entailment": {a: [b for b in ASSUMPTIONS if entails(a, b)] for a in ASSUMPTIONS},
                "facts": [{**asdict(row), "provenance": sources[row.theorem]} for row in bank.values()]}
    return MappingProxyType(bank), manifest, digest(manifest)


def _encoded(weights):
    return [[name, value.numerator, value.denominator]
            for name, value in sorted(weights.items()) if value]


def verify_direction(side, support, *, profile=PROFILE):
    """Accept only a nonnegative exact rational combination of entailed rows."""
    bank = fact_bank(profile)[0]
    if type(support) is not list:
        return False
    weights = {}
    for item in support:
        if type(item) is not list or len(item) != 3:
            return False
        name, numerator, denominator = item
        if (type(name) is not str or name not in bank or name in weights
                or type(numerator) is not int or type(denominator) is not int
                or numerator <= 0 or denominator <= 0 or gcd(numerator, denominator) != 1
                or not entails(side.assumption, bank[name].premise)):
            return False
        weights[name] = Fraction(numerator, denominator)
    vector = tuple(sum(value * bank[name].vector[i] for name, value in weights.items())
                   for i in range(len(VARIABLES)))
    rhs = sum(value * bank[name].rhs for name, value in weights.items())
    return list(weights) == sorted(weights) and vector == _vector(side.terms) and rhs <= side.upper


def verify_certificate(claim, certificate, *, profile=PROFILE):
    sides = claim.inequalities()
    return (type(certificate) is list and len(certificate) == len(sides)
            and all(verify_direction(side, support, profile=profile) for side, support in zip(sides, certificate)))


@lru_cache(maxsize=len(ASSUMPTIONS) * len(PROFILES))
def _closure(premise, profile):
    rows = tuple(row for row in fact_bank(profile)[0].values() if entails(premise, row.premise))
    closure = {}

    def add(vector, rhs, weights):
        if vector not in closure or rhs < closure[vector][0]:
            closure[vector] = rhs, _encoded(weights)

    for row in rows:
        for scale in range(1, 4):
            add(tuple(scale * a for a in row.vector), scale * row.rhs, {row.theorem: Fraction(scale)})
    for a, b in combinations(rows, 2):
        for i, j in product(range(1, 4), repeat=2):
            add(tuple(i * x + j * y for x, y in zip(a.vector, b.vector)), i * a.rhs + j * b.rhs,
                {a.theorem: Fraction(i), b.theorem: Fraction(j)})
    return rows, closure


def _short_certificate(side, profile):
    hit = _closure(side.assumption, profile)[1].get(_vector(side.terms))
    return hit[1] if hit is not None and hit[0] <= side.upper else None


def _propose(side, profile):
    exact = _short_certificate(side, profile)
    if exact is not None:
        return "EXACT_CLOSURE", deepcopy(exact)
    try:
        from scipy.optimize import linprog
    except ImportError:
        return "LP_UNAVAILABLE", None
    rows, _ = _closure(side.assumption, profile)
    try:
        result = linprog([0] * len(rows), A_eq=list(zip(*(row.vector for row in rows))),
                         b_eq=_vector(side.terms), A_ub=[[row.rhs for row in rows]], b_ub=[side.upper],
                         method="highs-ds", options={"maxiter": LP_ITERATIONS})
    except (ValueError, RuntimeError):
        return "LP_NUMERIC_FAILURE", None
    if not result.success:
        return ("LP_LIMIT" if result.status == 1 else "LP_NO_CERTIFICATE"), None
    if any(value < 0 or not isfinite(value) for value in result.x):
        return "LP_RECONSTRUCTION_FAILED", None
    support = _encoded({row.theorem: Fraction(float(value)).limit_denominator(MAX_DENOMINATOR)
                        for row, value in zip(rows, result.x)})
    return ("LP_EXACTLY_CHECKED", support) if verify_direction(side, support, profile=profile) else ("LP_RECONSTRUCTION_FAILED", None)


@lru_cache(maxsize=len(ASSUMPTIONS) * len(PROFILES))
def _equalities(premise, profile):
    directions = {(row.vector, row.rhs) for row in _closure(premise, profile)[0]}
    equations = [list(map(Fraction, (*vector, rhs))) for vector, rhs in sorted(directions)
                 if tuple(-v for v in vector) < vector and (tuple(-v for v in vector), -rhs) in directions]
    pivots = []
    for index in range(len(VARIABLES)):
        pivot = next((row for row in equations if row[index]), None)
        if pivot is None:
            continue
        equations.remove(pivot)
        pivot = [value / pivot[index] for value in pivot]
        equations = [[x - row[index] * y for x, y in zip(row, pivot)] for row in equations]
        pivots.append((index, pivot))
    return pivots


@lru_cache(maxsize=8192)
def _reduced(claim, premise, profile):
    rows = []
    for side in claim.inequalities():
        row = list(map(Fraction, (*_vector(side.terms), side.upper)))
        for index, pivot in _equalities(premise, profile):
            row = [x - row[index] * y for x, y in zip(row, pivot)]
        magnitude = next((abs(value) for value in row[:-1] if value), Fraction(1))
        rows.append(tuple(value / magnitude for value in row))
    return tuple(sorted(rows))


def dominates(left, right, *, profile=PROFILE):
    premise = right.bound.assumption
    if not entails(premise, left.bound.assumption):
        return False
    a, b = _reduced(left, premise, profile), _reduced(right, premise, profile)
    return all(any(source[:-1] == target[:-1] and source[-1] <= target[-1]
                   for source in a) for target in b)


class NoveltyFilter:
    """Store a single decision per canonical statement; replay needs no solver."""

    def __init__(self, replay=None, *, profile=PROFILE):
        if profile not in PROFILES:
            raise ValueError("unknown graph novelty profile")
        self.profile = profile
        self.replay = replay
        self.records = {}
        try:
            solver_version = replay["solver"]["version"] if replay is not None else version("scipy")
        except PackageNotFoundError:
            solver_version = None
        if solver_version is not None and type(solver_version) is not str:
            raise ValueError("invalid novelty solver provenance")
        self.solver = {"backend": "scipy.optimize.linprog/highs-ds", "version": solver_version}

    def classify(self, claim):
        if claim.id in self.records:
            return self.records[claim.id]["status"] == "KNOWN_IMPLICATION"
        sides = claim.inequalities()
        if self.replay is None:
            directions = [{"method": method, "support": support}
                          for method, support in (_propose(side, self.profile) for side in sides)]
        else:
            directions = self.replay["decisions"][claim.id]["directions"]
            if type(directions) is not list or len(directions) != len(sides):
                raise ValueError("novelty replay direction count differs")
            for side, direction in zip(sides, directions):
                method, support = direction["method"], direction["support"]
                exact = _short_certificate(side, self.profile)
                if exact is not None:
                    valid = method == "EXACT_CLOSURE" and support == exact
                elif method == "LP_EXACTLY_CHECKED" and self.solver["version"] is not None:
                    valid = verify_direction(side, support, profile=self.profile)
                else:
                    valid = type(method) is str and method in UNKNOWN_REASONS and support is None
                if not valid:
                    raise ValueError("invalid exact novelty evidence")
        known = verify_certificate(claim, [row["support"] for row in directions], profile=self.profile)
        reduced = [[str(value) for value in row] for row in _reduced(claim, claim.bound.assumption, self.profile)]
        self.records[claim.id] = {"statement": claim.to_dict(), "reduced": reduced, "directions": directions,
                                  "status": "KNOWN_IMPLICATION" if known else "UNKNOWN"}
        return known

    def report(self):
        _, manifest, sha = fact_bank(self.profile)
        result = {"manifest": manifest, "manifest_sha256": sha, "solver": self.solver,
                  "decisions": self.records}
        if self.replay is not None and stable(result) != stable(self.replay):
            raise ValueError("novelty manifest or decisions differ from offline replay")
        return deepcopy(result)
