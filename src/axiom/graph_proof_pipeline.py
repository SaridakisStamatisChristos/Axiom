"""Source-replayed discovery handoff to all-orders compositional proof attempts."""
from .graph_claims import digest, stable
from .graph_discovery import audit_campaign
from .graph_proof import audit, prove
from .graph_relations import AffineRelation, known_fact

SCHEMA = "axiom.graph_composite_dispatch.v1"


def _selections(campaign, discovery):
    from .graph_proof_beam import KNOWN_QUEUE, OPEN_QUEUE

    trials = discovery["trials"] + discovery.get("proof_beam", {}).get("trials", [])
    report_hash = digest(discovery)
    for trial in trials:
        claim = AffineRelation.from_dict(trial["statement"])
        if claim.id != trial["candidate_id"] or discovery["selection_used_holdout_data"] is not False:
            raise ValueError("invalid source-replayed selection")
        yield trial, {
            "campaign": campaign, "discovery_sha256": report_hash,
            "source_fingerprint": discovery["source_fingerprint"],
            "training": discovery["discovery"], "configuration": discovery["configuration"],
            "selection_used_holdout_data": False, "trial": trial,
            "queue": trial.get("queue", KNOWN_QUEUE if known_fact(claim) else OPEN_QUEUE),
        }


def _report(campaign, discovery, attempts):
    return {"schema": SCHEMA, "campaign": campaign, "discovery_sha256": digest(discovery),
            "offline_audit_is_execution_attestation": False, "results": attempts}


def dispatch_composed(db, ledger, campaign, *, legacy_reports=None, project_root=".", timeout=180):
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    attempts = [
        prove(trial["statement"], project_root=project_root, timeout=timeout,
              provenance=provenance, external_witness=trial["counterexample"])
        for trial, provenance in _selections(campaign, discovery)
    ]
    return _report(campaign, discovery, attempts)


def audit_composed_dispatch(db, ledger, campaign, artifact, *, legacy_reports=None):
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    if type(artifact) is not dict or type(artifact.get("results")) is not list:
        raise ValueError("invalid compositional dispatch artifact")
    for (trial, provenance), attempt in zip(_selections(campaign, discovery), artifact["results"], strict=True):
        audit(attempt)
        if (stable(attempt["statement"]) != stable(trial["statement"])
                or stable(attempt["provenance"]) != stable(provenance)
                or stable(attempt["external_witness"]) != stable(trial["counterexample"])):
            raise ValueError("proof attempt differs from source-replayed discovery selection")
    expected = _report(campaign, discovery, artifact["results"])
    if stable(artifact) != stable(expected):
        raise ValueError("compositional dispatch evidence differs from replay")
    return expected
