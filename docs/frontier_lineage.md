# AXIOM v0.11 — Independent graph-frontier evidence lineage

## Objective and evidence boundary

The v0.9 graph-frontier experiment independently tested new exact-order
graph conjectures at n=6 and n=7, drawing motivation from exhaustive,
nonvacuous original n=5 certificates. The v0.6–v0.8 cumulative knowledge
database previously indexed only the original graph campaigns, algebra,
number theory, recurrences and historical source-bound Lean metadata.

The v0.11 adapter now **imports full bounded experiment reports as an
additional independent SQLite overlay**. It never edits original v0.5
graph reports, historical source data, knowledge-graph nodes/edges,
federation records, or formal Lean provenance.

At exact n=6 or n=7, evidence states are only:

- **REFUTED**: a genuine concrete failing graph, independently checked by
  the original source experiment replay and witness checker.
- **EXPERIMENTALLY_SUPPORTED**: survived a specified bounded sample.
  This NEVER means a complete fixed-n proof, even for finite graph space.

All output explicitly retains proof count 0 at target order, external
Lean execution NOT_PERFORMED and originality NOT_ASSESSED. A source n=5
finite proof is a *motivation* to experiment at n=6/7, not a logical
implication across orders.

## Reproducible local installation

Ubuntu, Linux Mint, Python >= 3.11:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

Build all original source-bound evidence before importing new experiments:

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

Reproduce the actual v0.9 bounded experiments (not an invented
or fake summary):

    axiom graph-frontier-run --target-order 6 --seed 42 \
      --search-budget 256 --max-candidates 40 \
      --output research/graphs/n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-run --target-order 7 --seed 42 \
      --search-budget 256 --max-candidates 40 \
      --output research/graphs/n7.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-audit research/graphs/n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-audit research/graphs/n7.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

Import and inspect:

    axiom knowledge-frontier-import --db research/knowledge/axiom.sqlite3 \
      research/graphs/n6.json research/graphs/n7.json

    axiom knowledge-frontier-audit --db research/knowledge/axiom.sqlite3

    axiom knowledge-frontier-query --db research/knowledge/axiom.sqlite3 \
      --order 6 --status REFUTED

    axiom knowledge-frontier-query --db research/knowledge/axiom.sqlite3 \
      --order 7 --limit 10 --offset 0

## Evidence architecture

A separate overlay uses four tables:

| Table | Evidence |
|---|---|
| \`frontier_reports\` | Immutable canonical full report, campaign ID and SHA-256 |
| \`frontier_statements\` | Content-addressed exact-order graph statement and explicit no-proof scope |
| \`frontier_findings\` | Bounded experiment status, full search/counterexample JSON, report/statement foreign keys |
| \`frontier_motivations\` | Explicit non-entailing links to genuine original n=5 proof findings in the v0.7 federation |

Every import preflights the complete existing overlay before changing
anything. It refuses tampered persisted reports, missing source proof links,
nonexistent source nodes, changed statuses or mismatched original source
campaigns. Valid imports are idempotent; conflicting reuse of an existing
campaign ID is rejected. All source-dependent derived rows are reconstructed
from full independently re-executed reports.

Every full audit first rechecks the original graph knowledge, all supported
mathematical domain source reports, and any archived Lean proof metadata,
then re-executes **every** v0.9 frontier report against the original immutable
graph sources, compares all materialized statements/findings/source
motivations and checks foreign-key integrity.

The database itself remains a local mutable file, not a cryptographically
authenticated remote log: deleting *all* evidence including its source
snapshots is not externally detectable without a separately retained
manifest. Therefore preserve GitHub run logs, source reports and artifacts.

## Tests and CI gates

    pytest -q tests/test_frontier_lineage.py
    pytest -q

The \`.github/workflows/frontier-lineage.yml\` workflow reconstructs
the v0.6–v0.8 knowledge layers, generates independent n6/n7 campaign
reports, imports and audits them, and uploads the SQLite database and JSON
evidence on Python 3.11 and 3.13.

Merge to main only after this workflow and all existing graph,
mathematical knowledge, federation, formal provenance, research agenda and
pinned actual Lean 4 / Mathlib checks pass on the same final commit.

The v0.10 task scheduler does not silently ingest newly imported frontier
observations: integrating original and frontier evidence into prioritization
is a separate next engineering milestone requiring an explicit audited
policy for previously refuted claims and larger search budgets.
