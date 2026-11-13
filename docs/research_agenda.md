# AXIOM v0.10 — Evidence-gated autonomous research agenda

## Scientific purpose

AXIOM now has four source-separated mathematical domains (finite graphs,
integer-polynomial algebra, elementary number theory, modular recurrences),
an independently replayed cumulative evidence federation, and historical
Lean proof records bound to their exact original statements.

The next research problem is **selection**: which unanswered questions should
be investigated next without repeating disproved claims, mistaking empirical
survival for proof, or fabricating a formal-verification result?

This milestone implements a deterministic, auditable research-action scheduler.
It is *not* a new proof system, an LLM, a novelty assessor, or an autonomous
execution daemon.

## Trust and evidence gates

Before returning any task, the scheduler:

1. Replays the entire v0.5 finite-graph source evidence and verifies its
   knowledge-graph materialization.
2. Replays each original v0.2/v0.3 and v0.4 mathematical source using the
   respective domain-native auditor, rebuilding the typed v0.7 federation.
3. Re-checks all imported historical v0.8 Lean records against full source
   statements, local certificates and original report identities.
4. Computes a fingerprint from all exact graph, federation and formal source
   digests, not from a user-written ranking or unverifiable summary.

Any altered source, edge, evidence state, orphan record, or materialized
relationship causes failure before any proposed work is returned.

## Deterministic scheduling policy

Each distinct, typed *exact-domain statement* gets at most one actionable task.

| Original evidence | Proposed next action | Priority |
|---|---|---|
| Experimentally supported / unresolved; no proof | FALSIFY_WITH_INDEPENDENT_SEARCH | 1 |
| Algebra or number-theory local proof, no historical Lean record indexed | FORMALIZE_SUPPORTED_FRAGMENT | 2 |
| Algebra or number-theory proof, source-bound historical Lean record present | REEXECUTE_PINNED_LEAN | 3 |
| Fixed-n graph or modular-recurrence local certificate | FORMALIZE_EXACT_SCOPE | 4 |
| Already refuted | **Not scheduled** | — |

Priorities are deterministic editorial workflow suggestions, **not**
scientific confidence or mathematical significance scores. Ties are broken
by domain and content-addressed statement ID. Results retain exact typed
mathematical statements, supporting source campaigns, finding IDs, certificate
IDs, and offline Lean record IDs where relevant.

Graph proof scope remains **exact fixed graph order**, not all graph orders.
Modular recurrence scope is the claimed finite-state periodicity property.
Source-bound offline historical Lean records carry the marker
\`NOT_ESTABLISHED_BY_OFFLINE_AUDIT\`; the recommended work is actual kernel
reexecution, not unearned promotion to \`FORMALLY_VERIFIED\`.

No plan claims novelty or a new theorem; the agenda output explicitly records
zero proof-status upgrades.

## Reproduce locally (Ubuntu / Linux Mint)

From the repository root:

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

    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --limit 30 --output research/knowledge/research_agenda_v010.json

    axiom knowledge-plan-audit --db research/knowledge/axiom.sqlite3 \
      research/knowledge/research_agenda_v010.json

    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --domain graph --limit 10
    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --limit 100 --offset 100

The saved agenda is stable (no timestamps, nondeterministic IDs or secret
network state) and independently reproducible. The auditor reconstructs the
entire task set, applies the saved domain and limit, and requires an
exact canonical match. JSON files are saved via atomic replacement.

The agent may take the next top-ranked task, but the task itself provides
no authorization to skip appropriate experiment validation, provenance
capture or real Lean kernel checks.

## Verification

    pytest -q tests/test_knowledge_agenda.py
    pytest -q

The dedicated GitHub Actions workflow in
\`.github/workflows/research-agenda.yml\` runs on Python 3.11 and 3.13,
rebuilds the entire original evidence index, imports the full original
85 algebra and 96 number-theory historical Lean records, produces and
independently audits an agenda artifact, and preserves the resulting
SQLite and JSON files for inspection.

Legacy pinned Lean verification remains a separate actual kernel-execution
workflow. This milestone never treats offline import or CI metadata as a
new theorem proof.

## Open research obligations

- A ranking heuristic cannot substitute for open-problem novelty or value.
- New bounded graph counterexamples from the v0.9 frontier are not
  automatically folded into the immutable v0.5 reports; a typed
  frontend ingestion and separate audit are needed.
- Scheduling does not run the proposed tasks or learn from subsequent results.
- Genuine external Lean reexecution, trusted source translation, and future
  proof assistant generalization remain distinct obligations.
