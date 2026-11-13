# AXIOM v0.13 — Exact six-vertex evidence in the cumulative knowledge database

## Goal

Preserve AXIOM v0.12's 32,768-graph **fully enumerated exact n=6
certificate campaign** alongside the v0.6–v0.11 evidence layers without
modifying, overwriting, or silently promoting earlier findings.

The v0.11 frontier stores **bounded sampled** claims at n=6 and n=7,
not complete proofs. The v0.12 campaign has **independently checked finite
certificates** for supported claims at n=6 only. Their evidence status
must stay separate. Originality is not assessed and no Lean kernel
verification is claimed for the exact-n6 certificates.

## Reproduction on Linux (Ubuntu, Linux Mint)

From the repository root:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

Construct and audit the original graph knowledge, federation, Lean metadata
index, and bounded frontier first; commands and exact source paths are in
[frontier lineage](frontier_lineage.md) and
[formal provenance](formal_provenance.md).

Then obtain the complete exact-n6 source report with a real, exhaustive run:

    axiom graph-n6-run \
      --templates handshake degree_bound triangle_upper_bound \
        forest_edge_count tree_edge_count connected_edge_lower_bound \
        bipartite_no_triangles edges_le_vertices connected_edges_ge_n \
      --output research/graphs/n6_exact_report.json

    axiom graph-n6-audit research/graphs/n6_exact_report.json

Import into the existing source-bound SQLite database:

    axiom knowledge-exact-n6-import \
      --db research/knowledge/axiom.sqlite3 \
      research/graphs/n6_exact_report.json

    axiom knowledge-exact-n6-audit \
      --db research/knowledge/axiom.sqlite3

    axiom knowledge-exact-n6-query \
      --db research/knowledge/axiom.sqlite3 \
      --status PROVED_IN_SUPPORTED_FRAGMENT --limit 20

    axiom knowledge-exact-n6-query \
      --db research/knowledge/axiom.sqlite3 \
      --status REFUTED --limit 20 --offset 0

The query displays exact typed source statement, finite-order scope,
complete certificate or original counterexample, source campaign IDs,
and links (if any) to previously bounded v0.11 frontier experiments.

## Four independent persistence tables

- \`exact_n6_reports\`: exact original complete report and canonical SHA-256.
- \`exact_n6_statements\`: content-addressed exact graph-order-six typed claims,
  explicit checker, scope, non-generalization and non-Lean provenance.
- \`exact_n6_findings\`: individual exact finite certificates or counterexamples,
  source campaign and typed statement references.
- \`exact_n6_frontier_links\`: immutable relational links to previously saved
  n6 bounded experiments, with explicit no-edit and no-cross-order-implication.

Foreign-key integrity and complete materialization integrity are checked.
Import is idempotent, content-addressed, and fail-closed on conflicting
campaign IDs, modified proof metadata or incomplete/partial sources.
Every audit replays the original v0.5 graph campaigns, mathematical
federation, historical source-bound Lean records, v0.9 n6/n7 frontier
experiments and entire v0.12 exact-n6 certificate campaign.

A bounded experimental survival may be superseded by an exact counterexample,
but the original experiment itself is never rewritten. If a bounded genuine
counterexample conflicts with a newly claimed exact proof of **the same
typed statement and graph order**, the import is rejected.

These SHA-256 digests provide local consistency but are not external
cryptographic attestations. For long-term provenance, preserve GitHub CI
logs and retained source archives separately.

## Evidence and verification limits

All accepted finite proof claims quantify over **exactly n=6**.
The independently checked labelled search covers 2^15 = 32,768 graphs
per supported statement. This is not a universal all-n theorem, and
these certificates have NOT been verified by the Lean kernel.

An exact n6 refutation does not change evidence for any other graph
order. A proof at n=5 remains distinct from a proof at n=6.
All original historical statuses, including bounded experimental
survival, are preserved in their original source records.

## Test and release gates

    pytest -q tests/test_knowledge_exact_n6.py

The dedicated \`.github/workflows/exact-knowledge.yml\` CI matrix runs
the complete new adversarial test suite under Python 3.11 and 3.13.
It independently reconstructs all prerequisite source reports, real
v0.9 bounded frontier searches at n6/7, a full n6 exhaustive campaign,
the new exact-n6 knowledge overlay, source re-audits and typed queries.
It preserves both the final SQLite database and real JSON reports.

Historical tests remain active in their original workflows. The new
heavy integration module runs in full in its dedicated workflow instead
of being redundantly re-executed in every legacy regression matrix.
No existing Lean tests or genuine Lean kernel checks are removed.

The next step is evidence-priority integration in the v0.10 research
agenda, giving exact-order proofs and counterexamples authority over
bounded survival only for the *identical typed graph statement*.
