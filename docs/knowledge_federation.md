# AXIOM v0.7 — Cross-domain mathematical evidence federation

## Scope and epistemology

Version 0.7 extends the existing v0.6 SQLite knowledge database with a typed federation of four distinct domains. Original v0.6 graph nodes, edges, and historical evidence remain unchanged.

| Domain | Source schema | Auditor | Boundaries |
| --- | --- | --- | --- |
| Fixed-order finite graphs | axiom.graph.campaign.v1 | graph_campaign.audit_graph_report | Exact order n<=5 finite proofs |
| Polynomial algebra | axiom.v0.2.report | evidence.audit_report | Supported integer-polynomial fragment |
| Elementary number theory | axiom.number_theory.report.v1 | number_theory_campaign.audit_nt_report | Supported divisibility/congruence fragment |
| Modular recurrences | axiom.recurrence.campaign.v1 | recurrences.audit_sequence_campaign | Eventual periodicity of residue pairs |

No theorem is inferred from a similar-looking statement, a different graph order, or an independent mathematical domain. Cross-domain statement identity includes the domain and the original typed syntax.

**Historical Lean results are preserved separately and are not imported or promoted to FORMALLY_VERIFIED by this initial federation.** Genuine kernel results for algebra/number theory remain documented in previous releases; local source report statuses are not overwritten by this index. No mathematical novelty is asserted.

## Reproduce on Linux Mint / Ubuntu (Python 3.11+)

Install AXIOM using the main README, then in the project root run:

    axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom knowledge-federate --db research/knowledge/axiom.sqlite3 \
      research/v03_campaign_report.json \
      research/number_theory/v04_report.json \
      research/number_theory/v04_sequences.json

    axiom knowledge-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-federation-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-cross-query --db research/knowledge/axiom.sqlite3 \
      --domain number_theory --status PROVED_IN_SUPPORTED_FRAGMENT
    axiom knowledge-cross-query --db research/knowledge/axiom.sqlite3 \
      --domain recurrence --limit 40

The original knowledge-audit verifies the v0.6 finite-graph knowledge graph. The new knowledge-federation-audit verifies the original graph and replays every domain-specific source report, reconstructing all additional nodes and edges.

## Entity and relationship model

The new federation_sources, federation_nodes, and federation_edges tables retain complete normalized report JSON and deterministic content-addressed entities. Typed entities include source, domain, original statement, finding, search, counterexample, local proof certificate, and domain-specific checker.

Relationships: BELONGS_TO_DOMAIN, RECORDED_IN, INVESTIGATES, SEARCH_EVIDENCE, REFUTED_BY, LOCALLY_CERTIFIED_BY, DEPENDS_ON_PYTHON_CHECKER, and OBSERVATION_ONLY. Recurrence statements bind the exact specification, preperiod, and period. Each link records original source evidence rather than a conjectured logical implication.

The finder never emits a FORMALLY_VERIFIED finding. The statement's original report evidence status is retained. Duplicate statements merge only when their complete domain-qualified typed representation is exactly identical.

## Integrity and trust boundaries

- Import requires complete campaigns and domain-specific independent replay before mutation.
- Source campaigns are immutable; a changed snapshot sharing an identity is rejected.
- Full audit verifies SQLite and all original graph records, then compares regenerated federated nodes and edges against persisted values.
- Missing, altered, or injected links fail closed. Removing all derived nodes is treated as corruption, not silently repaired.
- Import is transactional, preserving previous v0.6 tables and every historical record.
- Python reference checkers and typed claim semantics remain within the trusted computing base.
- Offline report integrity is not external attestation of historical Lean execution.

Run pytest -q tests/test_knowledge_federation.py and pytest -q to verify all regression suites. The GitHub Actions workflow knowledge-federation.yml imports the preserved graph baseline/scale, historical algebra, number-theory, and recurrence reports and archives the checked SQLite output on Python 3.11/3.13.

## Next research milestone

v0.8 should introduce **source-bound Lean proof links** only when record integrity, originating certificate equality, kernel version/axiom checks, and independent external CI evidence have all been established. It must never infer Lean success from the Python proof status alone.
