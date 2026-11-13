"""AXIOM v0.12: genuinely exhaustive, independently replayed exact-n=6 graph proofs.

There are C(6,2)=15 possible unordered vertex pairs, hence exactly 2^15
labelled simple graphs. Every accepted certificate quantifies ONLY over
the 32,768 graphs with exactly six labelled vertices. This is not an all-n
theorem or a Lean proof.

Two different graph invariant implementations are used: the discovery
engine calls the original domain algorithms, and the independent checker
uses bitset adjacency/BFS/counting with no calls to that engine.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .graph_claims import GraphStatement, digest, stable, holds
from .graph_model import SimpleGraph, edge_positions
from .graph_checker import check_graph_witness

SCHEMA = "axiom.graph.n6.exhaustive_campaign.v1"
CERT_SCHEMA = "axiom.graph.n6.exact_certificate.v1"
N = 6
LABELED_GRAPHS = 1 << 15
SUPPORTED_TEMPLATES = (
    "handshake", "degree_bound", "triangle_upper_bound",
    "forest_edge_count", "tree_edge_count",
    "connected_edge_lower_bound", "bipartite_no_triangles",
    "edges_le_vertices", "connected_edges_ge_n",
)
DEFAULT_TEMPLATES = SUPPORTED_TEMPLATES[:7]
PROOF_SCOPE = "ALL labelled simple graphs with exactly n=6 vertices"
FORMAL_STATUS = "NOT_PERFORMED"


def _statement(template: str) -> GraphStatement:
    if type(template) is not str or template not in SUPPORTED_TEMPLATES:
        raise ValueError("unsupported exact-n6 structural claim template")
    return GraphStatement(N, template)


def _facts_discovery(mask: int) -> dict:
    """Use the original *discovery* structural graph algorithms."""
    from .graph_invariants import components, forest, bipartite, triangles
    graph = SimpleGraph.from_mask(N, mask)
    component_count = len(components(graph))
    connected = component_count == 1
    acyclic = forest(graph)
    return {
        "n": N, "edges": len(graph.edges),
        "degree_sum": sum(graph.degrees),
        "maximum_degree": max(graph.degrees),
        "components": component_count,
        "connected": connected, "forest": acyclic,
        "tree": connected and acyclic,
        "bipartite": bipartite(graph),
        "triangles": triangles(graph),
    }


def _facts_reference(mask: int) -> dict:
    """Independent structural bitset implementation; NO discovery oracle calls."""
    if type(mask) is not int or not 0 <= mask < LABELED_GRAPHS:
        raise ValueError("graph mask outside exact-six-vertex domain")
    adjacent = [0] * N
    degrees = [0] * N
    for i, (u, v) in enumerate(edge_positions(N)):
        if mask & (1 << i):
            adjacent[u] |= 1 << v
            adjacent[v] |= 1 << u
            degrees[u] += 1
            degrees[v] += 1
    edges = mask.bit_count()
    seen = 0
    component_count = 0
    for start in range(N):
        if seen & (1 << start):
            continue
        component_count += 1
        pending = [start]
        seen |= 1 << start
        while pending:
            vertex = pending.pop()
            unseen = adjacent[vertex] & ~seen
            while unseen:
                bit = unseen & -unseen
                unseen ^= bit
                seen |= bit
                pending.append(bit.bit_length() - 1)
    coloring = [-1] * N
    bipartite = True
    for start in range(N):
        if coloring[start] != -1:
            continue
        coloring[start] = 0
        pending = [start]
        while pending:
            vertex = pending.pop()
            unseen = adjacent[vertex]
            while unseen:
                bit = unseen & -unseen
                unseen ^= bit
                neighbor = bit.bit_length() - 1
                if coloring[neighbor] == -1:
                    coloring[neighbor] = 1 - coloring[vertex]
                    pending.append(neighbor)
                elif coloring[neighbor] == coloring[vertex]:
                    bipartite = False
    triangles = 0
    for a in range(N):
        for b in range(a + 1, N):
            if adjacent[a] & (1 << b):
                triangles += (adjacent[a] & adjacent[b] &
                              ~((1 << (b + 1)) - 1)).bit_count()
    # Independently recognize acyclicity by an undirected DFS with
    # parent tracking. NEVER define "forest" using |E| = n-components
    # here: that is the very claim the finite certificate must test.
    visited = [False] * N

    def cycle_found(u: int, parent: int) -> bool:
        visited[u] = True
        neighbors = adjacent[u]
        while neighbors:
            bit = neighbors & -neighbors
            neighbors ^= bit
            v = bit.bit_length() - 1
            if not visited[v]:
                if cycle_found(v, u):
                    return True
            elif v != parent:
                return True
        return False

    forest = True
    for root in range(N):
        if not visited[root] and cycle_found(root, -1):
            forest = False
            break
    connected = component_count == 1
    return {
        "n": N, "edges": edges,
        "degree_sum": sum(degrees), "maximum_degree": max(degrees),
        "components": component_count, "connected": connected,
        "forest": forest, "tree": connected and forest,
        "bipartite": bipartite, "triangles": triangles,
    }


def _scan(statement: GraphStatement, oracle) -> tuple[int, int | None]:
    """Enumerate EVERY one of the 2^15 masks, even after counterexample discovery."""
    if statement.n != N:
        raise ValueError("six-vertex checker cannot infer other graph orders")
    assumption_count = 0
    first_counterexample = None
    for mask in range(LABELED_GRAPHS):
        applicable, valid = holds(statement, oracle(mask))
        if applicable:
            assumption_count += 1
            if not valid and first_counterexample is None:
                first_counterexample = mask
    return assumption_count, first_counterexample


def check_n6_certificate(statement_data: dict, certificate: dict) -> bool:
    """Independently enumerate all labelled n=6 graphs and reject false claims."""
    statement = GraphStatement.from_dict(statement_data)
    _statement(statement.template)
    if statement.n != N or statement.k != 0:
        raise ValueError("certificate is restricted to exact n=6, k=0")
    if type(certificate) is not dict or set(certificate) != {
        "schema", "method", "statement_sha256", "order",
        "labelled_graphs_checked", "assumption_satisfying",
        "vacuous", "proof_scope", "formal_lean_verification"}:
        raise ValueError("invalid n6 finite certificate shape")
    if (certificate["schema"] != CERT_SCHEMA or
            certificate["method"] != "exhaustive_all_labelled_simple_graphs" or
            certificate["statement_sha256"] != digest(statement.to_dict()) or
            type(certificate["order"]) is not int or
            certificate["order"] != N or
            type(certificate["labelled_graphs_checked"]) is not int or
            certificate["labelled_graphs_checked"] != LABELED_GRAPHS or
            certificate["proof_scope"] != PROOF_SCOPE or
            certificate["formal_lean_verification"] != FORMAL_STATUS):
        raise ValueError("n6 proof certificate metadata mismatch")
    assumption_count, counterexample = _scan(statement, _facts_reference)
    if counterexample is not None:
        raise ValueError("exact six-vertex theorem is false: independent counterexample")
    if (type(certificate["assumption_satisfying"]) is not int or
            certificate["assumption_satisfying"] != assumption_count or
            type(certificate["vacuous"]) is not bool or
            certificate["vacuous"] != (assumption_count == 0)):
        raise ValueError("n6 certificate full-space coverage mismatch")
    return True


def investigate_n6(template: str) -> dict:
    statement = _statement(template)
    assumption_count, failure_mask = _scan(statement, _facts_discovery)
    evidence = {
        "statement": statement.to_dict(),
        "source_method": "fully_enumerated_primary_discovery_graph_invariants",
        "independent_checker": "axiom.graph_n6_exact.check_n6_certificate",
        "labelled_graphs_checked": LABELED_GRAPHS,
        "assumption_satisfying": assumption_count,
        "status": "REFUTED" if failure_mask is not None else
                  "PROVED_IN_SUPPORTED_FRAGMENT",
        "counterexample": None, "certificate": None,
        "proof_scope": PROOF_SCOPE,
        "all_order_generalization": "NOT_PROVED",
        "lean_formal_verification": FORMAL_STATUS,
        "originality": "NOT_ASSESSED",
    }
    if failure_mask is not None:
        witness = SimpleGraph.from_mask(N, failure_mask).to_dict()
        check_graph_witness(statement.to_dict(), witness)
        evidence["counterexample"] = witness
    else:
        certificate = {
            "schema": CERT_SCHEMA,
            "method": "exhaustive_all_labelled_simple_graphs",
            "statement_sha256": digest(statement.to_dict()),
            "order": N, "labelled_graphs_checked": LABELED_GRAPHS,
            "assumption_satisfying": assumption_count,
            "vacuous": assumption_count == 0,
            "proof_scope": PROOF_SCOPE,
            "formal_lean_verification": FORMAL_STATUS,
        }
        check_n6_certificate(statement.to_dict(), certificate)
        evidence["certificate"] = certificate
    return evidence


def research_n6(templates: list[str] | tuple[str, ...] = DEFAULT_TEMPLATES) -> dict:
    if (type(templates) not in (list, tuple) or not 1 <= len(templates) <=
            len(SUPPORTED_TEMPLATES) or
            any(type(t) is not str or t not in SUPPORTED_TEMPLATES for t in templates) or
            len(set(templates)) != len(templates)):
        raise ValueError("invalid or duplicate exact-order-six templates")
    ordered = sorted(templates)
    findings = [investigate_n6(t) for t in ordered]
    return {
        "schema": SCHEMA,
        "configuration": {"order": N, "templates": ordered},
        "campaign_id": digest([SCHEMA, N, ordered])[:24],
        "labelled_graph_space": LABELED_GRAPHS,
        "complete": True,
        "counts": {
            "PROVED_IN_SUPPORTED_FRAGMENT": sum(
                f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT" for f in findings),
            "REFUTED": sum(f["status"] == "REFUTED" for f in findings),
        },
        "findings": findings,
        "independent_certificate_verification": "PYTHON_EXACT_N6_ONLY",
        "formal_lean_verification": FORMAL_STATUS,
        "all_order_generalization": "NOT_PROVED",
        "originality": "NOT_ASSESSED",
    }


def audit_n6(report: dict) -> dict:
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise ValueError("unknown exact-six-vertex report")
    config = report.get("configuration")
    if type(config) is not dict or set(config) != {"order", "templates"}:
        raise ValueError("malformed exact-n6 research configuration")
    if type(config["order"]) is not int or config["order"] != N:
        raise ValueError("incorrect exhaustive graph order")
    expected = research_n6(config["templates"])
    if stable(expected) != stable(report):
        raise ValueError("n6 research report disagrees with independent exhaustive replay")
    return {
        "schema": SCHEMA,
        "audit": "ACCEPTED",
        "campaign_id": expected["campaign_id"],
        "exact_order": N,
        "labelled_graphs_per_statement": LABELED_GRAPHS,
        "counts": expected["counts"],
        "scope": PROOF_SCOPE,
        "formal_lean_verification": FORMAL_STATUS,
        "originality": "NOT_ASSESSED",
    }


def save_n6(report: dict, output: str) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".axiom-n6-", suffix=".tmp", delete=False) as stream:
            temp = stream.name
            stream.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
        os.replace(temp, path)
    finally:
        if temp is not None and os.path.exists(temp):
            os.unlink(temp)
