# AXIOM v0.15 — Full research-cycle dispatcher

The graph-to-Lean bridge already verifies three true exact-six-vertex
templates in the actual pinned Lean 4 kernel. AXIOM additionally offers
a reproducible **research cycle** combining formal proof attempts with
independent bounded falsification of unresolved exact-order-seven claims.

This is NOT automatic theorem discovery across arbitrary mathematics.

## Execution

After populating the fully source-replayed v0.14 knowledge database
(as documented in docs/reconciled_graph_agenda.md and docs/graph_lean_v015.md):

    axiom graph-research-cycle --db research/knowledge/axiom.sqlite3 \
      --project-root . --output-dir research/research_cycles \
      --proof-quota 3 --experiment-quota 2 --search-budget 64 \
      --seed 42 --timeout 240

Each run is written in a source- and configuration-addressed subdirectory:

    research/research_cycles/runs/<run_id>/

The run contains formal/summary.json, individual real Lean evidence JSON
files, bounded/<task-hash>.json files and a summary.json hash-chain ledger.
The program refuses to replace incomplete runs; rerunning an existing
complete run first performs an independent source/evidence replay and
returns the audited report without rewriting the records.

For example, to recheck one archived run:

    axiom graph-research-cycle-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/research_cycles/runs/<run_id>

## Selection and verification

The selector replays the complete original v0.14 plan at n=6 and n=7.
It dispatches up to the requested proof quota to the existing exact-n6
Lean kernel executor; unsupported proof templates remain pending. It also
picks the highest-priority outstanding n7 falsification tasks and submits
deterministic, nonrepeating edge masks to the independently implemented
graph reference oracle. Genuine counterexamples are checked again with
the original independent witness checker. Surviving sampled claims are
labelled SURVIVED_BOUNDED_SEARCH, *never* PROVED or FORMALLY_VERIFIED.

The samples are unique within the new run, but may overlap with historical
search campaigns. The sample budget is at most 256 per task. No all-order
claim is inferred from either exact n6 proofs or bounded n7 searches.
An offline source audit is NOT external execution attestation: check CI
job logs or rerun the actual Lean kernel.

All v0.1-v0.14 reports, databases and evidence statuses remain unchanged.
