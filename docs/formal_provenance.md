# AXIOM v0.8 — Source-bound Lean proof provenance

## Objective

Create a **complete, independently auditable lineage index** connecting the
historical AXIOM v0.3 and v0.4 Lean proof records to their exact originating
mathematical statements, independently checked local certificates, campaign
sources, and typed v0.7 knowledge-graph identities.

This phase is NOT a new Lean theorem checker and DOES NOT conclude that
historical Lean execution occurred merely because saved JSON says so.
Successful external Lean CI runs and pinned toolchains remain separate historical
execution evidence. In v0.8 the database records are explicitly labelled
\`SOURCE_BOUND_OFFLINE_ONLY\`.

The original v0.1–v0.7 research, reports, proofs, archives and SQLite graph
tables are never overwritten or removed.

## Source formats

- **Algebra (v0.3):** \`research/v03_campaign_report.json\` and
  \`research/v03_formal_results.ndjson\`, containing original typed statements,
  independently checked local certificates, full Lean source, originating
  campaign and candidate IDs, checker exit evidence and axiom report.
- **Number theory (v0.4):** \`research/number_theory/v04_report.json\`,
  \`research/number_theory/v04_formal_results.ndjson\` (source-bound index)
  and each full JSON record under \`research/lean_verified/number_theory/\`.
- **Graph theory:** finite proofs of EXACT fixed order n<=5 only; no
  Lean proofs imported.
- **Recurrences:** independent finite-state certificates only; no
  Lean proofs imported.

Only historical full records with status \`FORMALLY_VERIFIED\`, accepted flag true,
and matching full source/certificate binding are indexed. That means a historical
record *declares* Lean verified it and passes offline consistency checks; it
does not elevate the associated knowledge-graph finding beyond the original
local \`PROVED_IN_SUPPORTED_FRAGMENT\` classification.

## Run on Ubuntu / Linux Mint

From the repository root with Python 3.11+:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

    axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom knowledge-federate --db research/knowledge/axiom.sqlite3 \
      research/v03_campaign_report.json \
      research/number_theory/v04_report.json \
      research/number_theory/v04_sequences.json

    axiom knowledge-formal-import --db research/knowledge/axiom.sqlite3 \
      --algebra-ndjson research/v03_formal_results.ndjson \
      --number-index research/number_theory/v04_formal_results.ndjson \
      --number-records-dir research/lean_verified/number_theory

    axiom knowledge-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-federation-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-formal-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-formal-query --db research/knowledge/axiom.sqlite3 \
      --domain algebra --limit 2
    axiom knowledge-formal-query --db research/knowledge/axiom.sqlite3 \
      --domain number_theory --limit 2

The importer accepts algebra-only or number-theory-only records if their
exact originating v0.7 campaign is already present. Repeated imports are
idempotent when the saved canonical source records are unchanged. A conflicting
snapshot of the same source is rejected.

## Evidence model

The original v0.7 federation remains the primary source of mathematical truth
states. New tables store:

- \`formal_batches\`: immutable, canonical full historical evidence records
  with SHA-256 digests and foreign keys to the exact federated source campaign.
- \`formal_links\`: deterministic, content-addressed references to the
  original federation's finding, typed statement, and local certificate;
  source SHA-256, record digest, and verifiable checker metadata.

The importer reconstructs each link from the fully re-audited original report
and the complete archived Lean record, using
\`lean_backend.verify_record_integrity\` or
\`number_theory_lean.verify_nt_record_integrity\` as appropriate.
Number-theory summary rows are cross-checked against their full JSON records,
including original candidate ordinal, template, source SHA, theorem, permitted
axioms, Lean version and resolved Mathlib revision.

The full auditor rebuilds **all** formal links and replays the **entire**
v0.6/v0.7 knowledge chain first. Altering a stored record, proof source,
certificate, campaign ID, counterexample, relation target, digest or evidence
status fails closed. SQLite foreign-key checks reject orphan references.

## Historical CI and limits

Previous genuine Lean execution is documented in the original GitHub Actions
runs, but a detached local JSON result is not cryptographic proof of such an
execution. The v0.8 index deliberately reports:

- \`offline_record_integrity = ACCEPTED\`
- \`declared_kernel_status = FORMALLY_VERIFIED\`
- \`external_execution_attestation = NOT_ESTABLISHED_BY_OFFLINE_AUDIT\`
- \`knowledge_graph_status_upgrades = 0\`

A current run of \`lean-verification.yml\` independently repeats the legacy
85/85 algebra and 96/96 number-theory Lean checks, verifies transitive axiom
audits, and attaches executable GitHub CI logs. Those execution records are
separate evidence from the offline proof lineage index, not silently merged into
it. In particular, the AST-to-Lean statement translation remains a trust
boundary; passing Lean proves the *formalized statement*, and interpreting that
as the intended mathematical claim relies on the source translation.

The user-facing query presents full provenance **without asserting external
execution**. Authenticating historical GitHub provenance into a formally signed,
cross-platform proof certificate is a separate future milestone.

## Tests and release gates

Run:

    pytest -q tests/test_formal_provenance.py
    pytest -q

The workflow \`.github/workflows/formal-provenance.yml\` checks the preserved
historical source files on Python 3.11 and 3.13 and archives the generated
SQLite index and audit summary. The existing graph, federation and Lean
workflows must all succeed on the v0.8 pull request before merging.

For a secure research release, evidence statuses must never exceed the
strongest verified supporting artifact. No mathematical originality is claimed.
