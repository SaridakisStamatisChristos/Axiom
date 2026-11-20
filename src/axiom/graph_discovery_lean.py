"""Dispatch audited discovery survivors into the closed exact-order Lean bridge."""
from .graph_affine_lean_n3 import ORDER, TOTAL_MASKS, audit_n3_affine, verify_n3_affine
from .graph_checker import reference_properties
from .graph_claims import digest
from .graph_discovery import _failed_side, audit_campaign
from .graph_relations import AffineRelation
from .graph_synthesis import _witness


def dispatch_lean(db_path, ledger, name, *, legacy_reports=None, project_root=".", timeout=180):
    report = audit_campaign(db_path, ledger, name, legacy_reports=legacy_reports)
    results = []
    for trial in report["trials"]:
        if trial["status"] != "EXPERIMENTALLY_SURVIVING":
            continue
        claim = AffineRelation.from_dict(trial["statement"])
        result = {"candidate_id": claim.id, "statement": claim.to_dict(),
                  "formal_graph_order": ORDER, "all_order_generalization": "NOT_PROVED",
                  "counterexample": None, "proof_records": []}
        for mask in range(TOTAL_MASKS):
            failed = _failed_side(claim, reference_properties(ORDER, mask))
            if failed is not None:
                result["counterexample"] = _witness(failed, ORDER, mask)
                break
        if result["counterexample"] is not None:
            result["status"] = "REFUTED_BY_EXACT_ORDER_PRECHECK"
        else:
            for bound in claim.inequalities():
                proof = verify_n3_affine(bound.to_dict(), project_root=project_root,
                                         timeout_seconds=timeout, extended=True)
                audit_n3_affine(proof)
                result["proof_records"].append(proof)
            if all(record["accepted"] for record in result["proof_records"]):
                result["status"] = "FORMALLY_VERIFIED_EXACT_N3"
            elif any(record["lean_kernel_executed"] for record in result["proof_records"]):
                result["status"] = "FIXED_ORDER_PROOF_ATTEMPT_INCOMPLETE"
            else:
                result["status"] = "FIXED_ORDER_PROOF_PENDING"
        results.append(result)
    return {"schema": "axiom.graph_discovery_lean_handoff.v1", "campaign": name,
            "report_sha256": digest(report), "results": results,
            "scope": "only exact n=3 Lean proofs are dispatched",
            "universal_proof_attempt": "PENDING_UNIVERSAL_TRANSLATOR",
            "universal_theorems_promoted": 0}
