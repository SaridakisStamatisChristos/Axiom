"""All-orders proof attempts and offline replay of their evidence."""
from dataclasses import asdict, replace
from hashlib import sha256
from math import isfinite
import re
from time import perf_counter

from .graph_affine import ASSUMPTIONS, VARIABLES
from .graph_affine_lean_n3 import run_affine_kernel
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_discovery import _failed_side
from .graph_edge_induction import (EDGE_INDUCTION_PROOF, EDGE_INDUCTION_RULE,
                                   EDGE_INDUCTION_VERSION)
from .graph_lemma_retrieval import (
    DECOMPOSITION_INDEX, INDEX_DIGESTS, INDEX_VERSION, MAX_RETRIEVED_LEMMAS, describe, retrieve,
)
from .graph_large_witness import SCHEMA as LARGE_WITNESS_SCHEMA, replay_witness
from .graph_lemma_synthesis import MAX_SYNTHESIZED_LEMMAS, SYNTHESIS_VERSION, synthesize
from .graph_model import edge_positions
from .graph_order_split import ORDER_SPLIT_VERSION, POSITIVE_BANK, proof_body as order_split_body
from .graph_proof_hints import (CONTEXT_SCHEMA, HINT_SCHEMA, eligible_facts,
                                schedule as schedule_hints, validate as validate_hints)
from .graph_proof_plans import (MAX_PROOF_PLANS, PLAN_VERSION, accepted_plan,
                                body as plan_body, candidates as plan_candidates)
from .graph_proof_search import LemmaSpec, SearchLimits, search
from .graph_relations import AffineRelation, _vector
from .graph_synthesis import _witness
from .graph_universal_lean import (
    PINNED_MATHLIB_SHA, VERIFIED, _PREMISES, _RULES, _lemma_facts, _render_source, _render_terms,
)
from .lean_backend import ALLOWED_AXIOMS, LEAN_VERSION, MATHLIB_REV, TOOLCHAIN, _axiom_report

SCHEMA = "axiom.graph_proof_attempt.v1"
RETRIEVAL_SCHEMA = "axiom.graph_proof_attempt.v2"
SYNTHESIS_SCHEMA = "axiom.graph_proof_attempt.v3"
SPLIT_SCHEMA = "axiom.graph_proof_attempt.v4"
INDUCTION_SCHEMA = "axiom.graph_proof_attempt.v5"
PLAN_SCHEMA = "axiom.graph_proof_attempt.v6"
HINT_ATTEMPT_SCHEMA = "axiom.graph_proof_attempt.v7"
BANK = tuple(LemmaSpec(name, premise, _vector(weights.items()), rhs)
             for name, premise, weights, rhs in _RULES)
UNAVAILABLE = frozenset({
    "CONFIGURATION_MISSING", "LEAN_UNAVAILABLE", "DEPENDENCY_MANIFEST_MISSING",
    "MATHLIB_REVISION_MISMATCH", "VERSION_CHECK_FAILED", "VERSION_MISMATCH",
})
REJECTED = frozenset({
    "CHECKER_FAILED", "CHECKER_TIMEOUT", "CHECKER_IO_ERROR", "CHECKER_OUTPUT_EXCEEDED",
    "LEAN_AXIOM_REPORT_MISSING", "UNTRUSTED_AXIOMS",
})


def _sha(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _unsupported(statement):
    bound = statement.get("bound") if type(statement) is dict else None
    if type(bound) is dict:
        if bound.get("assumption") not in ASSUMPTIONS:
            return "UNSUPPORTED_PREMISE"
        terms = bound.get("lhs")
        if type(terms) is list and any(type(term) is dict and term.get("symbol") not in VARIABLES
                                       for term in terms):
            return "UNSUPPORTED_INVARIANT"
        if type(terms) is list and len(terms) > 6:
            return "UNSUPPORTED_ARITY"
    return "INVALID_CANONICAL_STATEMENT"


def _small_witness(claim, witness_order):
    for order in range(witness_order + 1):
        for mask in range(1 << len(edge_positions(order))):
            side = _failed_side(claim, reference_properties(order, mask))
            if side is not None:
                return _witness(side, order, mask)
    return None


def _render_lemma(spec, proof):
    terms = [(symbol, weight) for symbol, weight in zip(VARIABLES, spec.vector) if weight]
    return (
        f"private theorem {spec.theorem} {{n : Nat}} (G : SimpleGraph (Fin n)) "
        f"[DecidableRel G.Adj]{_PREMISES[spec.premise]} :\n"
        f"    {_render_terms(terms)} ≤ ({spec.rhs} : Int) := by\n"
        f"{proof}\n")


def _render_adapters(selected, projections, matches):
    used = [step for step in projections if (step.lemma.theorem, step.lemma.premise) in matches]
    dependencies = set(matches) | {(parent.theorem, parent.premise)
                                    for step in used for parent, _ in step.parents}
    entries = [entry for entry in selected if (entry.lemma.theorem, entry.lemma.premise) in dependencies]
    imports = sorted({module for entry in entries for module in entry.imports})
    wrappers = [_render_lemma(entry.lemma, "  " + entry.proof) for entry in entries]
    for step in used:
        facts = _lemma_facts((parent.theorem, parent.premise) for parent, _ in step.parents)
        wrappers.append(_render_lemma(step.lemma, facts + "\n  omega"))
    return imports, ("\n".join(wrappers) + "\n" if wrappers else "")


def _retry(claim, bank, limits, previous_nodes, *, integer_rounding=False):
    result = search(claim, bank, replace(limits, max_nodes=limits.max_nodes - previous_nodes),
                    integer_rounding=integer_rounding)
    return {**result, "nodes": previous_nodes + result["nodes"]}


def _prepare(statement, limits, witness_order, external_witness, retrieval_limit=0,
             synthesis_limit=0, split_order=False, induct_edges=False, plan_limit=0, *,
             proof_hints=None, context_only=False, retrieval_index=INDEX_VERSION):
    if type(retrieval_index) is not str or retrieval_index not in INDEX_DIGESTS:
        raise ValueError("unknown Mathlib retrieval index")
    if retrieval_index != INDEX_VERSION and not retrieval_limit:
        raise ValueError("a nondefault retrieval index requires a positive retrieval limit")
    if type(plan_limit) is not int or not 0 <= plan_limit <= MAX_PROOF_PLANS:
        raise ValueError("invalid proof plan limit")
    if type(induct_edges) is not bool:
        raise ValueError("invalid edge induction option")
    if type(split_order) is not bool:
        raise ValueError("invalid order split option")
    if type(retrieval_limit) is not int or not 0 <= retrieval_limit <= MAX_RETRIEVED_LEMMAS:
        raise ValueError("invalid lemma retrieval limit")
    if type(synthesis_limit) is not int or not 0 <= synthesis_limit <= MAX_SYNTHESIZED_LEMMAS:
        raise ValueError("invalid lemma synthesis limit")
    if type(witness_order) is not int or not 0 <= witness_order <= 5:
        raise ValueError("witness order must be between 0 and 5")
    base = {
        "schema": SCHEMA, "statement": statement, "statement_sha256": digest(statement),
        "candidate_id": None, "scope": None, "toolchain": TOOLCHAIN, "mathlib_rev": MATHLIB_REV,
        "expected_mathlib_revision": PINNED_MATHLIB_SHA, "novelty": "NOT_ASSESSED",
        "offline_audit_is_execution_attestation": False, "invariant_order": list(VARIABLES),
        "search_limits": asdict(limits), "witness_order_limit": witness_order,
        "derivation": None, "counterexample": None, "generated": None,
    }
    if retrieval_limit:
        base.update(schema=RETRIEVAL_SCHEMA, retrieval={
            "limit": retrieval_limit, "index": retrieval_index, "index_sha256": INDEX_DIGESTS[retrieval_index],
            "primary_nodes": None, "initial_derivation": None, "selected": [], "attempted": False,
        })
    if synthesis_limit:
        base.update(schema=SYNTHESIS_SCHEMA, synthesis={
            "limit": synthesis_limit, "method": SYNTHESIS_VERSION,
            "initial_derivation": None, "selected": [], "attempted": False,
        })
    if split_order:
        base.update(schema=SPLIT_SCHEMA, order_split={
            "method": ORDER_SPLIT_VERSION, "attempted": False,
            "initial_derivation": None, "positive_facts": [], "zero_branch": None,
        })
    if induct_edges:
        base.update(schema=INDUCTION_SCHEMA, edge_induction={
            "method": EDGE_INDUCTION_VERSION, "attempted": False,
            "initial_derivation": None, "selected_fact": None,
        })
    if plan_limit:
        base.update(schema=PLAN_SCHEMA, proof_plans={
            "method": PLAN_VERSION, "limit": plan_limit,
            "candidates": [], "accepted_index": None,
        })
    if proof_hints is not None:
        if not plan_limit:
            raise ValueError("proof hints require a positive proof plan limit")
        validate_hints(proof_hints, base["statement_sha256"])
        base.update(schema=HINT_ATTEMPT_SCHEMA, proof_hints={
            "input": proof_hints, "hint_indices": [], "rejected": [],
        })
    try:
        claim = AffineRelation.from_dict(statement)
    except (ValueError, TypeError, KeyError):
        return dict(base, status="UNSUPPORTED", reason=_unsupported(statement))
    base.update(candidate_id=claim.id, scope="ALL_GRAPH_ORDERS")
    witness = _small_witness(claim, witness_order)
    if external_witness is not None:
        if type(external_witness) is not dict:
            raise ValueError("invalid externally supplied graph witness")
        if external_witness.get("schema") == LARGE_WITNESS_SCHEMA:
            replay_witness(claim, external_witness)
        else:
            order = external_witness["exact_order"]
            mask = external_witness["labelled_edge_mask"]
            side = _failed_side(claim, reference_properties(order, mask))
            if side is None or stable(_witness(side, order, mask)) != stable(external_witness):
                raise ValueError("invalid externally supplied graph witness")
        witness = witness or external_witness
    if witness:
        return dict(base, status="COUNTEREXAMPLE", reason="INDEPENDENT_GRAPH_WITNESS",
                    counterexample=witness)

    bank = BANK
    derivation = search(claim, bank, limits)
    selected, projections = (), ()
    integer_rounding = retrieval_index == DECOMPOSITION_INDEX
    if retrieval_limit:
        info = base["retrieval"]
        primary_nodes = derivation["nodes"]
        info["primary_nodes"] = primary_nodes
        remaining = limits.max_nodes - primary_nodes
        if not derivation["derived"] and remaining > 0:
            selected = retrieve(claim, retrieval_limit, index=retrieval_index)
            info.update(selected=[describe(entry) for entry in selected],
                        initial_derivation=derivation, attempted=True)
            bank = BANK + tuple(entry.lemma for entry in selected)
            derivation = _retry(claim, bank, limits, primary_nodes,
                                integer_rounding=integer_rounding)
    if synthesis_limit and not derivation["derived"] and derivation["nodes"] < limits.max_nodes:
        projections = synthesize(claim, bank, synthesis_limit)
        base["synthesis"].update(attempted=True, initial_derivation=derivation,
                                 selected=[step.evidence() for step in projections])
        if projections:
            bank += tuple(step.lemma for step in projections)
            derivation = _retry(claim, bank, limits, derivation["nodes"],
                                integer_rounding=integer_rounding)
    split_used = split_order and not derivation["derived"] and derivation["nodes"] < limits.max_nodes
    if split_used:
        base["order_split"].update(
            attempted=True, initial_derivation=derivation,
            zero_branch="CONNECTED_IMPOSSIBLE" if claim.bound.assumption == "CONNECTED" else "ZERO_INVARIANTS",
        )
        bank += POSITIVE_BANK
        derivation = _retry(claim, bank, limits, derivation["nodes"],
                            integer_rounding=integer_rounding)
    if induct_edges and not derivation["derived"] and derivation["nodes"] < limits.max_nodes:
        base["edge_induction"].update(attempted=True, initial_derivation=derivation)
        bank += (EDGE_INDUCTION_RULE,)
        derivation = _retry(claim, bank, limits, derivation["nodes"],
                            integer_rounding=integer_rounding)
    base["derivation"] = derivation
    plans = ()
    remaining = limits.max_nodes - derivation["nodes"]
    if not derivation["derived"] and plan_limit and remaining:
        limit = min(plan_limit, remaining)
        if context_only:
            return dict(base, status="PLAN_SEARCH_READY", reason="PLAN_SEARCH_READY",
                        facts=eligible_facts(claim, bank), plan_slots=limit)
        plans = plan_candidates(claim, bank, limits.max_lemmas, limit)
        if proof_hints is not None:
            plans, indices, rejected = schedule_hints(
                proof_hints, eligible_facts(claim, bank), plans, limits.max_lemmas, limit)
            base["proof_hints"].update(hint_indices=indices, rejected=rejected)
        base["proof_plans"]["candidates"] = [[lemma.theorem for lemma in plan] for plan in plans]
    if not (derivation["derived"] or plans):
        budget_exhausted = (derivation["node_budget_exhausted"]
                            or ((retrieval_limit or synthesis_limit or split_order or induct_edges or plan_limit)
                                and derivation["nodes"] == limits.max_nodes))
        reason = "NODE_BUDGET_EXHAUSTED" if budget_exhausted else "NO_BOUNDED_COMBINATION"
        return dict(base, status="SEARCH_EXHAUSTED", reason=reason)
    if context_only:
        return dict(base, status="EXACT_DERIVATION_READY", reason="DERIVATION_READY")
    body = None
    local_bank = {lemma.theorem for lemma in POSITIVE_BANK}
    if plans:
        matches = sorted({(lemma.theorem, lemma.premise) for plan in plans for lemma in plan
                          if lemma.theorem not in local_bank})
        body = plan_body(claim, plans)
    else:
        matches = sorted({(lemma["theorem"], lemma["premise"])
                          for direction in derivation["directions"] for lemma in direction["lemmas"]})
        if split_used:
            local_names = [name for name, _ in matches if name in local_bank]
            matches = [(name, premise) for name, premise in matches if name not in local_bank]
            base["order_split"]["positive_facts"] = local_names
            if local_names:
                body = order_split_body(claim, matches, local_names)
    imports, adapters = _render_adapters(selected, projections, matches)
    if (EDGE_INDUCTION_RULE.theorem, EDGE_INDUCTION_RULE.premise) in matches:
        if not plans:
            base["edge_induction"]["selected_fact"] = EDGE_INDUCTION_RULE.theorem
        adapters += _render_lemma(EDGE_INDUCTION_RULE, EDGE_INDUCTION_PROOF) + "\n"
    if plans:
        # The completion guard runs after goal closure. Later branches
        # intentionally stay unexecuted when a plan succeeds.
        adapters += ("set_option linter.unusedTactic false in\n"
                     "set_option linter.unreachableTactic false in\n")
    name = "composite_" + digest(statement)[:24]
    source = _render_source(claim, name, _lemma_facts(matches),
                            adapters=adapters, proof_body=body, imports=imports)
    base["generated"] = {"source": source, "source_sha256": _sha(source),
                         "theorem": f"AxiomGraphUniversal.{name}"}
    return dict(base, status="NOT_ATTEMPTED", reason="DERIVATION_READY")


def _kernel_status(kernel, generated):
    if kernel is None:
        return "NOT_ATTEMPTED", "DERIVATION_READY"
    if type(kernel) is not dict or any(kernel.get(k) != v for k, v in generated.items()):
        raise ValueError("kernel evidence does not match generated source")
    if kernel.get("offline_audit_is_execution_attestation") is not False or kernel.get("command") != [
            "lake", "env", "lean"]:
        raise ValueError("invalid kernel execution metadata")
    for stream in ("stdout", "stderr"):
        log = kernel.get(stream)
        if log is not None and (type(log) is not str or _sha(log) != kernel.get(stream + "_sha256")):
            raise ValueError(f"{stream} digest differs from retained log")
    status = kernel["status"]
    if status == VERIFIED:
        log = kernel.get("stdout")
        axioms = _axiom_report(log, generated["theorem"]) if type(log) is str else None
        if not (kernel.get("accepted") is True and kernel.get("lean_kernel_executed") is True
                and type(kernel.get("checker_exit_code")) is int and kernel["checker_exit_code"] == 0
                and kernel.get("toolchain_file_matches") is True
                and kernel.get("lean_version") == LEAN_VERSION
                and kernel.get("mathlib_revision") == PINNED_MATHLIB_SHA
                and type(kernel.get("dependency_manifest_sha256")) is str
                and re.fullmatch("[0-9a-f]{64}", kernel["dependency_manifest_sha256"])
                and type(kernel.get("stderr")) is str and not kernel["stderr"].strip()
                and kernel.get("stderr_excerpt") == kernel["stderr"][-2048:]
                and axioms is not None and axioms == kernel.get("axioms")
                and set(axioms) <= ALLOWED_AXIOMS):
            raise ValueError("invalid successful kernel evidence")
        return VERIFIED, "LEAN_ACCEPTED_AND_AXIOMS_ALLOWED"
    if kernel.get("accepted") is not False:
        raise ValueError("unexpected kernel acceptance")
    if status in UNAVAILABLE and kernel.get("lean_kernel_executed") is False:
        return "LEAN_UNAVAILABLE", status
    if status in REJECTED:
        return "LEAN_REJECTED", status
    raise ValueError("unknown kernel outcome")


def _check_kernel(attempt, kernel):
    attempt["status"], attempt["reason"] = _kernel_status(kernel, attempt["generated"])
    plans = attempt.get("proof_plans")
    if plans and plans["candidates"] and attempt["status"] == VERIFIED:
        plans["accepted_index"] = accepted_plan(kernel["stdout"], len(plans["candidates"]))


def hint_context(statement, *, limits=SearchLimits(), witness_order=5,
                 retrieval_limit=0, synthesis_limit=0, split_order=False,
                 induct_edges=False, plan_limit=0, retrieval_index=INDEX_VERSION):
    if not plan_limit:
        raise ValueError("proof hint context requires a positive proof plan limit")
    result = _prepare(statement, limits, witness_order, None, retrieval_limit, synthesis_limit,
                      split_order, induct_edges, plan_limit, context_only=True, retrieval_index=retrieval_index)
    facts = result.get("facts", {})
    return {
        "schema": CONTEXT_SCHEMA, "statement": statement,
        "statement_sha256": result["statement_sha256"], "status": result["status"],
        "reason": result["reason"], "invariant_order": result["invariant_order"],
        "plan_slots": result.get("plan_slots", 0), "max_lemmas": limits.max_lemmas,
        "facts": [{**asdict(lemma), "scope": "POSITIVE_ORDER" if lemma in POSITIVE_BANK else "GLOBAL"}
                  for _, lemma in sorted(facts.items())],
        "response_template": {"schema": HINT_SCHEMA,
                              "statement_sha256": result["statement_sha256"], "plans": []},
    }


def prove(statement, *, limits=SearchLimits(), witness_order=5, project_root=".", timeout=180,
          provenance=None, external_witness=None, retrieval_limit=0, synthesis_limit=0,
          split_order=False, induct_edges=False, plan_limit=0, proof_hints=None,
          retrieval_index=INDEX_VERSION):
    if type(timeout) is not int or not 1 <= timeout <= 900:
        raise ValueError("Lean timeout must be between 1 and 900 seconds")
    started = perf_counter()
    attempt = _prepare(statement, limits, witness_order, external_witness,
                       retrieval_limit, synthesis_limit, split_order, induct_edges, plan_limit,
                       proof_hints=proof_hints, retrieval_index=retrieval_index)
    elapsed = perf_counter() - started
    kernel = None
    if attempt["generated"] is not None:
        kernel = run_affine_kernel(
            attempt["generated"], project_root, timeout, VERIFIED,
            expected_mathlib_revision=PINNED_MATHLIB_SHA, retain_logs=True)
        _check_kernel(attempt, kernel)
    attempt.update(kernel=kernel, search_elapsed_seconds=elapsed, lean_timeout_seconds=timeout,
                   provenance=provenance,
                   external_witness=external_witness)
    return {**attempt, "record_sha256": digest(attempt)}


def audit(attempt):
    schemas = (SCHEMA, RETRIEVAL_SCHEMA, SYNTHESIS_SCHEMA, SPLIT_SCHEMA, INDUCTION_SCHEMA, PLAN_SCHEMA,
               HINT_ATTEMPT_SCHEMA)
    if type(attempt) is not dict or attempt.get("schema") not in schemas:
        raise ValueError("unknown proof attempt schema")
    payload = {key: value for key, value in attempt.items() if key != "record_sha256"}
    if digest(payload) != attempt.get("record_sha256"):
        raise ValueError("proof attempt digest mismatch")
    elapsed, timeout = attempt["search_elapsed_seconds"], attempt["lean_timeout_seconds"]
    if (type(elapsed) not in (int, float) or not isfinite(elapsed) or elapsed < 0
            or type(timeout) is not int or not 1 <= timeout <= 900):
        raise ValueError("invalid proof timing evidence")
    schema = attempt["schema"]
    split_order = "order_split" in attempt
    induct_edges = "edge_induction" in attempt
    plan_schemas = (PLAN_SCHEMA, HINT_ATTEMPT_SCHEMA)
    has_hints = "proof_hints" in attempt
    if has_hints and (type(attempt["proof_hints"]) is not dict or "input" not in attempt["proof_hints"]):
        raise ValueError("invalid proof hint evidence")
    hints = attempt["proof_hints"]["input"] if has_hints else None
    has_plans = "proof_plans" in attempt
    if has_plans and (type(attempt["proof_plans"]) is not dict or "limit" not in attempt["proof_plans"]):
        raise ValueError("invalid proof plan evidence")
    plan_limit = attempt["proof_plans"]["limit"] if has_plans else 0
    retrieval_limit = attempt["retrieval"]["limit"] if "retrieval" in attempt else 0
    retrieval_index = attempt["retrieval"]["index"] if "retrieval" in attempt else INDEX_VERSION
    synthesis_limit = attempt["synthesis"]["limit"] if "synthesis" in attempt else 0
    if (("retrieval" in attempt and (schema == SCHEMA or not retrieval_limit))
            or ("synthesis" in attempt and (schema not in (SYNTHESIS_SCHEMA, SPLIT_SCHEMA, INDUCTION_SCHEMA, *plan_schemas)
                                            or not synthesis_limit))
            or (schema not in (INDUCTION_SCHEMA, *plan_schemas) and split_order != (schema == SPLIT_SCHEMA))
            or (schema not in plan_schemas and induct_edges != (schema == INDUCTION_SCHEMA))
            or (has_plans != (schema in plan_schemas))
            or (schema in plan_schemas and not plan_limit)
            or (has_hints != (schema == HINT_ATTEMPT_SCHEMA))
            or (has_hints and hints is None)):
        raise ValueError("unexpected proof fallback evidence")
    expected = _prepare(attempt["statement"], SearchLimits(**attempt["search_limits"]),
                        attempt["witness_order_limit"], attempt["external_witness"],
                        retrieval_limit, synthesis_limit, split_order, induct_edges, plan_limit,
                        proof_hints=hints, retrieval_index=retrieval_index)
    kernel = attempt["kernel"]
    if expected["generated"] is not None:
        _check_kernel(expected, kernel)
    elif kernel is not None:
        raise ValueError("unexpected kernel evidence")
    if any(stable(attempt.get(key)) != stable(value) for key, value in expected.items()):
        raise ValueError("proof attempt differs from deterministic replay")
    return True
