# AXIOM v0.12 — Exact six-vertex finite-graph proof engine

## Scientific contribution and exact logical boundary

AXIOM previously had independently checked finite-order graph proofs for
n<=5. The v0.9 frontier research tested n=6/7 claims on at most a bounded
sample of 256 graphs per candidate. Surviving bounded searches are **not proofs**.

Version 0.12 adds a genuinely exhaustive, independently checked finite
proof/refutation engine for a **closed subset of structural graph statements
at exactly n=6**:

- handshake (sum of degrees equals twice the number of edges)
- degree_bound (maximum degree is at most n-1)
- triangle_upper_bound (at most C(n,3) triangles)
- forest_edge_count (a forest has n-components edges)
- tree_edge_count (a tree has n-1 edges)
- connected_edge_lower_bound (a connected graph has at least n-1 edges)
- bipartite_no_triangles (a bipartite graph contains no triangle)

Two deliberately incorrect negative controls are also supported:

- edges_le_vertices (every simple graph has at most n edges)
- connected_edges_ge_n (a connected graph has at least n edges)

These are **known identities and counterexamples**, not original
mathematical discoveries. The exact restriction is crucial: **all
2^C(6,2) = 2^15 = 32,768 labelled simple graphs** are checked for each
statement. No finite certificate is issued for the same claim at n=7,
or for *all* finite graph orders. Even a successful finite proof is a
Python-checked exhaustive result, NOT Lean formally verified.

## Dual-independent computation

For every candidate:

1. The discovery evaluator creates each labelled graph using the original
   \`SimpleGraph\` model and original components/forest/bipartite/triangles
   functions from \`graph_invariants.py\`.
2. A separate independent bitset oracle computes vertex degrees, connected
   components, forest acyclicity via an independent DFS cycle detector,
   bipartiteness and triangles from
   adjacency bitsets; it does **not** import the discovery invariant engine.
3. Both call the same typed declarative \`graph_claims.holds\` statement
   interpreter. That shared interpreter, the enumeration model, and
   Python runtime remain trusted components; this is NOT Lean kernel proof.
4. The certificate checker separately enumerates all 32,768 labelled masks
   from zero to 32767, verifies the conclusion on every graph meeting
   the antecedent and verifies the exact assumption-satisfying count.
5. On failure, no proof certificate is issued. The actual graph witness is
   serialized and validated by the existing independent graph witness
   checker.

The finite proof artifact includes exact typed statement SHA-256,
fixed order 6, exact graph count 32768, antecedent-coverage count,
vacuity flag, explicit proof scope and formal status NOT_PERFORMED.

Only nonvacuous certificates should be considered meaningful results.
The result report preserves all source data, refutations, proof metadata
and explicit zero cross-order inference.

## Linux/Ubuntu reproduction

From the repository root with Python >= 3.11:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

    axiom graph-n6-run --output research/graphs/n6_exact_report.json

    axiom graph-n6-audit research/graphs/n6_exact_report.json

    axiom graph-n6-run --templates handshake degree_bound \
      connected_edges_ge_n --output research/graphs/n6_selected.json

To independently check one saved proof certificate, prepare a JSON object
with exactly two keys: \`statement\` (the typed statement from the report)
and \`certificate\` (the corresponding certificate from the report), then:

    axiom graph-n6-check-certificate research/graphs/one_n6_proof.json

The CLI rejects malformed certificates, invented all-order scope,
wrong order, wrong graph counts, false claims, altered statement hashes,
and changes to original proof-status fields.

The full research report is deterministically generated, contains no
timestamps and is saved atomically. \`graph-n6-audit\` independently
reconstructs the entire report, then demands exact canonical equality.

## Complexity, performance, and reproducibility

For fixed n=6, there are 15 candidate edges and 32,768 labelled graphs.
For each supported statement, both the discovery and certificate
checkers perform a complete loop over these 32,768 graphs.
For general symbolic n, this enumeration would scale as
2^(n(n-1)/2), and the structural-invariant calculations also require
graph-dependent processing. There is no claim of a scalable solution
to general graph isomorphism or arbitrary-order theorem proving.

This is a first **real increase in the exact finite graph proof boundary**
for the explicitly supported structural fragment, not for all 25 graph
templates.

## Tests and CI

    pytest -q tests/test_graph_n6_exact.py

Dedicated \`.github/workflows/exact-graph-n6.yml\` runs a complete
independent test suite under Python 3.11 and 3.13, produces and
independently re-audits the real 7-standard+2-negative-control report,
preserves the JSON artifact and reports full certification counts.

The heavyweight exact-order tests are sharded into the dedicated
workflow; historical graph regression, formal provenance, knowledge
federation and real Lean 4 kernel workflows remain separate and unchanged
in scientific coverage. A later release must verify each required
workflow on the same final pull-request SHA.

## Remaining scientific obligations

- Extend full exact n=6 proof coverage to other graph property templates
  with independently validated oracles; then n=7 would require
  2^21 = 2,097,152 labelled graphs per statement.
- Integrate exact-n6 certificates into the cumulative knowledge graph
  with the same immutable source-bound provenance and status labels.
- Explore a trusted formalization of finite simple graphs and its
  certificate checker inside Lean, with explicit source translation.
- Assess novelty only with a separate prior-art research process.
