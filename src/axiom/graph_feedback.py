"""Replayable counterexample-guided fitting with an order-separated holdout."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import sqlite3

from .graph_active_refute import search
from .graph_affine import VARIABLES
from .graph_campaign import _discovery_properties
from .graph_claims import digest, stable
from .graph_corpus import file_digest, screen_rows, screening_rows
from .graph_discovery import _connection, _discover
from .graph_explicit import ExplicitGraph
from .graph_large_witness import MAX_EXACT_ORDER, replay_witness
from .graph_model import edge_positions
from .graph_novelty import INTEGER_PROFILE, NoveltyFilter
from .graph_refutation_portfolio import structured_graphs
from .graph_relations import AffineRelation
from .graph_synthesis import _bounded_masks, _data

SCHEMA = "axiom.graph.feedback_campaign.v1"
FINAL_SCHEMA = "axiom.graph.feedback_final.v1"


def _configuration(seed=42, rounds=2, candidates=8, corpus_scan=256, corpus_exact=64,
                   active_budget=64, development_order=10, feedback=True, final_sha256=None):
    bounds = ((rounds, 1, 16), (candidates, 1, 128), (corpus_scan, 1, 100_000),
              (corpus_exact, 1, corpus_scan if type(corpus_scan) is int else 0),
              (active_budget, 1, 100_000), (development_order, 7, MAX_EXACT_ORDER - 1))
    if (type(seed) is not int or type(feedback) is not bool
            or any(type(x) is not int or not low <= x <= high for x, low, high in bounds)
            or (final_sha256 is not None and (type(final_sha256) is not str
                                             or not re.fullmatch(r"[0-9a-f]{64}", final_sha256)))):
        raise ValueError("invalid graph feedback campaign configuration")
    return {"seed": seed, "rounds": rounds, "candidates": candidates, "corpus_scan": corpus_scan,
            "corpus_exact": corpus_exact, "active_budget": active_budget,
            "development_order": development_order, "feedback": feedback, "final_sha256": final_sha256}


def _panel(path, split, config):
    """Freeze the actual ordered rows seen by the screener in one read snapshot."""
    cutoff = config["development_order"]
    limit = config["corpus_scan"]
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.execute("BEGIN")
        sources = dict(db.execute("SELECT family, manifest FROM sources ORDER BY family"))
        if (not sources or any(json.loads(value)["split"] != split for value in sources.values())
                or db.execute("SELECT 1 FROM graphs WHERE split<>? LIMIT 1", (split,)).fetchone()):
            raise ValueError(f"expected a dedicated {split} graph corpus")
        if split == "final" and db.execute(
                "SELECT 1 FROM graphs WHERE n<=? OR n>? LIMIT 1", (cutoff, MAX_EXACT_ORDER)).fetchone():
            raise ValueError("final graph orders must lie above the development cutoff and within exact replay")
        rows = list(screening_rows(db, split, max_order=cutoff if split == "development" else MAX_EXACT_ORDER,
                                   limit=limit + (split == "final")))
        if not rows or len(rows) > limit:
            raise ValueError(f"{split} panel is empty or exceeds the sealed scan budget")
        for identity, graph6, n, *_ in rows:
            graph = ExplicitGraph.from_graph6(graph6)
            if graph.n != n or sha256(graph6.encode("ascii")).hexdigest() != identity:
                raise ValueError("campaign corpus graph identity or order differs from its encoding")
    return rows, {"split": split, "graphs": len(rows), "families": list(sources),
                  "panel_sha256": digest(rows), "sources_sha256": digest(sources)}


def _base_training(seed):
    masks = {5: list(range(1024)), 6: _bounded_masks(6, seed, 64),
             7: random.Random(seed).sample(range(1 << len(edge_positions(7))), 64)}
    # Include deterministic sparse graphs so all supported premises have fitting coverage.
    for n in (6, 7):
        weights = {edge: 1 << index for index, edge in enumerate(edge_positions(n))}
        structured = (sum(weights[edge] for edge in graph.edges)
                      for _, graph in structured_graphs(n, "ALL") if graph.n == n)
        masks[n] = list(dict.fromkeys((*masks[n], *structured)))
    exact, metadata = _data(masks)
    if any(_discovery_properties(n, mask) != props
           for n, rows in masks.items() for mask, props in zip(rows, exact[n], strict=True)):
        raise ValueError("graph feedback training oracles disagree")
    return exact, metadata


def _feature_key(properties):
    return tuple(properties[name] for name in (*VARIABLES, "bipartite"))


def _screen(panel, claim, config, split):
    result = screen_rows(panel, claim, config["corpus_exact"], split=split)
    result["coverage_by_order"] = {str(n): counts for n, counts in result["coverage_by_order"].items()}
    return result


def _round(training, panel, config, replay):
    novelty = NoveltyFilter(replay["novelty"] if replay is not None else None, profile=INTEGER_PROFILE)
    bank, counts = _discover(training, novelty)
    trials = []
    for claim, _ in bank[:config["candidates"]]:
        corpus = _screen(panel, claim, config, "development")
        active = None
        if corpus["witness"] is None:
            active = search(claim, [], seed=config["seed"], budget=config["active_budget"],
                            profile="guided-v3", max_order=config["development_order"])
        witness = corpus["witness"] if active is None else active["witness"]
        if witness:
            replay_witness(claim, witness)
            if witness["graph"]["n"] > config["development_order"]:
                raise ValueError("development witness exceeds the sealed order cutoff")
        trials.append({"candidate_id": claim.id, "statement": claim.to_dict(), "corpus": corpus,
                       "active": active, "outcome": "REFUTED" if witness else "SURVIVED_DEVELOPMENT"})
    return {"generated_candidates": len(bank), "candidate_bank_sha256": digest([c.id for c, _ in bank]),
            "discovery_counts": dict(counts), "novelty": novelty.report(), "trials": trials}


def _experiment(config, panel, manifest, replay=None):
    training, base = _base_training(config["seed"])
    features = {_feature_key(p) for rows in training.values() for p in rows}
    rounds = []
    for i in range(config["rounds"]):
        before = {str(n): len(rows) for n, rows in sorted(training.items())}
        training_sha = digest({str(n): rows for n, rows in training.items()})
        result = _round(training, panel, config, None if replay is None else replay["rounds"][i])
        additions = []
        if config["feedback"] and i + 1 < config["rounds"]:
            for trial in result["trials"]:
                stage = "active" if trial["active"] is not None else "corpus"
                witness = trial[stage]["witness"]
                if witness is None:
                    continue
                props = witness["checked_properties"]
                key = _feature_key(props)
                if key not in features:
                    features.add(key)
                    training.setdefault(props["n"], []).append(props)
                    additions.append({"candidate_id": trial["candidate_id"], "stage": stage,
                                      "graph_sha256": witness["graph_sha256"], "order": props["n"]})
        rounds.append({**result, "round": i + 1, "training_counts": before,
                       "training_sha256": training_sha,
                       "next_training_sha256": digest({str(n): rows for n, rows in training.items()}),
                       "feedback_added": additions})
    eligible = [trial["statement"] for trial in rounds[-1]["trials"]
                if trial["outcome"] == "SURVIVED_DEVELOPMENT"]
    return {"schema": SCHEMA, "configuration": config, "development_panel": manifest, "base_training": base,
            "rounds": rounds, "frozen_candidates": eligible, "frozen_candidates_sha256": digest(eligible)}


def _stored(db, name):
    row = db.execute("SELECT report, sha256 FROM feedback_campaigns WHERE name=?", (name,)).fetchone()
    if row is None:
        raise ValueError("unknown graph feedback campaign")
    report = json.loads(row[0])
    if report["schema"] != SCHEMA or digest(report) != row[1]:
        raise ValueError("invalid feedback campaign digest or schema")
    return report


def _different_paths(left, right):
    a, b = Path(left).resolve(), Path(right).resolve()
    if a == b or (a.exists() and b.exists() and a.samefile(b)):
        raise ValueError("graph corpus and feedback ledger must use different files")


def run_campaign(corpus, ledger, name, **options):
    if type(name) is not str or not name.strip() or len(name) > 128:
        raise ValueError("campaign name must have 1..128 characters")
    config = _configuration(**options)
    _different_paths(corpus, ledger)
    panel, manifest = _panel(corpus, "development", config)
    with closing(_connection(ledger)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS feedback_campaigns (
            name TEXT PRIMARY KEY, report TEXT NOT NULL, sha256 TEXT NOT NULL,
            final_report TEXT, final_sha256 TEXT)""")
        if db.execute("SELECT 1 FROM feedback_campaigns WHERE name=?", (name,)).fetchone():
            prior = _stored(db, name)
            if prior["configuration"] != config:
                raise ValueError("feedback campaign name already has different parameters")
            return _replay(prior, panel, manifest)
        report = _experiment(config, panel, manifest)
        db.execute("INSERT INTO feedback_campaigns(name, report, sha256) VALUES(?, ?, ?)",
                   (name, stable(report), digest(report)))
        return report


def _replay(prior, panel, manifest):
    if manifest != prior["development_panel"]:
        raise ValueError("feedback campaign development panel differs from the recorded snapshot")
    report = _experiment(_configuration(**prior["configuration"]), panel, manifest, replay=prior)
    if stable(report) != stable(prior):
        raise ValueError("feedback campaign differs from deterministic replay")
    return report


def audit_campaign(corpus, ledger, name):
    _different_paths(corpus, ledger)
    if not Path(ledger).is_file():
        raise ValueError("missing graph feedback ledger")
    with closing(_connection(ledger)) as db:
        prior = _stored(db, name)
    panel, manifest = _panel(corpus, "development", prior["configuration"])
    return _replay(prior, panel, manifest)


def evaluate_final(corpus, ledger, name):
    _different_paths(corpus, ledger)
    if not Path(ledger).is_file():
        raise ValueError("missing graph feedback ledger")
    with closing(_connection(ledger)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        prior = _stored(db, name)
        config = prior["configuration"]
        commitment = config["final_sha256"]
        if commitment is None:
            raise ValueError("campaign has no precommitted final corpus hash")
        if Path(str(Path(corpus).resolve()) + "-wal").exists() or file_digest(corpus) != commitment:
            raise ValueError("final corpus must be a checkpointed file matching the sealed commitment")
        panel, manifest = _panel(corpus, "final", config)
        if set(manifest["families"]) & set(prior["development_panel"]["families"]):
            raise ValueError("a final family is also registered in the development corpus")
        trials = []
        for statement in prior["frozen_candidates"]:
            claim = AffineRelation.from_dict(statement)
            result = _screen(panel, claim, config, "final")
            if result["witness"]:
                replay_witness(claim, result["witness"])
            trials.append({"statement": statement, "screen": result})
        if file_digest(corpus) != commitment or Path(str(Path(corpus).resolve()) + "-wal").exists():
            raise ValueError("final corpus changed during evaluation")
        report = {"schema": FINAL_SCHEMA, "campaign_sha256": digest(prior), "sealed_file_sha256": commitment,
                  "frozen_candidates_sha256": prior["frozen_candidates_sha256"], "final_panel": manifest,
                  "trials": trials}
        previous = db.execute("SELECT final_report, final_sha256 FROM feedback_campaigns WHERE name=?",
                              (name,)).fetchone()
        if previous != (None, None):
            if previous != (stable(report), digest(report)):
                raise ValueError("final report differs from deterministic replay")
        else:
            db.execute("UPDATE feedback_campaigns SET final_report=?, final_sha256=? WHERE name=?",
                       (stable(report), digest(report), name))
        return report
