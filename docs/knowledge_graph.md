# AXIOM v0.6 — Cumulative Mathematical Knowledge Graph

## Scope and epistemic boundary

The knowledge graph is an **audited, cumulative index** over preserved **complete AXIOM v0.5 finite-simple-graph campaign reports**. It does not reclassify mathematical evidence. Imported reports are independently replayed with the existing audit_graph_report verifier. A finite proof for n<=5 applies **only to exactly n vertices**, not all graph orders. Graph claims have **zero Lean 4 kernel verifications**, and originality is **not assessed**.

The schema is axiom.knowledge_graph.v1; the initial source adapter supports axiom.graph.campaign.v1. Older v0.1–v0.4 mathematical evidence remains untouched. A future domain-specific adapter must preserve original proof-checking and provenance semantics rather than coercing these results into graph claims.

## Reproduce

Install Python 3.11+ and AXIOM as in README. From the repository root:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'
    pytest -q

    axiom knowledge-build \
      --db research/knowledge/axiom.sqlite3 \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom knowledge-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-query --db research/knowledge/axiom.sqlite3 --template handshake --order 5
    axiom knowledge-query --db research/knowledge/axiom.sqlite3 --status REFUTED --limit 15

Query results include stable statement IDs. Inspect the direct evidence links with:

    axiom knowledge-neighbors 'statement:ID_FROM_QUERY' --db research/knowledge/axiom.sqlite3

The CLI prints JSON. Importing the same report again is logically idempotent. Full normalized source JSON is stored inside the database to permit offline re-audit. Importing a different snapshot under an existing campaign ID is rejected. Partial reports are rejected.

## Typed entity graph

| Node | Meaning |
| --- | --- |
| campaign | Full campaign identity and original source-report digest |
| statement | A typed exact-order graph proposition; each graph order is distinct |
| finding | A candidate's campaign-specific classification and history |
| search | Bounded or exhaustive search evidence; never by itself a proof |
| finite_proof | An exact-order proof certificate |
| counterexample | Independently checked falsifying graph witness |
| checker | Trusted Python reference checker and its precise limitations |
| template_family | Same template and integer parameter across graph orders |

Typed relationships: INVESTIGATES, RECORDED_IN, SEARCH_EVIDENCE, REFUTED_BY, SUPPORTED_BY_FINITE_PROOF, EXPERIMENTALLY_TESTED_BY, INSTANCE_OF, DEPENDS_ON_CHECKER.

NEXT_ORDER_ANALOGUE connects consecutive **observed orders** sharing a predicate template and parameter, strictly for navigation. Edge metadata explicitly records logical_implication=false and universal_generalization=false. A higher-order analogue does not inherit the proof status of any lower-order statement.

A finite proof depends on the checker implementation, not on inferred mathematical premises. The importer does not invent proof-to-proof dependencies where the original certificate contains none.

## Integrity and trust boundary

- Every complete source report is deterministically replayed, including its original proof certificates and counterexamples, before import.
- Identifiers derive from canonical SHA-256 JSON digests, not string similarity.
- SQLite retains a normalized copy of each complete report, with digest-linked provenance.
- The knowledge audit rematerializes all nodes and edges from the reports, comparing exact canonical JSON values to persisted records.
- SQLite integrity and foreign-key checks are required; extra, missing, or corrupted relationships fail closed.
- Imports are transactional; an existing corrupted database will not be silently repaired.
- Original discovery evidence states are unchanged; search without a counterexample does not establish mathematical truth.
- Python independent invariants and the shared typed claim interpreter form a trusted computing base. This is **not** Lean formal verification or a research originality assessment.
- No cloud services, paid AI APIs, or GPUs are necessary.

## Verification and limitations

Run pytest -q tests/test_knowledge_graph.py for coverage of multi-campaign imports, idempotency, evidence scope, conflicting reports, tampering and CLI behavior.

The workflow .github/workflows/knowledge-graph.yml imports the actual preserved v0.5 baseline and scale reports, audits the materialized graph and runs tests on Python 3.11 and 3.13. Passing CI supports these bounded engineering checks, not a claim of novel theorems.

This v0.6 adapter only supports graph-domain reports. Extension to the earlier algebraic and number-theory proof records requires preserving distinct Lean evidence roots and an explicit dependency DAG, rather than assuming equivalent proof statuses.

## Subsequent development

- Type-safe ingestion of the earlier polynomial, recurrence and number-theory domains.
- Actual lemma-to-lemma proof dependencies with verified edges, cycle detection and trust closure.
- Evidence-grounded cross-domain theorem search and semantic equivalence.
- Knowledge-guided conjecture generation while explicitly preserving experiment-versus-proof separation.
