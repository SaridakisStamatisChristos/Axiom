"""AXIOM v0.16 — genuinely nonduplicative graph falsification across campaigns.

The v0.14 source replay is the trust gate. This executor reconstructs the
EXACT labelled masks tested by the preserved v0.5/v0.9 search algorithms,
then excludes those masks and all masks checked in earlier v0.16 iterations.

An absence of counterexamples is NEVER a proof. Verified n=6 Lean results
remain in the separate v0.15 formal lane; this module produces n=7 bounded
experiments and independently replays every persisted observation.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path

from .graph_campaign import _sample_masks
from .graph_checker import check_graph_witness, reference_properties
from .graph_claims import GraphStatement, digest, holds, stable
from .graph_model import SimpleGraph, edge_positions
from .graph_research_cycle import _tasks, SEARCH_ACTIONS
from .knowledge_graph import _open

SCHEMA = "axiom.graph_novelty_iteration.v1"
SEARCH_METHOD = "BOUNDED_LABELLED_GRAPH_SEARCH"
MAX_ITERATION = 64


def _configuration(iteration: int, seed: int, search_budget: int,
                   task_limit: int) -> dict:
    if type(iteration) is not int or not 0 <= iteration <= MAX_ITERATION:
        raise ValueError("iteration must be 0..64")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be a uint32")
    if type(search_budget) is not int or not 1 <= search_budget <= 512:
        raise ValueError("search_budget must be 1..512")
    if type(task_limit) is not int or not 1 <= task_limit <= 10:
        raise ValueError("task_limit must be 1..10")
    return {
        "iteration": iteration, "seed": seed,
        "search_budget": search_budget, "task_limit": task_limit,
    }


def _sampled_masks(search: dict, order: int) -> set[int]:
    """Replay the *actual historical* landmark/PRNG sampling algorithm."""
    if type(search) is not dict or search.get("method") != SEARCH_METHOD:
        raise ValueError("unexpected historical graph search method")
    budget, seed = search.get("search_budget"), search.get("seed")
    if type(budget) is not int or not 1 <= budget <= 2048:
        raise ValueError("invalid historical search budget")
    if type(seed) is not int or type(search.get("graph_order")) is not int:
        raise ValueError("invalid historical graph search seed/order")
    if search["graph_order"] != order or order != 7:
        raise ValueError("historical search order does not match exact task")
    calculated = _sample_masks(order, seed, budget)
    if (type(search.get("structures_checked")) is not int or
            search["structures_checked"] != len(calculated) or
            search.get("labelled_graph_space") != 1 << len(edge_positions(order))):
        raise ValueError("historical source masks disagree with original coverage")
    return set(calculated)


def historical_exclusions(db_path: str, tasks: list[dict]) -> tuple[dict, dict]:
    """Read ONLY materialized evidence already verified by full source replay.

    The caller MUST obtain tasks from _tasks(), which first runs the
    independent v0.14 audit across all historical source layers.
    """
    selected = {}
    for task in tasks:
        GraphStatement.from_dict(task["statement"])
        if task["statement"]["n"] != 7 or task["action"] not in SEARCH_ACTIONS:
            raise ValueError("only exact-order-seven unresolved tasks may be sampled")
        selected[task["statement_id"]] = task["task_id"]
    masks = {task["task_id"]: set() for task in tasks}
    source_ids = defaultdict(set)
    with _open(db_path, existing=True) as conn:
        nodes = {
            sid: (kind, json.loads(payload))
            for sid, kind, payload in conn.execute(
                "SELECT node_id,kind,payload FROM federation_nodes")
        }
        search_by_finding = defaultdict(list)
        finding_by_statement = defaultdict(list)
        for src, relation, dst in conn.execute(
                "SELECT source,relation,target FROM federation_edges"):
            if relation == "SEARCH_EVIDENCE":
                search_by_finding[src].append(dst)
            elif relation == "INVESTIGATES":
                finding_by_statement[dst].append(src)

        for sid, task_id in selected.items():
            for fid in sorted(finding_by_statement[sid]):
                node = nodes.get(fid)
                if node is None or node[0] != "finding":
                    raise ValueError("original finding link is malformed")
                for search_id in sorted(search_by_finding[fid]):
                    search_node = nodes.get(search_id)
                    if search_node is None or search_node[0] != "search":
                        raise ValueError("original search evidence link is malformed")
                    search = search_node[1]["search"]
                    if search["method"] != SEARCH_METHOD:
                        continue
                    masks[task_id].update(_sampled_masks(search, 7))
                    source_ids[task_id].add("original:" + search_id)

        frontier = conn.execute(
            "SELECT finding_id,statement_id,evidence_json "
            "FROM frontier_findings ORDER BY finding_id").fetchall()
        for fid, sid, payload in frontier:
            if sid not in selected:
                continue
            finding = json.loads(payload)
            if finding["statement"]["n"] != 7:
                raise ValueError("frontier evidence crossed graph order")
            task_id = selected[sid]
            masks[task_id].update(_sampled_masks(finding["search"], 7))
            source_ids[task_id].add("frontier:" + fid)

    summaries = {
        task_id: {
            "distinct_historical_masks": len(masks[task_id]),
            "historical_masks_sha256": digest(sorted(masks[task_id])),
            "source_records": sorted(source_ids[task_id]),
        }
        for task_id in sorted(masks)
    }
    return masks, summaries


def _novel_masks(task_id: str, seed: int, iteration: int, budget: int,
                 forbidden: set[int]) -> list[int]:
    """Full-period odd-stride traversal of the 2^21 labelled graph space."""
    space = 1 << len(edge_positions(7))
    if len(forbidden) + budget > space:
        raise ValueError("insufficient unexplored labelled graph masks")
    raw = hashlib.sha256(
        f"AXIOM-v016:{seed}:{iteration}:{task_id}".encode("ascii")).digest()
    start = int.from_bytes(raw[:8], "big") % space
    stride = (int.from_bytes(raw[8:16], "big") % (space // 2)) * 2 + 1
    result: list[int] = []
    for i in range(space):
        mask = (start + stride * i) % space
        if mask not in forbidden:
            result.append(mask)
            if len(result) == budget:
                return result
    raise ValueError("cannot complete novel graph sampling")


def _trial(task: dict, fp: str, cfg: dict, exclusions: set[int],
           history: dict) -> dict:
    stmt = GraphStatement.from_dict(task["statement"])
    if stmt.n != 7 or task["action"] not in SEARCH_ACTIONS:
        raise ValueError("invalid bounded task in novelty executor")
    selected = _novel_masks(task["task_id"], cfg["seed"],
                            cfg["iteration"], cfg["search_budget"], exclusions)
    visited = []
    applicable = 0
    witness = None
    for mask in selected:
        valid_assumptions, conclusion = holds(stmt, reference_properties(7, mask))
        visited.append(mask)
        if valid_assumptions:
            applicable += 1
            if not conclusion:
                witness = SimpleGraph.from_mask(7, mask).to_dict()
                check_graph_witness(stmt.to_dict(), witness)
                break
    return {
        "task_id": task["task_id"],
        "statement_id": task["statement_id"],
        "action": task["action"],
        "statement": stmt.to_dict(),
        "source_fingerprint": fp,
        "historical_source_count": len(history["source_records"]),
        "historical_distinct_masks": history["distinct_historical_masks"],
        "historical_masks_sha256": history["historical_masks_sha256"],
        "excluded_prior_masks": len(exclusions),
        "masks_checked": visited,
        "new_distinct_masks_checked": len(visited),
        "assumption_satisfying": applicable,
        "status": "REFUTED" if witness is not None else "SURVIVED_BOUNDED_SEARCH",
        "counterexample": witness,
        "exhaustive": False,
        "lean_formal_verification": "NOT_PERFORMED",
        "formal_lean_verification": "NOT_PERFORMED",
        "all_orders_proved": False,
        "original_source_modified": False,
    }


def _render(fp: str, tasks: list[dict], exclusions: dict, history: dict,
            refuted: set[str], cfg: dict, previous_sha256: str) -> dict:
    ranked = [t for t in tasks
              if t["action"] in SEARCH_ACTIONS and t["task_id"] not in refuted]
    results = []
    for task in ranked[:cfg["task_limit"]]:
        tid = task["task_id"]
        results.append(_trial(task, fp, cfg, exclusions[tid], history[tid]))
    return {
        "schema": SCHEMA, "source_fingerprint": fp,
        "configuration": cfg,
        "previous_iteration_sha256": previous_sha256,
        "eligible_open_tasks": len(ranked),
        "attempted": len(results),
        "refutations": sum(t["status"] == "REFUTED" for t in results),
        "bounded_survivals": sum(
            t["status"] == "SURVIVED_BOUNDED_SEARCH" for t in results),
        "new_masks_checked": sum(t["new_distinct_masks_checked"] for t in results),
        "results": results,
        "experimental_only": True,
        "formal_lean_verification": "NOT_PERFORMED",
        "all_order_generalization": "NOT_PROVED",
        "historical_source_modified": False,
    }


def _read_iteration(folder: Path, index: int) -> dict:
    path = folder / f"iteration_{index:04d}.json"
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError(f"missing or excessive research iteration {index}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or data.get("schema") != SCHEMA:
        raise ValueError("unrecognized research iteration evidence")
    return data


def _replay(folder: Path, end: int, fp: str, tasks: list[dict],
            originals: dict, history: dict) -> tuple[dict, set[str], str, dict]:
    excluded = {tid: set(masks) for tid, masks in originals.items()}
    refuted: set[str] = set()
    previous_sha = "0" * 64
    last = None
    for index in range(end + 1):
        saved = _read_iteration(folder, index)
        cfg = saved.get("configuration")
        if type(cfg) is not dict or set(cfg) != {
            "iteration", "seed", "search_budget", "task_limit"
        }:
            raise ValueError("malformed iteration configuration")
        _configuration(**cfg)
        if cfg["iteration"] != index:
            raise ValueError("iteration order or identity changed")
        expected = _render(fp, tasks, excluded, history, refuted, cfg, previous_sha)
        if stable(expected) != stable(saved):
            raise ValueError("persisted research iteration failed independent replay")
        for trial in expected["results"]:
            tid = trial["task_id"]
            if any(mask in excluded[tid] for mask in trial["masks_checked"]):
                raise ValueError("previously tested graph reappeared in research evidence")
            excluded[tid].update(trial["masks_checked"])
            if trial["status"] == "REFUTED":
                refuted.add(tid)
        previous_sha = digest(expected)
        last = expected
    return excluded, refuted, previous_sha, last


def _source(db_path: str) -> tuple[str, list[dict], dict, dict]:
    fp, all_tasks = _tasks(db_path, 7)  # Independently replays all prior source layers.
    tasks = [t for t in all_tasks if t["action"] in SEARCH_ACTIONS]
    originals, history = historical_exclusions(db_path, tasks)
    return fp, tasks, originals, history


def run_iteration(db_path: str, output_dir: str, *, iteration: int = 0,
                  seed: int = 42, search_budget: int = 64,
                  task_limit: int = 2) -> dict:
    cfg = _configuration(iteration, seed, search_budget, task_limit)
    fp, tasks, original, history = _source(db_path)
    folder = Path(output_dir) / "iterations"
    # Ensure no already-written later iteration is silently invalidated.
    if any(folder.glob("iteration_*.json")):
        indexes = sorted(int(path.stem.split("_")[-1]) for path in
                         folder.glob("iteration_*.json"))
        if indexes != list(range(indexes[-1] + 1)):
            raise ValueError("research iteration sequence has missing checkpoints")
        if iteration < indexes[-1]:
            saved = audit_iteration(db_path, str(folder / f"iteration_{iteration:04d}.json"))
            if saved["report"]["configuration"] != cfg:
                raise ValueError("existing research iteration has different parameters")
            return saved["report"]
        if iteration > indexes[-1] + 1:
            raise ValueError("cannot skip research iterations")
    elif iteration != 0:
        raise ValueError("first research iteration must be zero")
    excluded, refuted, prev, _ = _replay(
        folder, iteration - 1, fp, tasks, original, history)
    target = folder / f"iteration_{iteration:04d}.json"
    if target.exists():
        report = _read_iteration(folder, iteration)
        expected = _render(fp, tasks, excluded, history, refuted, cfg, prev)
        if stable(report) != stable(expected):
            raise ValueError("requested existing iteration has different parameters or evidence")
        return report
    report = _render(fp, tasks, excluded, history, refuted, cfg, prev)
    folder.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    # Exclusive creation: never overwrite existing evidence, even after a crash.
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return report


def audit_iteration(db_path: str, report_path: str) -> dict:
    target = Path(report_path)
    if not target.name.startswith("iteration_") or target.suffix != ".json":
        raise ValueError("research evidence is not an iteration artifact")
    try:
        index = int(target.stem.split("_")[-1])
    except ValueError as exc:
        raise ValueError("invalid research iteration filename") from exc
    if target.name != f"iteration_{index:04d}.json":
        raise ValueError("noncanonical research iteration filename")
    _configuration(index, 0, 1, 1)
    fp, tasks, original, history = _source(db_path)
    _, _, _, report = _replay(target.parent, index, fp, tasks, original, history)
    return {
        "audit": "ACCEPTED_SOURCE_AND_SAMPLE_REPLAY",
        "source_fingerprint": fp,
        "iteration": index,
        "new_masks_checked": report["new_masks_checked"],
        "refutations": report["refutations"],
        "experimental_only": True,
        "kernel_reexecution_performed": False,
        "report": report,
    }
