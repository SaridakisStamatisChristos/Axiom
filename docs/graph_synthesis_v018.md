# AXIOM v0.18 — Compositional graph-conjecture laboratory

## Motivation

v0.17 ranked 45 instances of AXIOM's original 25 graph theorem templates.
Source replay showed nearly every template was already falsified, elementary,
or vacuous; its one surviving task (alpha + omega <= n + 1) is a known
elementary theorem. A fixed catalog cannot supply novel mathematical questions
by repeated sampling.

v0.18 introduces a **second, nonbreaking statement grammar**: exact
rational affine inequalities over the integer invariants n, edges, triangles,
independence, clique number, chromatic number, maximum degree, matching number,
and connected-component count. Each expression is canonicalized by clearing
positive denominators and dividing by the integer GCD. A negative multiplier
is never silently applied to <=. Only two graph observables plus optional n
are admitted in the initial search, bounding the search complexity.

The statements have explicit universal quantification over all finite simple
graphs, but their evidence is finite and therefore **NOT_PROVED** unless a
separate valid proof is eventually produced.

## Training and holdout separation

1. Independently audit all existing AXIOM research layers with the v0.14
   source replay gate; reconstruct exact historical labelled n=7 masks.
2. Train on all 1,024 labelled n=5 simple graphs, a deterministic bounded n=6
   sample, and a deterministic bounded sample of *historical* n=7 graphs.
3. Enumerate integer coefficient pairs from {-2,-1,1,2}, optional n coefficients
   from {-1,0,1}, and assumptions ALL, CONNECTED, BIPARTITE, TRIANGLE_FREE.
4. Fit the smallest observed upper bound for each statement using discovery
   data exclusively. Remove normalized duplicates, equations tight at fewer
   than two graph orders, and combinations that add no information beyond
   the independent marginal envelopes on the training corpus. Flag selected
   known elementary bounds for formalization rather than repeated testing.
5. Rank the remaining cross-order-correlated candidates by a reproducible
   **subjective resource-allocation heuristic**. It is not an estimated
   probability of correctness or a novelty score.
6. Before any new experiment, preflight promising candidates against **all**
   historical labelled n=7 masks, not merely the source training subset.
   Any old counterexample receives a separately checked source witness
   and zero newly explored masks. Defer known universal elementary bounds
   even when a candidate is expressed under a stronger assumption.
7. Only *after* full historical preflight, allocate genuinely unseen n=7
   graph masks for each surviving selected candidate. Exclude all historical
   n=7 masks and masks checked for earlier candidates in the run. This is
   the sealed holdout cohort.
8. Recheck any counterexample with two independent graph-invariant engines,
   and preserve REFUTED_ON_HOLDOUT, SURVIVED_BOUNDED_HOLDOUT, or
INCONCLUSIVE_NO_ANTECEDENT_COVERAGE when no held-out graph satisfies the
statement's antecedent.

Training and holdout graph counts, mask digests, all selected statements,
counterexamples and kernel-proof boundaries are preserved as an immutable JSON
artifact. A full source-replayed audit recomputes the entire experiment and
rejects tampering or changed parameters.

## CLI

    axiom graph-synthesize --db research/knowledge/axiom.sqlite3 \
      --output research/knowledge/affine_synthesis_v018.json \
      --seed 42 --n6-training 64 --n7-training 64 \
      --holdout-budget 32 --max-candidates 4

    axiom graph-synthesize-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/knowledge/affine_synthesis_v018.json

Use the established v0.14 source/federation/frontier/exact-n6 import commands
to prepare the DB; missing historical research is a hard failure.

## Proof boundaries

The new affine grammar **does not have a sound AXIOM-to-Lean graph semantics
translator yet**. The JSON output includes a machine-readable
PENDING_AFFINE_TO_LEAN_TRANSLATION queue for surviving statements. It does
*not* assert that Lean ran or that a proof exists. The real v0.15 Lean executor
continues operating on its own existing, previously supported templates.

- Exact n=5 training enumeration means only the training corpus covers all
  labelled graphs of that *one* order. It does not prove a universal theorem.
- n=6 training and n=7 historical and holdout cohorts are bounded.
- Holdout passes do not imply a proof, universal generality or originality.
- Novelty remains NOT_ASSESSED until a genuine literature review.
- Zero new candidates is an allowed, negative scientific result. Never invent
  new theorems or artificially pass validation gates.
- Earlier source evidence is not modified and v0.15/16/17 APIs are unchanged.
