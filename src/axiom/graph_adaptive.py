"""AXIOM v0.17: source-first candidate discovery and information-aware experiments.

The existing v0.14 agenda and v0.16 task history remain immutable. This
independent, source-bound lane enumerates *existing typed grammar*, checks
candidates against audited old n=7 graph masks BEFORE spending new search
budget, deprioritizes elementary bounds, and executes only candidates whose
antecedents have been observed and whose conclusions survived the source probe.

These are experiment-selection heuristics; not theorem discovery, novelty
attestation, universal evidence, or a Lean verification.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path

from .graph_campaign import _discovery_properties
from .graph_checker import reference_properties, check_graph_witness
from .graph_claims import GraphStatement, TEMPLATES, PARAMETERIZED, holds, stable, digest
from .graph_model import SimpleGraph, edge_positions
from .graph_nonduplicate import _novel_masks, _sampled_masks
from .graph_research_cycle import _tasks
from .knowledge_graph import _open

SCHEMA = "axiom.graph_adaptive_discovery.v1"
BANK_SCHEMA = "axiom.graph_candidate_bank.v1"
# These are established elementary facts or direct elementary implications,
# not formal proofs supplied by AXIOM. The policy only changes job priority.
ELEMENTARY = frozenset({
    "handshake", "degree_bound", "triangle_upper_bound", "matching_upper_bound",
    "bipartite_no_triangles", "bipartite_chromatic_bound",
    "forest_bipartite", "forest_edge_count", "tree_edge_count",
    "connected_edge_lower_bound", "connected_has_chromatic_ge_two",
    "clique_le_chromatic", "chromatic_le_delta_plus_one",
    "independence_times_chromatic",
})


def _config(seed: int, source_probe: int, experiment_budget: int,
            task_limit: int) -> dict:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be uint32")
    if type(source_probe) is not int or not 1 <= source_probe <= 256:
        raise ValueError("source_probe must be 1..256")
    if type(experiment_budget) is not int or not 1 <= experiment_budget <= 256:
        raise ValueError("experiment_budget must be 1..256")
    if type(task_limit) is not int or not 1 <= task_limit <= 12:
        raise ValueError("task_limit must be 1..12")
    return {
        "seed": seed, "source_probe": source_probe,
        "experiment_budget": experiment_budget, "task_limit": task_limit,
    }


def _historical(db_path: str) -> tuple[set[int], set[str], set[str], dict]:
    """Original graph masks and statement statuses, AFTER full source audit."""
    masks = set()
    seen = set()
    refuted = set()
    from_sources = defaultdict(int)
    with _open(db_path, existing=True) as db:
        nodes = {
            nid: (kind, json.loads(raw)) for nid, kind, raw in db.execute(
                "SELECT node_id,kind,payload FROM federation_nodes")
        }
        for nid, (kind, item) in sorted(nodes.items()):
            if (kind == "search" and item.get("domain") == "graph" and
                    item["search"].get("method") == "BOUNDED_LABELLED_GRAPH_SEARCH" and
                    item["search"].get("graph_order") == 7):
                original = _sampled_masks(item["search"], 7)
                masks.update(original)
                from_sources["original"] += 1
        for finding_id, statement_id in db.execute(
                "SELECT source,target FROM federation_edges "
                "WHERE relation='INVESTIGATES'"):
            f = nodes.get(finding_id)
            s = nodes.get(statement_id)
            if f is None or s is None:
                raise ValueError("original finding has missing graph statement")
            if (f[0] != "finding" or s[0] != "statement" or
                    f[1].get("domain") != "graph"):
                continue
            stmt = GraphStatement.from_dict(s[1]["statement"])
            if stmt.n != 7:
                continue
            key = stmt.canonical_key()
            seen.add(key)
            if f[1]["status"] == "REFUTED":
                refuted.add(key)
        statements = {
            sid: json.loads(raw)["statement"]
            for sid, raw in db.execute(
                "SELECT statement_id,payload FROM frontier_statements")}
        for sid, raw in db.execute(
                "SELECT statement_id,evidence_json FROM frontier_findings"):
            record = json.loads(raw)
            stmt = GraphStatement.from_dict(statements[sid])
            if stmt.n != 7:
                continue
            seen.add(stmt.canonical_key())
            if record["status"] == "REFUTED":
                refuted.add(stmt.canonical_key())
            masks.update(_sampled_masks(record["search"], 7))
            from_sources["frontier"] += 1
    return masks, seen, refuted, dict(sorted(from_sources.items()))


def _elementary(statement: GraphStatement) -> bool:
    if statement.template in ELEMENTARY:
        return True
    if statement.template == "bipartite_independence_at_least_k":
        # In a bipartite graph, one of the two colour classes has >= ceil(n/2)
        # vertices and is independent. This is a reason to seek formalization,
        # not an AXIOM proof certificate or Lean attestation.
        return statement.k <= (statement.n + 1) // 2
    if statement.template == "edges_le_n_plus_k":
        return statement.n + statement.k >= statement.n * (statement.n - 1) // 2
    return False


def _pool_candidates() -> list[GraphStatement]:
    result = []
    for template in sorted(TEMPLATES):
        values = range(-3, 8) if template in PARAMETERIZED else (0,)
        for k in values:
            result.append(GraphStatement(7, template, k))
    return result


def _probe_masks(masks: set[int], source_probe: int) -> list[int]:
    return sorted(masks, key=lambda m: (
        hashlib.sha256(f"AXIOMv017-source-probe:{m}".encode("ascii")).digest(),
        m))[:source_probe]


def _pilot(stmt: GraphStatement, masks: list[int], cache: dict) -> dict:
    checked, applicable, witness = 0, 0, None
    for mask in masks:
        applies, valid = holds(stmt, cache[mask])
        checked += 1
        if applies:
            applicable += 1
            if not valid:
                witness = SimpleGraph.from_mask(7, mask).to_dict()
                check_graph_witness(stmt.to_dict(), witness)
                other_applies, other_valid = holds(stmt, _discovery_properties(7, mask))
                if not other_applies or other_valid:
                    raise ValueError("independent source-probe witness check disagrees")
                break
    return {
        "sampled_old_graphs": checked,
        "antecedent_satisfied": applicable,
        "preexisting_witness": witness,
        "dual_oracle_witness_verified": witness is not None,
    }


def _candidate_bank(masks: set[int], seen: set[str], refuted: set[str],
                    cfg: dict) -> dict:
    probe = _probe_masks(masks, cfg["source_probe"])
    if not probe:
        raise ValueError("historical n=7 source graph bank is empty")
    cache = {mask: reference_properties(7, mask) for mask in probe}
    candidates = []
    for statement in _pool_candidates():
        key = statement.canonical_key()
        pilot = _pilot(statement, probe, cache)
        trivial = _elementary(statement)
        if key in refuted:
            disposition = "ALREADY_REFUTED_IN_AUDITED_SOURCES"
        elif pilot["preexisting_witness"] is not None:
            disposition = "REFUTED_BY_PREEXISTING_GRAPH"
        elif trivial:
            disposition = "DEFER_ELEMENTARY_TO_FORMALIZATION"
        elif pilot["antecedent_satisfied"] == 0:
            disposition = "INSUFFICIENT_ANTECEDENT_COVERAGE"
        else:
            disposition = "ELIGIBLE_FOR_NEW_EXPERIMENT"
        # Subjective resource-priority heuristic, not truth probability.
        # The guardrails above exclude known refutations, elementary bounds
        # and vacuous antecedents BEFORE a candidate may receive any score.
        priority = (
            100 * int(disposition == "ELIGIBLE_FOR_NEW_EXPERIMENT")
            + min(20, pilot["antecedent_satisfied"])
            + 4 * int(TEMPLATES[statement.template][0] is not None)
            + 3 * int(key not in seen)
        )
        candidates.append({
            "candidate_id": "graph-candidate:" + digest(statement.to_dict()),
            "statement": statement.to_dict(),
            "in_original_research_source": key in seen,
            "elementary_prioritization_heuristic": trivial,
            "source_probe": pilot,
            "disposition": disposition,
            "priority_score": priority,
            "not_a_proof": True,
            "mathematical_novelty": "NOT_ASSESSED",
        })
    candidates.sort(key=lambda c: (-c["priority_score"],
                                   c["statement"]["template"],
                                   c["statement"]["k"]))
    return {
        "schema": BANK_SCHEMA,
        "historical_labelled_masks": len(masks),
        "historical_masks_sha256": digest(sorted(masks)),
        "source_probe_masks_sha256": digest(probe),
        "source_probe_masks": probe,
        "source_probe_count": len(probe),
        "candidate_count": len(candidates),
        "eligible_count": sum(c["disposition"] == "ELIGIBLE_FOR_NEW_EXPERIMENT"
                              for c in candidates),
        "candidates": candidates,
        "novelty": "NOT_ASSESSED",
        "theorems_proved": 0,
    }


def _new_experiment(item: dict, fp: str, cfg: dict,
                    excluded: set[int]) -> dict:
    stmt = GraphStatement.from_dict(item["statement"])
    planned = _novel_masks(item["candidate_id"], cfg["seed"], 0,
                           cfg["experiment_budget"], excluded)
    checked, applies, witness = [], 0, None
    for mask in planned:
        yes, valid = holds(stmt, reference_properties(7, mask))
        checked.append(mask)
        if yes:
            applies += 1
            if not valid:
                witness = SimpleGraph.from_mask(7, mask).to_dict()
                check_graph_witness(stmt.to_dict(), witness)
                other_yes, other_valid = holds(stmt, _discovery_properties(7, mask))
                if not other_yes or other_valid:
                    raise ValueError("independent experiment witness check disagrees")
                break
    return {
        "candidate_id": item["candidate_id"],
        "statement": stmt.to_dict(),
        "source_fingerprint": fp,
        "masks_checked": checked,
        "independent_graphs_checked": len(checked),
        "assumption_satisfying": applies,
        "status": "REFUTED" if witness else "SURVIVED_BOUNDED_SEARCH",
        "counterexample": witness,
        "dual_oracle_witness_verified": witness is not None,
        "exhaustive": False,
        "formal_lean_verification": "NOT_PERFORMED",
        "generalization_to_all_n": "NOT_PROVED",
    }


def research_discovery(db_path: str, *, seed: int = 42,
                       source_probe: int = 96,
                       experiment_budget: int = 48,
                       task_limit: int = 4) -> dict:
    cfg = _config(seed, source_probe, experiment_budget, task_limit)
    source_fingerprint, _ = _tasks(db_path, 7)  # Full original replay gate.
    masks, seen, refuted, sources = _historical(db_path)
    bank = _candidate_bank(masks, seen, refuted, cfg)
    selected = [item for item in bank["candidates"]
                if item["disposition"] == "ELIGIBLE_FOR_NEW_EXPERIMENT"][
                    :cfg["task_limit"]]
    excluded = set(masks)
    experiments = []
    for item in selected:
        trial = _new_experiment(item, source_fingerprint, cfg, excluded)
        if set(trial["masks_checked"]) & excluded:
            raise ValueError("new experiment repeated an earlier labelled graph")
        excluded.update(trial["masks_checked"])
        experiments.append(trial)
    return {
        "schema": SCHEMA,
        "configuration": cfg,
        "source_fingerprint": source_fingerprint,
        "audited_sources_by_layer": sources,
        "candidate_bank": bank,
        "new_graph_experiments": experiments,
        "executed": len(experiments),
        "new_distinct_masks_checked": sum(
            x["independent_graphs_checked"] for x in experiments),
        "new_refutations": sum(x["status"] == "REFUTED" for x in experiments),
        "experimental_survivals": sum(
            x["status"] == "SURVIVED_BOUNDED_SEARCH" for x in experiments),
        "strict_old_and_new_mask_nonoverlap": True,
        "formal_kernel_executed": False,
        "mathematical_novelty": "NOT_ASSESSED",
        "source_evidence_modified": False,
        "theorem_promotion_count": 0,
        "universal_theorem_claim": False,
    }


def save_discovery(db_path: str, output: str, *, seed: int = 42,
                   source_probe: int = 96,
                   experiment_budget: int = 48,
                   task_limit: int = 4) -> dict:
    cfg = _config(seed, source_probe, experiment_budget, task_limit)
    path = Path(output)
    if path.exists():
        audited = audit_discovery(db_path, output)
        if audited["report"]["configuration"] != cfg:
            raise ValueError("cannot overwrite immutable research campaign")
        return audited["report"]
    report = research_discovery(db_path, **cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return report


def audit_discovery(db_path: str, report_file: str) -> dict:
    path = Path(report_file)
    if path.stat().st_size > 3_000_000:
        raise ValueError("oversized graph discovery experiment")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if type(recorded) is not dict or recorded.get("schema") != SCHEMA:
        raise ValueError("unknown research discovery schema")
    cfg = recorded.get("configuration")
    if type(cfg) is not dict or set(cfg) != {
        "seed", "source_probe", "experiment_budget", "task_limit"
    }:
        raise ValueError("altered research selection configuration")
    expected = research_discovery(db_path, **cfg)
    if stable(recorded) != stable(expected):
        raise ValueError("independent source-based discovery replay disagrees")
    return {
        "audit": "ACCEPTED_SOURCE_AND_EXPERIMENT_REPLAY",
        "source_fingerprint": expected["source_fingerprint"],
        "candidate_count": expected["candidate_bank"]["candidate_count"],
        "eligible_count": expected["candidate_bank"]["eligible_count"],
        "new_graphs": expected["new_distinct_masks_checked"],
        "source_evidence_modified": False,
        "formal_kernel_executed": False,
        "report": expected,
    }
