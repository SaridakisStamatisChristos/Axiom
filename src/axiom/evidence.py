"""Strict independent evidence/status audit for generated and persisted findings."""
from __future__ import annotations

from typing import Any
from .certificate_checker import check_certificate, CertificateError
from .mathematics import Statement
from .verification import _witness_is_valid


VALID_TRACES = {
    "REFUTED": ["GENERATED", "UNDER_TEST", "REFUTED"],
    "EXPERIMENTALLY_SUPPORTED": ["GENERATED", "UNDER_TEST", "EXPERIMENTALLY_SUPPORTED"],
    "UNRESOLVED": ["GENERATED", "UNDER_TEST", "UNRESOLVED"],
    "PROVED_IN_SUPPORTED_FRAGMENT": ["GENERATED", "UNDER_TEST", "PROOF_CANDIDATE", "PROVED_IN_SUPPORTED_FRAGMENT"],
}


def audit_finding(finding: dict[str, Any]) -> bool:
    """Reject fabricated/stale evidence. No status promotion from data alone."""
    status = finding["status"]
    if status not in VALID_TRACES or finding["history"] != VALID_TRACES[status]:
        raise ValueError("unsupported or falsified evidence-state transition")
    if finding["originality"] != "NOT_ASSESSED":
        raise ValueError("novelty status cannot be promoted without literature evidence")
    statement = Statement.from_dict(finding["statement"])
    search = finding["search"]
    proof = finding["proof"]
    witness = search.get("counterexample")
    if status == "REFUTED":
        if proof is not None or type(witness) is not dict or set(witness) != set(statement.variables):
            raise ValueError("refutation must contain a witness and no proof")
        if any(type(x) is not int for x in witness.values()):
            raise ValueError("non-integral counterexample")
        values = _witness_is_valid(statement, witness)
        if values is None or search.get("lhs_value") != values[0] or search.get("rhs_value") != values[1]:
            raise ValueError("invalid or inconsistent refutation witness")
    elif status == "PROVED_IN_SUPPORTED_FRAGMENT":
        if witness is not None or not isinstance(proof, dict) or not isinstance(proof.get("certificate"), dict):
            raise ValueError("proof status missing certificate or containing witness")
        try:
            check_certificate(finding["statement"], proof["certificate"])
        except CertificateError as exc:
            raise ValueError("persisted proof certificate failed independent replay") from exc
    else:
        if witness is not None or proof is not None:
            raise ValueError("unverified finding contains proof/witness")
    return True


def audit_report(report: dict[str, Any]) -> dict[str, int]:
    """Replay deterministic generation, identities, evidence and reported totals."""
    import hashlib
    import json
    from .generation import generate
    from .verification import falsify

    if report.get("schema") != "axiom.v0.2.report":
        raise ValueError("unsupported research report schema")
    config = report["configuration"]
    if config.get("engine_version") != "0.2.0":
        raise ValueError("mismatched generator version")
    stable = json.dumps(config, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(stable.encode()).hexdigest()[:24] != report["campaign_id"]:
        raise ValueError("incorrect campaign id")
    produced = generate(config["seed"], config["candidates"], config["domain"])
    cursor = report["progress"]["cursor"]
    if type(cursor) is not int or cursor < 0 or cursor > len(produced):
        raise ValueError("invalid campaign cursor")
    dedup: dict[str, tuple] = {}
    for ordinal, (template, statement) in enumerate(produced[:cursor]):
        key = statement.canonical_key()
        if key not in dedup:
            dedup[key] = (ordinal, template, statement.to_dict())
    findings = report["findings"]
    if len(findings) != len(dedup) or report["progress"]["unique_candidates"] != len(findings):
        raise ValueError("missing or extra candidate findings")
    expected = list(dedup.items())
    counts: dict[str, int] = {}
    for finding, (key, (ordinal, template, stmt)) in zip(findings, expected):
        if (finding["ordinal"] != ordinal or finding["template"] != template or
                finding["statement"] != stmt or
                finding["candidate_id"] != hashlib.sha256(key.encode()).hexdigest()):
            raise ValueError("candidate statement or provenance mismatch")
        audit_finding(finding)
        # Recompute bounded search from its exact recorded campaign parameters.
        # This catches manipulated test counts, search boundaries and witnesses.
        recreated = falsify(Statement.from_dict(stmt), config["lower"], config["upper"],
                            config["max_evals"], config["seed"] + ordinal)
        if finding["search"] != json.loads(json.dumps(recreated, sort_keys=True)):
            raise ValueError("reported search evidence disagrees with deterministic replay")
        counts[finding["status"]] = counts.get(finding["status"], 0) + 1
    if (report["progress"]["duplicates_rejected"] != cursor - len(findings) or
            report["progress"]["complete"] != (cursor == len(produced)) or
            any(report["counts"].get(status, 0) != counts.get(status, 0)
                for status in set(report["counts"]) | set(counts))):
        raise ValueError("incorrect campaign totals")
    return counts
