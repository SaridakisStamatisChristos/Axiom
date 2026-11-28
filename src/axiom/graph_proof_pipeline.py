"""Source-replayed discovery handoff to all-orders compositional proof attempts."""
from dataclasses import asdict

from .graph_claims import digest, stable
from .graph_discovery import audit_campaign
from .graph_lemma_retrieval import (
    EXTREMAL_INDEX, CARDINALITY_INDEX, PALETTE_INDEX, CERTIFICATE_INDEX, CLIQUE_INDEPENDENCE_INDEX, CLIQUE_BOUNDS_INDEX, COMPONENT_INDEX,
    COMPONENT_INDEPENDENCE_INDEX,
    DECOMPOSITION_INDEX, INDEX_VERSION, MATCHING_CARDINALITY_INDEX, MATCHING_INDEX,
    SCHEDULED_INDEX, STRUCTURAL_INDEX,
)
from .graph_proof import BANK, SCHEMA as ATTEMPT_SCHEMA, audit, prove
from .graph_proof_hints import validate as validate_hints
from .graph_proof_search import SearchLimits, search
from .graph_relations import AffineRelation, known_fact

SCHEMA = "axiom.graph_composite_dispatch.v1"
PROFILE_SCHEMA = "axiom.graph_composite_dispatch.v2"
DISPATCH_SCHEMAS = (SCHEMA, PROFILE_SCHEMA)
CAMPAIGN_HINT_SCHEMA = "axiom.graph_campaign_proof_hints.v1"
FIXED_PROFILE = "fixed"
EXTENDED_PROFILE = "extended"
STRUCTURAL_PROFILE = "structural"
MATCHING_PROFILE = "matching"
COMPONENT_PROFILE = "components"
COMPONENT_INDEPENDENCE_PROFILE = "component-independence"
CLIQUE_INDEPENDENCE_PROFILE = "clique-independence"
CLIQUE_BOUNDS_PROFILE = "clique-bounds"
DECOMPOSITION_PROFILE = "decomposition"
SCHEDULED_PROFILE = "scheduled"
CARDINALITY_PROFILE = "cardinality"
PALETTE_PROFILE = "palette"
CERTIFICATE_PROFILE = "certificate"
MATCHING_CARDINALITY_PROFILE = "matching-cardinality"
_ENGINES = {
    FIXED_PROFILE: {},
    EXTENDED_PROFILE: {"retrieval_limit": 5, "synthesis_limit": 3, "split_order": True,
                       "induct_edges": True, "plan_limit": 16},
}
_ENGINES[STRUCTURAL_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": STRUCTURAL_INDEX}
_ENGINES[MATCHING_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": MATCHING_INDEX}
_ENGINES[COMPONENT_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": COMPONENT_INDEX}
_ENGINES[COMPONENT_INDEPENDENCE_PROFILE] = {
    **_ENGINES[EXTENDED_PROFILE], "retrieval_index": COMPONENT_INDEPENDENCE_INDEX,
}
_ENGINES[MATCHING_CARDINALITY_PROFILE] = {
    **_ENGINES[EXTENDED_PROFILE], "retrieval_index": MATCHING_CARDINALITY_INDEX,
}

_ENGINES[CLIQUE_INDEPENDENCE_PROFILE] = {
    **_ENGINES[EXTENDED_PROFILE], "retrieval_index": CLIQUE_INDEPENDENCE_INDEX,
}

_ENGINES[CLIQUE_BOUNDS_PROFILE] = {
    **_ENGINES[EXTENDED_PROFILE], "retrieval_index": CLIQUE_BOUNDS_INDEX,
}

_ENGINES[DECOMPOSITION_PROFILE] = {
    **_ENGINES[EXTENDED_PROFILE], "retrieval_index": DECOMPOSITION_INDEX,
}

_ENGINES[SCHEDULED_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": SCHEDULED_INDEX}
_ENGINES["extremal"] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": EXTREMAL_INDEX}
_ENGINES[CARDINALITY_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": CARDINALITY_INDEX}
_ENGINES[PALETTE_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": PALETTE_INDEX}
_ENGINES[CERTIFICATE_PROFILE] = {**_ENGINES[EXTENDED_PROFILE], "retrieval_index": CERTIFICATE_INDEX}


def _selections(campaign, discovery):
    from .graph_proof_beam import KNOWN_QUEUE, OPEN_QUEUE

    trials = discovery["trials"] + discovery.get("proof_beam", {}).get("trials", [])
    report_hash = digest(discovery)
    for trial in trials:
        claim = AffineRelation.from_dict(trial["statement"])
        if claim.id != trial["candidate_id"] or discovery["selection_used_holdout_data"] is not False:
            raise ValueError("invalid source-replayed selection")
        queue = trial.get("queue")
        if queue is None:
            derivable = search(claim, BANK, SearchLimits())["derived"]
            queue = KNOWN_QUEUE if derivable or known_fact(claim) else OPEN_QUEUE
        yield trial, {
            "campaign": campaign, "discovery_sha256": report_hash,
            "source_fingerprint": discovery["source_fingerprint"],
            "training": discovery["discovery"], "configuration": discovery["configuration"],
            "selection_used_holdout_data": False, "trial": trial,
            "queue": queue,
        }


def _configuration(profile, timeout, manifest):
    if type(profile) is not str or profile not in _ENGINES:
        raise ValueError("unknown discovery proof profile")
    if type(timeout) is not int or not 1 <= timeout <= 900:
        raise ValueError("Lean timeout must be between 1 and 900 seconds")
    if profile == FIXED_PROFILE:
        if manifest is not None:
            raise ValueError("campaign proof hints require a non-fixed proof profile")
        return None
    return {"profile": profile, "options": dict(_ENGINES[profile]),
            "timeout_seconds": timeout, "hints": manifest}


def _campaign_hints(selections, manifest):
    if manifest is None:
        return {}
    if (type(manifest) is not dict or set(manifest) != {"schema", "hints"}
            or manifest["schema"] != CAMPAIGN_HINT_SCHEMA
            or type(manifest["hints"]) is not list or not 1 <= len(manifest["hints"]) <= len(selections)):
        raise ValueError("invalid campaign proof hints manifest")
    selected = {digest(trial["statement"]) for trial, _ in selections}
    inputs = {}
    for hints in manifest["hints"]:
        key = hints.get("statement_sha256") if type(hints) is dict else None
        if type(key) is not str or key not in selected or key in inputs:
            raise ValueError("campaign proof hint must identify a unique selected statement")
        validate_hints(hints, key)
        inputs[key] = hints
    return inputs


def _report(campaign, discovery, attempts, configuration):
    result = {"schema": SCHEMA, "campaign": campaign, "discovery_sha256": digest(discovery),
              "offline_audit_is_execution_attestation": False, "results": attempts}
    if configuration is not None:
        result.update(schema=PROFILE_SCHEMA, proof_configuration=configuration)
    return result


def dispatch_composed(db, ledger, campaign, *, legacy_reports=None, project_root=".", timeout=180,
                      proof_profile=FIXED_PROFILE, proof_hints=None):
    configuration = _configuration(proof_profile, timeout, proof_hints)
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    selections = list(_selections(campaign, discovery))
    hints = _campaign_hints(selections, proof_hints)
    attempts = [
        prove(trial["statement"], project_root=project_root, timeout=timeout,
              provenance=provenance, external_witness=trial["counterexample"],
              proof_hints=hints.get(digest(trial["statement"])), **_ENGINES[proof_profile])
        for trial, provenance in selections
    ]
    return _report(campaign, discovery, attempts, configuration)


def _audit_configuration(attempt, configuration, hints):
    if configuration is None:
        if attempt["schema"] != ATTEMPT_SCHEMA:
            raise ValueError("unexpected proof options in fixed discovery dispatch")
        return
    options = {
        "retrieval_limit": attempt.get("retrieval", {}).get("limit", 0),
        "synthesis_limit": attempt.get("synthesis", {}).get("limit", 0),
        "split_order": "order_split" in attempt, "induct_edges": "edge_induction" in attempt,
        "plan_limit": attempt.get("proof_plans", {}).get("limit", 0),
    }
    index = attempt.get("retrieval", {}).get("index", INDEX_VERSION)
    if index != INDEX_VERSION:
        options["retrieval_index"] = index
    if (options != configuration["options"]
            or attempt["lean_timeout_seconds"] != configuration["timeout_seconds"]
            or stable(attempt.get("proof_hints", {}).get("input")) != stable(hints)
            or attempt["search_limits"] != asdict(SearchLimits())
            or attempt["witness_order_limit"] != 5):
        raise ValueError("proof attempt differs from discovery proof configuration")


def audit_composed_dispatch(db, ledger, campaign, artifact, *, legacy_reports=None):
    if (type(artifact) is not dict or artifact.get("schema") not in DISPATCH_SCHEMAS
            or type(artifact.get("results")) is not list):
        raise ValueError("invalid compositional dispatch artifact")
    configuration = None
    if artifact["schema"] == PROFILE_SCHEMA:
        recorded = artifact.get("proof_configuration")
        if type(recorded) is not dict:
            raise ValueError("invalid discovery proof configuration")
        configuration = _configuration(recorded.get("profile"), recorded.get("timeout_seconds"),
                                       recorded.get("hints"))
        if configuration is None or stable(recorded) != stable(configuration):
            raise ValueError("invalid discovery proof configuration")
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    selections = list(_selections(campaign, discovery))
    hints = _campaign_hints(selections, configuration["hints"] if configuration else None)
    for (trial, provenance), attempt in zip(selections, artifact["results"], strict=True):
        audit(attempt)
        if (stable(attempt["statement"]) != stable(trial["statement"])
                or stable(attempt["provenance"]) != stable(provenance)
                or stable(attempt["external_witness"]) != stable(trial["counterexample"])):
            raise ValueError("proof attempt differs from source-replayed discovery selection")
        _audit_configuration(attempt, configuration, hints.get(digest(trial["statement"])))
    expected = _report(campaign, discovery, artifact["results"], configuration)
    if stable(artifact) != stable(expected):
        raise ValueError("compositional dispatch evidence differs from replay")
    return expected
