# AXIOM v0.14 — Reconciled graph research agenda

## Scientific purpose

AXIOM now has three *distinct* evidence sources for finite simple graphs:

- **Original n<=5 finite proofs** and n6/n7 bounded searches in historical
  v0.5 campaigns, replayed in the v0.6/v0.7 knowledge database.
- **v0.9 bounded n6/n7 frontier research**, with immutable original
  counterexamples and sampled survivals indexed in v0.11.
- **v0.12 exact n6 exhaustive finite certificates** (all 32,768 labelled
  six-vertex simple graphs), indexed and independently checked in v0.13.

Version 0.14 connects these sources to an **evidence-reconciled research
scheduler**, without changing any historical source report, statement, proof
certificate, counterexample, database field, or existing v0.10 multi-domain
agenda. The planner is deterministic and provides action *proposals*, not
automatic research execution or newly proved theorems.

## Exact-typed statement identity

All three layers are normalized against the entire closed
\`GraphStatement\` type, including template, graph order \`n\`, and integer
parameter \`k\`. An n=5 proof does not prove n=6; a verified exact-n6
certificate does not prove n=7. Bounded n6 observations never count as
complete n6 proofs.

Actions are ranked deterministically:

| Evidence for the identical typed fixed-order graph claim | Next action | Priority |
|---|---|---|
| At least one independently verified refutation | Exclude from further research agenda | — |
| Experiment survived bounded v0.9 search, no valid exact proof or refutation | EXTEND_BOUNDED_FALSIFICATION | 1 |
| Only v0.5 experimental search/no certificate | FALSIFY_WITH_INDEPENDENT_SEARCH | 2 |
| Exact n=6 nonvacuous exhaustive certificate, no counterexample | FORMALIZE_EXACT_N6_IN_LEAN | 3 |
| Existing n<=5 finite certificate | FORMALIZE_LOCAL_FINITE_PROOF_IN_LEAN | 4 |

For a claim previously marked experimental at n=6 but now accompanied by
a verified exact n=6 proof, the *new task* becomes Lean formalization,
not repeating bounded counterexample search. All original experimental
records remain unchanged.

For a claim with an independent verified counterexample in **any** of
the three replayed source layers, the task is excluded. A contradiction
between a full certificate and a genuine counterexample on the same
typed statement causes an explicit error instead of selecting whichever
status is more convenient.

Evidence provenance per task includes original campaign identifiers,
typed finding IDs, a source certificate fingerprint, coverage from the
existing search records, and **the exact graph order**. No task claims
originality, universal proof or actual Lean kernel execution.

The priority numbers are a reproducible scheduling heuristic, **not**
mathematical significance or probabilistic proof confidence.

## Usage

From the repository root with Python 3.11+:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

Construct the original source-bound database and import the bounded frontier
and complete exact-n6 certificates first. Follow
[frontier lineage](frontier_lineage.md),
[exact n6 proof](exact_n6.md), and
[exact knowledge](knowledge_exact_n6.md).

Run the planner:

    axiom knowledge-graph-plan \
      --db research/knowledge/axiom.sqlite3 \
      --limit 100 --offset 0 \
      --output research/knowledge/graph_plan_v014.json

    axiom knowledge-graph-plan-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/knowledge/graph_plan_v014.json

    axiom knowledge-graph-plan \
      --db research/knowledge/axiom.sqlite3 \
      --order 6 --limit 20 --offset 0

    axiom knowledge-graph-plan \
      --db research/knowledge/axiom.sqlite3 \
      --order 7 --limit 20 --offset 0

Pagination is explicit and stable; tasks have canonical content-addressed
IDs. \`source_fingerprint\` includes the original graph and federation
digests, historical source-bound Lean batch digests, and both the bounded
frontier and exhaustive exact-n6 campaign digests.

## Trust and audit model

Before producing **any** tasks, the planner calls the full v0.13 source
auditor. That auditor independently replays original v0.5 finite-graph
reports, v0.7 mathematical federation, historical v0.8 Lean source links,
every imported n6/n7 bounded frontier search, and every imported exact
n=6 exhaustive certificate. Every materialized table is compared to
expected replay output, and referential integrity must pass.

The planner requires **at least one successfully imported exact n6
campaign**. It never fabricates an exact certificate when there is only
bounded n6 evidence.

The saved agenda audit recomputes the entire source-replayed task set and
requires byte-equivalent canonical JSON content, including source
fingerprint and requested paging configuration. It rejects tampered
plans, falsified status fields, altered proofs and missing source files.

An offline historical Lean source record is not proof of an independently
observed Lean run, and Python's exhaustive finite certificate is also not
a formal Lean theorem. The next action explicitly requests a genuine
kernel-checking implementation, without prematurely attributing one.

## Verification and performance

    pytest -q tests/test_knowledge_graph_plan.py

The dedicated \`.github/workflows/reconciled-graph-agenda.yml\` workflow
rebuilds every source layer from exact historical reports, runs real
bounded n6/n7 and full n6 32,768-labelled-graph experiments, imports
and audits them, generates and independently audits the graph agenda,
and preserves complete database, results and task JSON artifacts on
Python 3.11 and 3.13.

The expensive integration suite is executed in full in its dedicated
matrix; legacy graph and Lean jobs retain all previous research and kernel
checks and do not duplicate this heavyweight file unnecessarily.

The computational cost of audit is intentionally significant: it
reexecutes scientific experiments rather than trusting stored labels.
Future optimization may use signed, independently verified immutable
campaign snapshots, but never skip provenance verification by default.

## Next research milestone

Use the highest-priority still-open n=7 graph tasks to run stronger
nonduplicate falsification experiments. A full labelled n=7 exhaustive
search would require **2^21 = 2,097,152 graphs per statement**; no n=7
finite proof should be issued unless a complete, independently checked
procedure actually covers the target finite domain.
