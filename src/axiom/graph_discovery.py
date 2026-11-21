"""Source-replayed affine discovery with transactional holdout history."""
from collections import Counter
from contextlib import closing
from itertools import combinations, product
import json
from pathlib import Path
import sqlite3
from time import perf_counter

from .graph_adaptive import _historical
from .graph_affine import ASSUMPTIONS, INVARIANTS, applicable, check_conjecture
from .graph_campaign import _discovery_properties
from .graph_checker import reference_properties
from .graph_claims import digest, stable
from .graph_guided import audit_guided
from .graph_relations import AffineRelation, implies, known_fact
from .graph_research_cycle import _tasks
from .graph_stratified import audit_followup, sample_stratum
from .graph_synthesis import _bounded_masks, _choose_historical, _config, _data, _witness, audit_synthesis

SCHEMA = "axiom.graph_affine_discovery.v2"
HOLDOUT_ORDER = 7


def _discover(training):
    bank = {}
    counts = Counter()
    for assumption in ASSUMPTIONS:
        groups = [[p for p in training[n] if applicable(assumption, p)] for n in (5, 6, 7)]
        if not all(groups):
            counts["MISSING_PREMISE_COVERAGE"] += 1
            continue
        for x, y in combinations(INVARIANTS, 2):
            for a, b, c in product((-2, -1, 1, 2), (-2, -1, 1, 2), (-1, 0, 1)):
                values = [[a * p[x] + b * p[y] + c * p["n"] for p in group]
                          for group in groups]
                high = max(map(max, values))
                low = min(map(min, values))
                relation = "=" if high == low else "<="
                if abs(high) > 256:
                    counts["OUTSIDE_BOUND"] += 1
                    continue
                tight_orders = sum(high in group for group in values)
                if tight_orders < 2:
                    counts["NOT_CROSS_ORDER_TIGHT"] += 1
                    continue
                counts["EQUALITY_PROPOSED" if relation == "=" else "INEQUALITY_PROPOSED"] += 1
                claim = AffineRelation.normalized({x: a, y: b, "n": c}, high,
                                                  assumption, relation)
                if known_fact(claim):
                    counts["SYMBOLIC_REDUNDANCY"] += 1
                    continue
                margin = max(max(a * p[x] for p in group) + max(b * p[y] for p in group)
                             + c * group[0]["n"] for group in groups) - high
                score = (relation == "=", tight_orders, margin)
                if claim in bank:
                    counts["CANONICAL_DUPLICATE"] += 1
                if claim not in bank or score > bank[claim]:
                    bank[claim] = score
    return [(claim, bank[claim]) for claim in sorted(
        bank, key=lambda item: (bank[item], item.id), reverse=True)], counts


def _failed_side(claim, properties):
    for side in claim.inequalities():
        applies, valid, _ = check_conjecture(side, properties)
        if applies and not valid:
            return side
    return None


def _select(bank, historical, limit):
    selected = []
    refutations = []
    counts = Counter()
    # The finite historical preflight is isolated from all new observations.
    for claim, score in bank:
        if any(implies(prior, claim) for prior, _, _ in selected):
            counts["SYMBOLIC_DOMINATION"] += 1
            continue
        coverage = 0
        for mask, props in historical:
            if not applicable(claim.bound.assumption, props):
                continue
            coverage += 1
            failed = _failed_side(claim, props)
            if failed is not None:
                refutations.append({"candidate_id": claim.id, "statement": claim.to_dict(),
                                    "witness": _witness(failed, HOLDOUT_ORDER, mask)})
                counts["HISTORICALLY_REFUTED"] += 1
                break
        else:
            if coverage == 0:
                counts["NO_HISTORICAL_PREMISE_COVERAGE"] += 1
                continue
            # A later, stronger survivor can subsume an earlier candidate.
            survivors = [entry for entry in selected if not implies(claim, entry[0])]
            counts["SYMBOLIC_DOMINATION"] += len(selected) - len(survivors)
            selected = survivors
            selected.append((claim, score, coverage))
    return selected[:limit], refutations, counts


def _source(db, legacy_reports):
    fingerprint, _ = _tasks(db, HOLDOUT_ORDER)
    masks, _, _, histories = _historical(db)
    legacy = set()
    parents = {}
    paths = legacy_reports or {}
    if set(paths) - {"v18", "guided", "stratified"} or ("stratified" in paths and "v18" not in paths):
        raise ValueError("stratified legacy evidence requires its original v0.18 report")
    if "v18" in paths:
        report = audit_synthesis(db, paths["v18"])["report"]
        parents["v18"] = digest(report)
        legacy.update(mask for trial in report["holdout"]["experiments"]
                      for mask in trial["masks_checked"])
    if "guided" in paths:
        report = audit_guided(db, paths["guided"])["report"]
        parents["guided"] = digest(report)
        legacy.update(mask for trial in report["guided_holdout"]["results"]
                      for mask in trial["masks_checked"])
    if "stratified" in paths:
        report = audit_followup(db, paths["v18"], paths["stratified"])["report"]
        parents["stratified"] = digest(report)
        legacy.update(mask for trial in report["results"] for mask in trial["masks_checked"])
    return fingerprint, masks, histories, parents, legacy


def _experiment(source, cfg, prior_pairs):
    fingerprint, historical, histories, parents, legacy = source
    masks = {5: list(range(1024)),
             6: _bounded_masks(6, cfg["seed"], cfg["n6_training"]),
             7: _choose_historical(historical, cfg["seed"], cfg["n7_training"])}
    reference, metadata = _data(masks)
    training = {n: [_discovery_properties(n, mask) for mask in group]
                for n, group in masks.items()}
    if training != reference:
        raise ValueError("discovery and reference invariant oracles disagree on training data")
    bank, discovery_counts = _discover(training)
    source_graphs = [(mask, reference_properties(HOLDOUT_ORDER, mask))
                     for mask in sorted(historical, key=lambda mask: (-mask.bit_count(), mask))]
    selected, refutations, preflight_counts = _select(bank, source_graphs, cfg["max_candidates"])

    proof_beam = cfg.get("proof_beam", 0)
    if proof_beam:
        from .graph_proof_beam import candidate_beam
        proof_banks, beam_counts = candidate_beam(training, proof_beam)
        beam_summary = {}
        beam_selected = []
        for queue, candidates in proof_banks.items():
            picks, rejected, counts = _select(candidates, source_graphs, cfg["max_candidates"])
            beam_selected.extend((claim, score, count, queue) for claim, score, count in picks)
            beam_summary[queue] = {
                "candidate_count": len(candidates),
                "candidate_bank_sha256": digest([claim.to_dict() for claim, _ in candidates]),
                "historical_counterexamples": rejected,
                "preflight_counts": dict(counts),
            }

    forbidden = historical | legacy | {mask for n, mask in prior_pairs if n == HOLDOUT_ORDER}
    trials = []
    proof_trials = []
    all_selected = [(claim, score, count, None) for claim, score, count in selected]
    if proof_beam:
        all_selected.extend(beam_selected)
    for claim, score, past_count, queue in all_selected:
        # The existing sampler uses its affine prefix as a domain tag. Include
        # relation identity so equality and inequality sample independently.
        proposed, sampling = sample_stratum(
            "affine-graph:" + digest(claim.to_dict()), claim.bound.assumption,
            cfg["seed"], cfg["holdout_budget"], forbidden)
        checked = []
        witness = None
        for mask in proposed:
            checked.append(mask)
            failed = _failed_side(claim, reference_properties(HOLDOUT_ORDER, mask))
            if failed is not None:
                witness = _witness(failed, HOLDOUT_ORDER, mask)
                break
        forbidden.update(checked)
        trial = {
            "candidate_id": claim.id, "statement": claim.to_dict(),
            "selection_score": list(score), "historical_applicable_graphs": past_count,
            "graph_order": HOLDOUT_ORDER, "masks_checked": checked,
            "sampling": sampling, "counterexample": witness,
            "status": ("REFUTED" if witness else
                       "INCONCLUSIVE_NO_ANTECEDENT_COVERAGE" if not checked else
                       "INCONCLUSIVE_SAMPLE_BUDGET" if len(checked) < cfg["holdout_budget"]
                       else "EXPERIMENTALLY_SURVIVING"),
            "universal_proof": "NOT_PROVED", "mathematical_novelty": "NOT_ASSESSED",
        }
        if queue is None:
            trials.append(trial)
        else:
            proof_trials.append({**trial, "queue": queue})
    extra = {"proof_beam": {"search_counts": beam_counts, "queues": beam_summary,
                            "trials": proof_trials}} if proof_beam else {}
    return {
        **extra,
        "schema": SCHEMA, "configuration": cfg, "source_fingerprint": fingerprint,
        "historical_source_histories": histories,
        "historical_masks_sha256": digest(sorted(historical)),
        "legacy_report_sha256": parents,
        "prior_holdout_pairs_sha256": digest(sorted(prior_pairs)),
        "discovery": metadata, "selection_used_holdout_data": False,
        "discovery_invariant_crosscheck": "BOTH_ORACLES_AGREE",
        "candidate_count": len(bank),
        "candidate_bank_sha256": digest([claim.to_dict() for claim, _ in bank]),
        "discovery_counts": dict(discovery_counts), "preflight_counts": dict(preflight_counts),
        "historical_counterexamples": refutations,
        "selection_status": ("SELECTED" if selected else "NO_CANDIDATE_SURVIVED_PREFLIGHT"
                             if bank else "NO_CANDIDATE_PASSED_DISCOVERY_FILTERS"),
        "trials": trials,
    }


def _connection(path):
    db = sqlite3.connect(path, timeout=600)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def _initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        seq INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
        report TEXT NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS checked_masks (
        graph_order INTEGER NOT NULL, mask INTEGER NOT NULL, campaign INTEGER NOT NULL,
        PRIMARY KEY(graph_order, mask), FOREIGN KEY(campaign) REFERENCES campaigns(seq))""")


def _pairs(report):
    trials = report["trials"] + report.get("proof_beam", {}).get("trials", [])
    return {(trial["graph_order"], mask) for trial in trials for mask in trial["masks_checked"]}


def _stored(db, row):
    seq, name, payload, sha = row
    report = json.loads(payload)
    if type(report) is not dict or report.get("schema") != SCHEMA or digest(report) != sha:
        raise ValueError(f"invalid campaign digest or schema: {name}")
    index = set(db.execute(
        "SELECT graph_order, mask FROM checked_masks WHERE campaign = ?", (seq,)))
    if index != _pairs(report):
        raise ValueError(f"campaign mask index differs from evidence: {name}")
    return report


def _campaign_config(seed, n6_training, n7_training, holdout_budget, max_candidates, proof_beam=0):
    cfg = _config(seed, n6_training, n7_training, holdout_budget, max_candidates)
    if type(proof_beam) is not int or not 0 <= proof_beam <= 64:
        raise ValueError("proof beam width must be 0..64")
    if proof_beam:
        cfg["proof_beam"] = proof_beam
    return cfg


def run_campaign(db_path, ledger, name, *, seed=42, n6_training=64, n7_training=64,
                 holdout_budget=24, max_candidates=4, legacy_reports=None, proof_beam=0):
    cfg = _campaign_config(seed, n6_training, n7_training, holdout_budget, max_candidates, proof_beam)
    if type(name) is not str or not name.strip() or len(name) > 128:
        raise ValueError("campaign name must have 1..128 characters")
    source_path, ledger_path = Path(db_path).resolve(), Path(ledger).resolve()
    if source_path == ledger_path or (ledger_path.exists() and source_path.samefile(ledger_path)):
        raise ValueError("campaign ledger must differ from the historical source")
    source = _source(db_path, legacy_reports)
    with closing(_connection(ledger)) as db, db:
        # Serialize new experiments. A failure commits neither masks nor report.
        db.execute("BEGIN IMMEDIATE")
        _initialize(db)
        row = db.execute("SELECT * FROM campaigns WHERE name = ?", (name,)).fetchone()
        if row is not None:
            prior = _replay(db, source, name)
            if prior["configuration"] != cfg:
                raise ValueError("campaign name already has different parameters")
            return prior
        prior = _history(db, source)
        result = _experiment(source, cfg, prior)
        cursor = db.execute("INSERT INTO campaigns(name,report,sha256) VALUES (?,?,?)",
                            (name, stable(result), digest(result)))
        db.executemany("INSERT INTO checked_masks VALUES (?,?,?)",
                       [(order, mask, cursor.lastrowid) for order, mask in sorted(_pairs(result))])
        return result


def _history(db, source, through=None):
    prior = set()
    rows = db.execute("SELECT * FROM campaigns ORDER BY seq")
    for row in rows:
        report = _stored(db, row)
        if report["source_fingerprint"] != source[0] or report["legacy_report_sha256"] != source[3]:
            raise ValueError("campaign ledger is bound to a different historical source or parent")
        if report["prior_holdout_pairs_sha256"] != digest(sorted(prior)):
            raise ValueError("campaign history digest is inconsistent")
        if through is not None:
            expected = _experiment(source, _campaign_config(**report["configuration"]), prior)
            if stable(expected) != stable(report):
                raise ValueError(f"campaign differs from deterministic replay: {row[1]}")
            if row[1] == through:
                return report
        prior.update(_pairs(report))
    if through is not None:
        raise ValueError("unknown graph discovery campaign")
    return prior


def _replay(db, source, name):
    return _history(db, source, through=name)


def audit_campaign(db_path, ledger, name, *, legacy_reports=None, artifact=None):
    if not Path(ledger).is_file():
        raise ValueError("missing graph discovery ledger")
    source = _source(db_path, legacy_reports)
    with closing(_connection(ledger)) as db, db:
        db.execute("BEGIN")
        report = _replay(db, source, name)
    if artifact is not None:
        supplied = json.loads(Path(artifact).read_text(encoding="utf-8"))
        if stable(supplied) != stable(report):
            raise ValueError("exported campaign differs from deterministic replay")
    return report


def benchmark_campaign(db_path, ledger, name, *, legacy_reports=None):
    started = perf_counter()
    report = audit_campaign(db_path, ledger, name, legacy_reports=legacy_reports)
    elapsed = perf_counter() - started
    candidates = report["candidate_count"]
    return {"schema": "axiom.graph_discovery_benchmark.v1", "campaign": name,
            "report_sha256": digest(report), "audit_wall_seconds": elapsed,
            "generated_candidates": candidates,
            "candidates_per_audited_second": candidates / elapsed,
            "selected_candidates": len(report["trials"]),
            "historical_refutations": len(report["historical_counterexamples"]),
            "new_holdout_masks": len(_pairs(report)), "discovery_counts": report["discovery_counts"]}
