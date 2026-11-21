"""Deterministic candidate selection for bounded Lean tactic search."""
from itertools import combinations
import re

from .graph_order_split import POSITIVE_BANK, proof_body as order_split_body
from .graph_relations import _vector
from .graph_universal_lean import _lemma_facts

PLAN_VERSION = "axiom.graph_proof_plans.v1"
MAX_PROOF_PLANS = 16
_POOL_SIZE = 7
_ORDER_FACTS = {lemma.theorem for lemma in POSITIVE_BANK}
_MARKER = "AXIOM_ACCEPTED_PLAN:"


def candidates(claim, bank, max_lemmas, limit):
    """Try arithmetic alone, then rank small bundles by signed target coverage."""
    targets = [_vector(side.terms) for side in claim.inequalities()]
    required = [{(i, v > 0) for i, v in enumerate(target) if v} for target in targets]
    positive = {i for target in targets for i, v in enumerate(target) if v > 0}
    signs = {lemma: {(i, v > 0) for i, v in enumerate(lemma.vector) if v}
             for lemma in bank if lemma.premise in ("ALL", claim.bound.assumption)}

    def rank(bundle):
        covered = set().union(*(signs[lemma] for lemma in bundle))
        return (sum(sum(sign for _, sign in side - covered) for side in required),
                sum(sign and i not in positive for i, sign in covered),
                len(bundle), sum(len(side - covered) for side in required),
                tuple(lemma.theorem for lemma in bundle))

    pool = sorted(signs, key=lambda lemma: rank((lemma,)))[:_POOL_SIZE]
    bundles = (bundle for size in range(1, min(max_lemmas, len(pool)) + 1)
               for bundle in combinations(pool, size))
    return [(), *sorted(bundles, key=rank)[:limit - 1]]


def body(claim, plans):
    branches = []
    for index, plan in enumerate(plans):
        matches = [(lemma.theorem, lemma.premise) for lemma in plan
                   if lemma.theorem not in _ORDER_FACTS]
        locals_ = [lemma.theorem for lemma in plan if lemma.theorem in _ORDER_FACTS]
        if locals_:
            steps = order_split_body(claim, matches, locals_)
        else:
            steps = _lemma_facts(matches) + "\n  omega"
        lines = [line[2:] for line in steps.splitlines() if line]
        lines.extend(("done", f'trace "{_MARKER}{index}"'))
        branches.append("  | " + "\n    ".join(lines))
    # Lean may recover from an error in the final alternative. Keep that
    # alternative separate from the branches that can report acceptance.
    branches.append('  | fail "AXIOM proof plans exhausted"')
    return "  first\n" + "\n".join(branches)


def accepted_plan(stdout, candidate_count):
    matches = re.findall(rf"^{_MARKER}([0-9]{{1,2}})$", stdout, re.MULTILINE)
    if len(matches) != 1 or int(matches[0]) >= candidate_count:
        raise ValueError("invalid Lean proof-plan feedback")
    return int(matches[0])
