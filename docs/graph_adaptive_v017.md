# AXIOM v0.17 — information-aware graph hypothesis scheduler

This layer addresses the experimental shortcoming exposed by v0.16: the
source-derived v0.14 agenda contained only two live n=7 bounded tasks, both
elementary bipartite independence lower bounds. Blindly repeating these tests
cannot create meaningful research diversity.

v0.17 extends **candidate selection**, not the theorem grammar. Every
generated candidate is an existing closed, typed AXIOM graph template at
exact order n=7. Mathematical originality remains **NOT ASSESSED**.

The scheduler first invokes the full v0.14 replay gate; from the vetted
historical research database it then reconstructs the union of labelled
graphs already sampled by original and frontier campaigns. It selects up
to \`--source-probe\` old graphs with a deterministic hashed order and
checks every grammar candidate against them *before* allocating new
research computation.

Candidates already refuted in the historical findings are excluded.
Candidates contradicted by an old graph produce a new independently
checked graph witness, **without** claiming a newly explored graph.
Elementary implications (e.g., the bipartite colour-class bound
alpha >= ceil(n/2)) are routed to a **deferred formalization candidate**
classification; no formal proof is claimed. Candidate assumptions never
satisfied by the probe are reported separately, not mistaken for evidence
in favor of the conjecture.

Eligible hypotheses are ranked by an explicit subjective resource heuristic
based on preflight applicability, conditionality and whether the statement
appeared in older campaigns. This is not a truth estimate or a novelty
measure. The top eligible candidates receive new, unique labelled graph
masks, excluding all historical masks and masks used by earlier experiments
in the same run. Counterexamples are checked by two independent invariant
engines; survivors remain **SURVIVED_BOUNDED_SEARCH**.

## Usage

Construct a v0.14/v0.16 research database using the documented source
imports, then run:

    axiom graph-research-discover --db research/knowledge/axiom.sqlite3 \
      --output research/knowledge/discovery_v017.json \
      --seed 42 --source-probe 96 --experiment-budget 48 --task-limit 4

    axiom graph-research-discover-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/knowledge/discovery_v017.json

Evidence is immutable, content bound to its source fingerprint and fully
replayed by the audit command. No historical report or original SQLite
finding is modified.

## Limitations

- Fixed n=7; no universal theorem claims.
- The hypothesis language is the current 25-template AXIOM grammar, not
  a general generator of new mathematics.
- Structural deferral is a heuristic to prioritize Lean formalization.
  The scheduler does not itself invoke Lean.
- Source probes are deterministic bounded tests. A surviving candidate
  need not be true.
- Source probes may not cover graph assumptions such as rare forests or
  specific chromatic configurations. Those cases are marked as
  insufficient-coverage tasks for future targeted sampling.
