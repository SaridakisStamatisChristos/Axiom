"""Closed arbitrary-order Lean proofs for source-bound graph relations."""
from hashlib import sha256
from importlib.resources import files
import re

from .graph_affine_lean_n3 import run_affine_kernel
from .graph_claims import digest, stable
from .graph_discovery import audit_campaign
from .graph_relations import AffineRelation, _implies, _vector
from .lean_backend import ALLOWED_AXIOMS, LEAN_VERSION, MATHLIB_REV, TOOLCHAIN, LeanBackendError

PROOF_SCHEMA = "axiom.graph_universal_lean.v1"
DISPATCH_SCHEMA = "axiom.graph_universal_dispatch.v1"
PINNED_MATHLIB_SHA = "56a005855ea17e0b0958f73ec801ae140b0a1679"
VERIFIED = "FORMALLY_VERIFIED"
_TERMS = {
    "n": "n", "edges": "edges G", "triangles": "triangles G",
    "independence": "independence G", "clique": "clique G",
    "chromatic": "chromatic G", "maximum_degree": "maximumDegree G",
    "matching": "matching G", "components": "components G",
}
_PREMISES = {
    "ALL": "", "CONNECTED": " (premise : G.Connected)",
    "BIPARTITE": " (premise : G.IsBipartite)",
    "TRIANGLE_FREE": " (premise : G.CliqueFree 3)",
}
# Each entry names a bundled, kernel-checked lemma and its exact linear
# statement. The matcher only selects lemmas; Lean still checks the goal.
_RULES = (
    ("clique_le_chromatic", "ALL", {"clique": 1, "chromatic": -1}, 0),
    ("clique_le_triangles_add_two", "ALL", {"clique": 1, "triangles": -1}, 2),
    ("matching_le_edges", "ALL", {"matching": 1, "edges": -1}, 0),
    ("components_le_order", "ALL", {"components": 1, "n": -1}, 0),
    ("connected_edge_bound", "CONNECTED", {"n": 1, "edges": -1}, 1),
    ("connected_component_edge_bound", "CONNECTED", {"n": 1, "edges": -1, "components": -1}, 0),
    ("triangle_free_degree_bound", "TRIANGLE_FREE", {"maximum_degree": 1, "independence": -1}, 0),
)


def _match(bound):
    target = _vector(bound.terms)
    for name, premise, weights, rhs in _RULES:
        if premise not in ("ALL", bound.assumption):
            continue
        if _implies(_vector(weights.items()), rhs, target, bound.upper):
            return name, premise
    return None


def _lemma_facts(matches):
    return "\n".join(
        f"  have h{index} := {lemma} G" + (" premise" if premise != "ALL" else "")
        for index, (lemma, premise) in enumerate(matches)
    )


def _render_terms(terms):
    return " + ".join(f"({weight} : Int) * (({_TERMS[symbol]}) : Int)"
                      for symbol, weight in terms)


def _render_source(claim, name, facts, *, adapters="", proof_body=None, imports=()):
    bound = claim.bound
    prelude = files("axiom").joinpath("lean", "GraphUniversal.lean").read_text(encoding="utf-8")
    source = "".join(f"import {module}\n" for module in imports) + prelude
    terms = _render_terms(bound.terms)
    relation = "≤" if claim.relation == "<=" else "="
    body = f"{facts}\n  omega" if proof_body is None else proof_body
    source += (
        "\nnamespace AxiomGraphUniversal\n"
        f"{adapters}"
        f"theorem {name} (n : Nat) (G : SimpleGraph (Fin n)) [DecidableRel G.Adj]"
        f"{_PREMISES[bound.assumption]} :\n"
        f"    {terms} {relation} ({bound.upper} : Int) := by\n"
        f"{body}\n"
        f"#print axioms {name}\nend AxiomGraphUniversal\n"
    )
    return source


def build_universal_source(statement):
    claim = AffineRelation.from_dict(statement)
    matches = [_match(side) for side in claim.inequalities()]
    if any(match is None for match in matches):
        return None
    name = "claim_" + digest(statement)[:24]
    source = _render_source(claim, name, _lemma_facts(matches))
    return {
        "schema": PROOF_SCHEMA, "statement": statement, "statement_sha256": digest(statement),
        "scope": "every n : Nat and every simple graph on Fin n satisfying the premise",
        "matched_lemmas": [match[0] for match in matches],
        "source": source, "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
        "theorem": f"AxiomGraphUniversal.{name}", "toolchain": TOOLCHAIN,
        "mathlib_rev": MATHLIB_REV,
    }


def audit_universal_proof(record):
    if type(record) is not dict or record.get("schema") != PROOF_SCHEMA:
        raise LeanBackendError("unknown universal graph proof schema")
    expected = build_universal_source(record["statement"])
    if expected is None or any(stable(record.get(k)) != stable(v) for k, v in expected.items()):
        raise LeanBackendError("altered universal graph proof source, statement, or scope")
    if record.get("offline_audit_is_execution_attestation") is not False:
        raise LeanBackendError("invalid offline graph proof attestation")
    if record.get("status") == VERIFIED:
        axioms = record.get("axioms")
        if not (record.get("accepted") is True and record.get("lean_kernel_executed") is True
                and type(record.get("checker_exit_code")) is int and record["checker_exit_code"] == 0
                and record.get("toolchain_file_matches") is True
                and record.get("lean_version") == LEAN_VERSION
                and record.get("mathlib_revision") == PINNED_MATHLIB_SHA
                and all(type(record.get(key)) is str and re.fullmatch("[0-9a-f]{64}", record[key])
                        for key in ("stdout_sha256", "dependency_manifest_sha256"))
                and type(axioms) is list and all(type(x) is str and x in ALLOWED_AXIOMS for x in axioms)):
            raise LeanBackendError("invalid successful universal kernel record")
    elif record.get("accepted") is not False:
        raise LeanBackendError("unaccepted universal graph proof record")
    return True


def _candidates(report):
    for trial in report["trials"]:
        claim = AffineRelation.from_dict(trial["statement"])
        if trial["candidate_id"] != claim.id:
            raise ValueError("discovery candidate identity mismatch")
        yield trial, claim


def _entry(trial, claim, proof):
    status = trial["status"]
    states = ["PROPOSED"]
    if status == "REFUTED":
        states.append("REFUTED")
        handoff = "REFUTED_WITH_WITNESS"
    elif status == "EXPERIMENTALLY_SURVIVING":
        states.append(status)
        if proof is not None and proof["accepted"]:
            states.extend(("PROVED", VERIFIED))
            handoff = VERIFIED
        elif proof is not None:
            handoff = "PENDING_" + proof["status"]
        else:
            handoff = "PENDING_UNSUPPORTED_RELATION"
    else:
        handoff = "PENDING_" + status
    return {
        "candidate_id": claim.id, "statement": claim.to_dict(), "claim_states": states,
        "handoff": handoff, "counterexample": trial["counterexample"],
        "mathematical_novelty": {"status": "NOT_ASSESSED", "literature_sources": []},
        "proof": proof,
    }


def _report(campaign, discovery, entries):
    return {"schema": DISPATCH_SCHEMA, "campaign": campaign,
            "discovery_sha256": digest(discovery),
            "offline_audit_is_execution_attestation": False, "results": entries}


def dispatch_universal(db, ledger, campaign, *, legacy_reports=None, project_root=".", timeout=180):
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    entries = []
    for trial, claim in _candidates(discovery):
        proof = None
        if trial["status"] == "EXPERIMENTALLY_SURVIVING":
            generated = build_universal_source(claim.to_dict())
            if generated is not None:
                proof = run_affine_kernel(generated, project_root, timeout, VERIFIED,
                                          expected_mathlib_revision=PINNED_MATHLIB_SHA)
                audit_universal_proof(proof)
        entries.append(_entry(trial, claim, proof))
    return _report(campaign, discovery, entries)


def audit_dispatch(db, ledger, campaign, artifact, *, legacy_reports=None):
    discovery = audit_campaign(db, ledger, campaign, legacy_reports=legacy_reports)
    if type(artifact) is not dict or type(artifact.get("results")) is not list:
        raise ValueError("invalid universal graph dispatch artifact")
    entries = []
    for (trial, claim), recorded in zip(_candidates(discovery), artifact["results"], strict=True):
        proof = recorded["proof"]
        supported = (trial["status"] == "EXPERIMENTALLY_SURVIVING"
                     and build_universal_source(claim.to_dict()) is not None)
        if supported != (proof is not None):
            raise ValueError("universal proof dispatch does not match the replayed campaign")
        if proof is not None:
            audit_universal_proof(proof)
            if stable(proof["statement"]) != stable(claim.to_dict()):
                raise ValueError("universal proof bound to a different claim")
        entries.append(_entry(trial, claim, proof))
    expected = _report(campaign, discovery, entries)
    if stable(expected) != stable(artifact):
        raise ValueError("universal dispatch evidence differs from replay")
    return expected
