"""AXIOM v0.9: auditable next-order finite-graph conjecture falsification.

A fixed-order proof at n=5 motivates a *new question* at n in {6,7}.
There is no logical implication across graph orders. The target search is
bounded, so no surviving statement is reported as proved.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .graph_claims import GraphStatement, digest, stable
from .graph_campaign import scan_graph_statement
from .graph_checker import check_graph_witness
from .knowledge_graph import _validated_reports

SCHEMA = "axiom.graph.frontier.v1"
ALGORITHM = "replay_verified_n5_templates_then_deterministic_bounded_target_search"
MAX_SOURCE_BYTES = 8_000_000
MAX_SOURCE_COUNT = 64


def _validate_config(seed: int, target_order: int, search_budget: int,
                     max_candidates: int) -> None:
    if (type(seed) is not int or type(target_order) is not int or
            target_order not in (6, 7) or
            type(search_budget) is not int or not 1 <= search_budget <= 2048 or
            type(max_candidates) is not int or not 1 <= max_candidates <= 200):
        raise ValueError("invalid reproducible graph-frontier configuration")


def load_graph_sources(paths: list[str]) -> list[dict]:
    """Load and replay each complete original graph report, never trust a digest alone."""
    if not paths or len(paths) > MAX_SOURCE_COUNT:
        raise ValueError("expected 1..64 original finite-graph research reports")
    data = []
    for raw in paths:
        path = Path(raw)
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("source graph report exceeds configured maximum bytes")
        data.append(json.loads(path.read_text(encoding="utf-8")))
    return _validated_reports(data)


def _sources(reports: list[dict]) -> list[dict]:
    return [
        {"campaign_id": report["campaign_id"], "report_sha256": digest(report),
         "source_schema": report["schema"]}
        for report in reports
    ]


def frontier_plan(reports: list[dict], *, target_order: int,
                  search_budget: int, max_candidates: int) -> list[dict]:
    """Deterministically select missing/under-tested candidates with n=5 motivation.

    Each proof source is complete and nonvacuous. Previously REFUTED claims
    are deliberately excluded. A target with an existing experimental search
    at least as large as the proposed budget is skipped as redundant.
    """
    _validate_config(0, target_order, search_budget, max_candidates)
    verified = _validated_reports(reports)
    motivations: dict[tuple[str, int], list[dict]] = {}
    prior: dict[tuple[str, int], list[dict]] = {}
    for report in verified:
        cid = report["campaign_id"]
        for finding in report["findings"]:
            stmt = GraphStatement.from_dict(finding["statement"])
            family = (stmt.template, stmt.k)
            if (stmt.n == 5 and finding["status"] == "PROVED_IN_SUPPORTED_FRAGMENT"
                    and type(finding["proof"]) is dict
                    and finding["proof"]["certificate"]["vacuous"] is False):
                motivations.setdefault(family, []).append({
                    "campaign_id": cid,
                    "candidate_id": finding["candidate_id"],
                    "proof_certificate_sha256": digest(finding["proof"]["certificate"]),
                    "proven_scope": "exact order n=5 only",
                })
            if stmt.n == target_order:
                prior.setdefault(family, []).append({
                    "campaign_id": cid, "candidate_id": finding["candidate_id"],
                    "status": finding["status"],
                    "search_budget": finding["search"]["search_budget"],
                    "structures_checked": finding["search"]["structures_checked"],
                })
    candidates = []
    for (template, k), proofs in sorted(motivations.items()):
        observed = sorted(prior.get((template, k), []),
                          key=lambda f: (f["campaign_id"], f["candidate_id"]))
        if any(r["status"] == "REFUTED" for r in observed):
            continue
        if any(r["status"] not in ("EXPERIMENTALLY_SUPPORTED",) for r in observed):
            raise ValueError("target order has unsupported original status")
        if observed and max(r["search_budget"] for r in observed) >= search_budget:
            continue
        stmt = GraphStatement(target_order, template, k)
        candidates.append({
            "candidate_id": digest(stmt.to_dict()),
            "statement": stmt.to_dict(),
            "source_proofs": sorted(proofs, key=lambda x: (
                x["campaign_id"], x["candidate_id"])),
            "prior_target_evidence": observed,
            "selection_reason": (
                "UNTESTED_TARGET_ORDER" if not observed else
                "BOUNDED_RETEST_WITH_GREATER_SEARCH_BUDGET"),
            "logical_implication_from_n5": False,
        })
    # Unobserved candidates come first, then previously only experimentally
    # supported candidates; within classes, sort by exact statement identity.
    candidates.sort(key=lambda c: (
        c["selection_reason"] != "UNTESTED_TARGET_ORDER",
        c["statement"]["template"], c["statement"]["k"]))
    return candidates[:max_candidates]


def research_frontier(reports: list[dict], *, seed: int = 42,
                      target_order: int = 6, search_budget: int = 512,
                      max_candidates: int = 200) -> dict[str, Any]:
    """Conduct genuinely executable bounded counterexample discovery."""
    _validate_config(seed, target_order, search_budget, max_candidates)
    verified = _validated_reports(reports)
    config = {"algorithm": ALGORITHM, "seed": seed,
              "target_order": target_order, "search_budget": search_budget,
              "max_candidates": max_candidates}
    planned = frontier_plan(verified, target_order=target_order,
                            search_budget=search_budget,
                            max_candidates=max_candidates)
    findings = []
    for ordinal, item in enumerate(planned):
        stmt = GraphStatement.from_dict(item["statement"])
        sample = scan_graph_statement(stmt, search_budget, seed + ordinal)
        witness = sample["counterexample"]
        if witness is not None:
            check_graph_witness(stmt.to_dict(), witness)
        if sample["method"] != "BOUNDED_LABELLED_GRAPH_SEARCH":
            raise ValueError("frontier target unexpectedly exhaustive")
        findings.append({
            **item,
            "ordinal": ordinal,
            "status": "REFUTED" if witness is not None else
                      "EXPERIMENTALLY_SUPPORTED",
            "search": sample,
            "proof": None,
            "formal_lean_verification": "NOT_PERFORMED",
            "originality": "NOT_ASSESSED",
            "generalization_to_all_orders": "NOT_PROVED",
        })
    counts = {
        "REFUTED": sum(f["status"] == "REFUTED" for f in findings),
        "EXPERIMENTALLY_SUPPORTED": sum(
            f["status"] == "EXPERIMENTALLY_SUPPORTED" for f in findings),
    }
    return {
        "schema": SCHEMA,
        "configuration": config,
        "campaign_id": digest([config, _sources(verified)])[:24],
        "source_reports": _sources(verified),
        "complete": True,
        "candidate_count": len(findings),
        "counts": counts,
        "findings": findings,
        "mathematical_scope":
            "target n=6 or n=7: bounded labelled graph search, not universal or exhaustive proof",
        "source_proof_scope": "original finite graph theorems hold at exactly n=5",
        "formal_verification": "NOT_PERFORMED",
        "novelty": "NOT_ASSESSED",
    }


def audit_frontier(report: dict, reports: list[dict]) -> dict[str, Any]:
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unrecognized graph-frontier report")
    cfg = report.get("configuration")
    if type(cfg) is not dict or set(cfg) != {
            "algorithm", "seed", "target_order", "search_budget", "max_candidates"}:
        raise ValueError("graph-frontier configuration was altered")
    if cfg["algorithm"] != ALGORITHM:
        raise ValueError("graph-frontier algorithm mismatch")
    _validate_config(cfg["seed"], cfg["target_order"], cfg["search_budget"],
                     cfg["max_candidates"])
    replay = research_frontier(reports, seed=cfg["seed"],
                               target_order=cfg["target_order"],
                               search_budget=cfg["search_budget"],
                               max_candidates=cfg["max_candidates"])
    if stable(report) != stable(replay):
        raise ValueError("frontier report disagrees with independent deterministic replay")
    return {
        "schema": SCHEMA, "audit": "ACCEPTED",
        "campaign_id": report["campaign_id"],
        "target_order": cfg["target_order"],
        "candidates": report["candidate_count"],
        "counts": report["counts"],
        "proofs_at_target_order": 0,
        "novelty": "NOT_ASSESSED",
    }


def run_frontier(paths: list[str], *, output: str, seed: int = 42,
                 target_order: int = 6, search_budget: int = 512,
                 max_candidates: int = 200) -> dict:
    verified = load_graph_sources(paths)
    report = research_frontier(
        verified, seed=seed, target_order=target_order,
        search_budget=search_budget, max_candidates=max_candidates)
    audit_frontier(report, verified)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)
    return report
