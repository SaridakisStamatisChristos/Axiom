"""Transactional canonical graph6 ingestion and batched exact graph features."""
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
from itertools import combinations, islice
import json
from pathlib import Path
import sqlite3
import subprocess

from .graph_affine import applicable
from .graph_claims import digest, stable
from .graph_explicit import ExplicitGraph, parse_graph6
from .graph_invariants import bipartite
from .graph_large_witness import MAX_EXACT_ORDER, _violation, certify_witness, exact_properties

SCHEMA = "axiom.graph.corpus.v1"
FEATURES = ("n", "edges", "maximum_degree", "triangles", "components")
EXPENSIVE = ("clique", "chromatic", "independence", "matching")
BATCH = 2048


def file_digest(path):
    with Path(path).open("rb") as stream:
        value = sha256()
        for chunk in iter(lambda: stream.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


def cheap_features(lines):
    import numpy as np

    cohorts = defaultdict(list)
    for i, line in enumerate(lines):
        n, values = parse_graph6(line)
        cohorts[n].append((i, values))
    output = [None] * len(lines)
    for n, rows in cohorts.items():
        if n > 24:
            for i, _ in rows:
                output[i] = (n, None, None, None, None)
            continue
        if n < 2:
            for i, _ in rows:
                output[i] = (n, 0, 0, 0, n)
            continue
        positions = [(a, b) for b in range(n) for a in range(b)]
        sextets = np.asarray([packed for _, packed in rows], dtype=np.uint8)
        bits = ((sextets[:, :, None] >> np.arange(5, -1, -1)) & 1)
        bits = bits.reshape(len(rows), -1)[:, :len(positions)].astype(bool)
        adj = np.zeros((len(rows), n, n), dtype=bool)
        for column, (a, b) in enumerate(positions):
            adj[:, a, b] = adj[:, b, a] = bits[:, column]
        edges = bits.sum(axis=1)
        degree = adj.sum(axis=2).max(axis=1)
        triangles = np.zeros(len(rows), dtype=np.int64)
        for a, b, c in combinations(range(n), 3):
            triangles += adj[:, a, b] & adj[:, b, c] & adj[:, a, c]
        reach = adj.copy()
        for k in range(n):
            reach |= reach[:, :, k, None] & reach[:, None, k, :]
        components = sum(~reach[:, v, :v].any(axis=1) for v in range(n))
        for j, (i, _) in enumerate(rows):
            output[i] = (n, int(edges[j]), int(degree[j]), int(triangles[j]), int(components[j]))
    return output


def _initialize(db):
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS graphs (
            id TEXT PRIMARY KEY, graph6 TEXT UNIQUE NOT NULL, split TEXT NOT NULL,
            n INTEGER NOT NULL, edges INTEGER, maximum_degree INTEGER, triangles INTEGER, components INTEGER
        );
        CREATE TABLE IF NOT EXISTS sources (
            family TEXT PRIMARY KEY, manifest TEXT NOT NULL, input_count INTEGER NOT NULL,
            ordered_sha256 TEXT NOT NULL, sampled_checks INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS provenance (
            family TEXT NOT NULL REFERENCES sources(family), id TEXT NOT NULL REFERENCES graphs(id),
            PRIMARY KEY (family, id)
        );
    """)


def _input_lines(stream):
    for line in stream:
        line = line.rstrip("\r\n").removeprefix(">>graph6<<")
        if line:
            yield line


def _canonicalize(block, labelg):
    run = subprocess.run([str(labelg), "-q", "-g"], input="\n".join(block) + "\n",
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         check=True, timeout=60)
    canonical = run.stdout.splitlines()
    if len(canonical) != len(block):
        raise ValueError("labeller changed the graph count")
    return canonical


def _check_isomorphic(raw, canonical):
    import networkx as nx

    a, b = (ExplicitGraph.from_graph6(line) for line in (raw, canonical))
    g, h = nx.empty_graph(a.n), nx.empty_graph(b.n)
    g.add_edges_from(a.edges)
    h.add_edges_from(b.edges)
    if not nx.is_isomorphic(g, h):
        raise ValueError("canonical output failed independent isomorphism check")


def ingest(database, path, labelg, *, family, origin, split="development", seed=None, parameters=None):
    if split not in ("development", "validation", "final") or not family or not origin:
        raise ValueError("invalid source provenance")
    labelg = Path(labelg).resolve()
    manifest = {"schema": SCHEMA, "feature_schema": "axiom.graph.corpus_features.v1",
                "family": family, "origin": origin, "split": split, "seed": seed,
                "parameters": parameters or {}, "source_sha256": file_digest(path),
                "labeller_sha256": file_digest(labelg)}
    with closing(sqlite3.connect(database, timeout=600)) as db, db, Path(path).open(encoding="ascii") as source:
        _initialize(db)
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('labeller', ?)", (manifest["labeller_sha256"],))
        if db.execute("SELECT value FROM metadata WHERE key='labeller'").fetchone()[0] != manifest["labeller_sha256"]:
            raise ValueError("canonical labeller differs from the corpus pin")
        old = db.execute("SELECT manifest FROM sources WHERE family=?", (family,)).fetchone()
        if old is not None:
            if old[0] != stable(manifest):
                raise ValueError("family already identifies a different source")
            return
        db.execute("INSERT INTO sources VALUES (?,?,0,'',0)", (family, stable(manifest)))
        mixed = db.execute("SELECT 1 FROM graphs WHERE split<>? LIMIT 1", (split,)).fetchone()
        lines = _input_lines(source)
        content_hash = sha256()
        count = sampled = 0
        while block := list(islice(lines, BATCH)):
            for line in block:
                parse_graph6(line)
            canonical = _canonicalize(block, labelg)
            for i, (raw, result) in enumerate(zip(block, canonical, strict=True)):
                if (count + i) % 4096 == 0:
                    _check_isomorphic(raw, result)
                    sampled += 1
            records = []
            for line, feature in zip(canonical, cheap_features(canonical), strict=True):
                encoded = line.encode("ascii")
                content_hash.update(encoded + b"\n")
                records.append((sha256(encoded).hexdigest(), line, split, *feature))
            db.executemany("INSERT OR IGNORE INTO graphs VALUES (?,?,?,?,?,?,?,?)", records)
            db.executemany("INSERT OR IGNORE INTO provenance VALUES (?,?)",
                           ((family, record[0]) for record in records))
            if mixed and db.execute(
                "SELECT 1 FROM provenance p JOIN graphs g ON p.id=g.id WHERE p.family=? AND g.split<>? LIMIT 1",
                (family, split),
            ).fetchone():
                raise ValueError("an isomorphic graph already belongs to another split")
            count += len(block)
        if file_digest(path) != manifest["source_sha256"]:
            raise ValueError("graph source changed during ingestion")
        db.execute("UPDATE sources SET input_count=?, ordered_sha256=?, sampled_checks=? WHERE family=?",
                   (count, content_hash.hexdigest(), sampled, family))


def summarize(database, split="development"):
    columns = ", ".join(f"COUNT({name})" for name in FEATURES)
    with closing(sqlite3.connect(database)) as db:
        coverage = {n: {**dict(zip(FEATURES, counts)), **dict.fromkeys(EXPENSIVE, 0)}
                    for n, *counts in db.execute(
                        f"SELECT n, {columns} FROM graphs WHERE split=? GROUP BY n ORDER BY n", (split,))}
        sources = {}
        for family, metadata, n, sha, checked in db.execute("SELECT * FROM sources ORDER BY family"):
            manifest = json.loads(metadata)
            if manifest["split"] == split:
                total = db.execute("SELECT COUNT(*) FROM provenance WHERE family=?", (family,)).fetchone()[0]
                sources[family] = {"manifest": manifest, "manifest_sha256": digest(manifest),
                                   "input_count": n, "unique_graph_count": total,
                                   "graph6_sha256": sha, "sampled_isomorphisms": checked}
        hasher = sha256()
        for (identity,) in db.execute("SELECT id FROM graphs WHERE split=? ORDER BY id", (split,)):
            hasher.update(bytes.fromhex(identity))
        return {"schema": SCHEMA, "split": split, "sources": sources, "feature_coverage_by_order": coverage,
                "unique_graph_count": sum(row["n"] for row in coverage.values()),
                "corpus_sha256": hasher.hexdigest()}


def screen(database, claim, exact_budget, *, split="development"):
    """Evaluate cheap rows first, and explicitly count expensive or unsupported rows."""
    if type(exact_budget) is not int or exact_budget < 0:
        raise ValueError("expected a nonnegative exact graph budget")
    needed = {name for name, _ in claim.bound.terms}
    counts = defaultdict(Counter)
    exhausted = 0
    witness = None
    with closing(sqlite3.connect(database)) as db:
        rows = db.execute("""
            WITH probes AS (SELECT DISTINCT id FROM provenance WHERE family LIKE 'structured-%')
            SELECT g.id, g.graph6, g.n, g.edges, g.maximum_degree, g.triangles, g.components
            FROM graphs g LEFT JOIN probes p ON p.id=g.id
            WHERE g.split=? ORDER BY p.id IS NULL, g.id
            """, (split,))
        for identity, line, *values in rows:
            n, _, _, triangles, components = values
            counts[n]["visited"] += 1
            props = dict(zip(FEATURES, values))
            if None in values:
                counts[n]["missing_features"] += 1
                continue
            graph = None
            props.update(connected=components == 1, triangle_free=triangles == 0)
            if claim.bound.assumption == "BIPARTITE":
                graph = ExplicitGraph.from_graph6(line)
                props["bipartite"] = bipartite(graph)
            if not applicable(claim.bound.assumption, props):
                counts[n]["outside_premise"] += 1
                continue
            if needed - props.keys():
                if exhausted >= exact_budget or n > MAX_EXACT_ORDER:
                    counts[n]["missing_features"] += 1
                    continue
                graph = graph or ExplicitGraph.from_graph6(line)
                props = exact_properties(graph)
                exhausted += 1
            counts[n]["evaluated"] += 1
            if _violation(claim, props) is not None:
                graph = graph or ExplicitGraph.from_graph6(line)
                if n > MAX_EXACT_ORDER:
                    counts[n]["evaluated"] -= 1
                    counts[n]["missing_features"] += 1
                    continue
                witness = certify_witness(claim, graph, origin=f"canonical corpus graph {identity}")
                break
    return {"schema": "axiom.graph.corpus_screen.v1", "candidate_id": claim.id, "split": split,
            "exact_budget": exact_budget, "exact_graphs": exhausted, "coverage_by_order": dict(counts),
            "status": "REFUTED" if witness else "NO_REFUTATION_OBSERVED", "witness": witness}
