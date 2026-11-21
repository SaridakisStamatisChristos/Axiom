"""Validate and schedule external suggestions using only eligible proof facts."""
import json
import re

from .graph_proof_plans import MAX_PROOF_PLANS

HINT_SCHEMA = "axiom.graph_proof_hints.v1"
CONTEXT_SCHEMA = "axiom.graph_proof_hint_context.v1"
MAX_HINT_BYTES = 16_384
_FACT_NAME = re.compile(r"[a-z][a-z0-9_]{0,95}")


def _unique_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate key in proof hints JSON")
    return result


def read_hints(path):
    with open(path, "rb") as stream:
        data = stream.read(MAX_HINT_BYTES + 1)
    if len(data) > MAX_HINT_BYTES:
        raise ValueError("proof hints file exceeds 16 KiB")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_keys)
    except RecursionError as exc:
        raise ValueError("proof hints JSON is too deeply nested") from exc
    if type(value) is not dict:
        raise ValueError("proof hints must be a JSON object")
    return value


def validate(hints, statement_sha256):
    if (type(hints) is not dict or set(hints) != {"schema", "statement_sha256", "plans"}
            or hints["schema"] != HINT_SCHEMA):
        raise ValueError("invalid proof hints schema")
    if hints["statement_sha256"] != statement_sha256:
        raise ValueError("proof hints do not match statement digest")
    plans = hints["plans"]
    if type(plans) is not list or not 1 <= len(plans) <= MAX_PROOF_PLANS:
        raise ValueError("invalid proof hints plan count")
    for bundle in plans:
        if (type(bundle) is not list or not 1 <= len(bundle) <= 7
                or any(type(name) is not str or not _FACT_NAME.fullmatch(name) for name in bundle)
                or len(set(bundle)) != len(bundle)):
            raise ValueError("invalid proof hints fact bundle")


def eligible_facts(claim, bank):
    return {lemma.theorem: lemma for lemma in bank
            if lemma.premise in ("ALL", claim.bound.assumption)}


def schedule(hints, eligible, ranked, max_lemmas, limit):
    plans = [()]
    hint_indices = [None]
    rejected = []
    seen = set()
    for index, names in enumerate(hints["plans"]):
        key = frozenset(names)
        unavailable = sorted(key.difference(eligible))
        if unavailable:
            rejected.append({"index": index, "reason": "FACT_UNAVAILABLE", "facts": unavailable})
        elif len(names) > max_lemmas:
            rejected.append({"index": index, "reason": "LEMMA_LIMIT"})
        elif key in seen:
            rejected.append({"index": index, "reason": "DUPLICATE"})
        elif len(plans) == limit:
            rejected.append({"index": index, "reason": "PLAN_LIMIT"})
        else:
            plans.append(tuple(eligible[name] for name in sorted(names)))
            hint_indices.append(index)
            seen.add(key)
    for plan in ranked[1:]:
        if len(plans) == limit:
            break
        if frozenset(lemma.theorem for lemma in plan) not in seen:
            plans.append(plan)
            hint_indices.append(None)
    return plans, hint_indices, rejected
