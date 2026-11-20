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

## Composing statements in Python

Use `AffineExpression` to add, subtract, or scale affine expressions on
either side of an inequality. Invariants and assumptions use enums, and
coefficients and constants accept `int` and `Fraction`.

```python
from fractions import Fraction

from axiom.graph_affine import (
    AffineExpression, AffineGraphConjecture, GraphAssumption, GraphInvariant,
)

alpha = AffineExpression.invariant(GraphInvariant.INDEPENDENCE)
omega = AffineExpression.invariant(GraphInvariant.CLIQUE)
order = AffineExpression.invariant(GraphInvariant.ORDER)
statement = AffineGraphConjecture.from_expressions(
    (alpha + omega).scaled(Fraction(1, 2)),
    (order + AffineExpression(constant=1)).scaled(Fraction(1, 2)),
    assumption=GraphAssumption.ALL,
)
```

The constructor combines repeated terms and cancels shared terms across both
sides before applying the existing coefficient, bound, and arity limits to
the normalized statement. The example has the same JSON representation and ID
as the flat form `alpha + omega - n <= 1`. Reordering terms, moving terms
across sides, or multiplying both sides by a positive rational preserves the
ID. Reversing an inequality or changing its assumption can change its meaning
and is outside that normalization. IDs represent canonical syntax and do not
establish equivalence under graph-specific facts.

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

## Persistent affine discovery

Use `graph-discover` for new experiments. This lane fits exact affine
inequalities and equalities from orders 5, 6, and 7. When an expression is
constant across the applicable discovery cohort, it emits an equality and
checks both directions. Integer-lattice normalization canonicalizes scaled
bounds and sign-reversed equalities. Symbolic bounds reject some tautologies
and safely remove implications within the candidate bank. Training scores
describe fit and guide experimental priority.

Discovery and reference invariant implementations agree on every training
graph. Selection then screens candidates against the audited historical n=7
bank, and the first use of the new n=7 masks is holdout testing. The sampler
is premise-aware and nonuniform. All refutations carry an exact graph witness
rechecked by both implementations. The report gives explicit reason codes
when discovery or historical preflight leaves no eligible candidate.

Use a separate SQLite ledger and reuse it across campaign names. It stores
every checked holdout under its exact `(graph order, labelled mask)` key.
A transaction commits each report and its masks together. Auditing replays
the ordered prefix through the requested campaign. Repeating a name with
identical parameters replays its original result. Optionally pass audited
historical holdouts using `--legacy-v18`, `--legacy-guided`, and
`--legacy-stratified` to exclude their observations too. The stratified
artifact requires its original v0.18 parent. Supply the same legacy inputs
for each command using a given ledger.

```bash
common=(--db research/knowledge/axiom.sqlite3 --ledger discovery.sqlite3)
axiom graph-discover "${common[@]}" --campaign first > first.json
axiom graph-discover "${common[@]}" --campaign followup > followup.json
axiom graph-discover-audit "${common[@]}" --campaign followup --artifact followup.json
axiom graph-discover-benchmark "${common[@]}" --campaign first
axiom graph-discover-lean "${common[@]}" --campaign first > first-lean.json
```

The benchmark reports the replay wall time, workload counts, and candidate
throughput. The Lean command replays the named campaign and automatically
dispatches the surviving claims to the pinned kernel after exhaustive
dual-oracle precheck at exactly three vertices. The translator derives each
invariant from the four possible edge-count cases and uses a decidable
proposition over all eight labelled masks. An equality requires kernel
acceptance of both directions. A precheck counterexample refutes the original
universal conjecture. A kernel success verifies only the fixed-order result.
Use [universal proof dispatch](graph_universal_v020.md) for the supported
arbitrary-order relations.

The CI workflow archives both campaigns, the SQLite ledger, benchmark
measurements, tamper rejection, and source-bound Lean records. The original
v0.18 report and v0.19 proof formats remain replayable.
