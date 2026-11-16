# AXIOM v0.19 — premise-aware independent graph holdout

Prior versions selected n=7 graph masks uniformly from an odd-stride traversal
of all 2^21 labelled simple graphs, irrespective of a conjecture's antecedent.
This rendered an important v0.18 bipartite experiment inconclusive: none of
its 24 held-out graphs were bipartite.

This version adds **a distinct follow-up research lane**. Source-audit and
replay the previous v0.18 experiment, then exclude every historically observed
n=7 mask and every prior v0.18 holdout graph. Generate a new deterministic,
bounded, *antecedent-filtered* sample for each previously selected conjecture.

- ALL: use the existing full-period odd-stride generator, with exclusions.
- CONNECTED: use a full-period odd-stride generator and keep only graphs
  independently confirmed to be connected.
- TRIANGLE_FREE: use the same deterministic traversal, accepting only graphs
  whose independently computed triangle count is zero.
- BIPARTITE: deliberately construct a labelled two-colour partition and a
  deterministic pseudorandom subset of between-partition edges; independently
  verify bipartiteness before accepting each graph.

**Sampling caveat:** These are stratified research cohorts and are NOT
uniform samples from the labelled graph space restricted by each assumption.
In particular, the bipartite generator is biased by partition multiplicity.
The report explicitly records this limitation. Statistical claims about the
fraction of graphs obeying an inequality are therefore inappropriate.

All accepted new graphs are pairwise distinct, excluded from the historical
source bank, and tested under the exact typed antecedent of their conjecture.
Each sample preserves the number of proposals, rejections, and
premise-satisfying graphs. If a budget produces zero qualifying graphs, the
result is explicitly inconclusive and never called surviving.

The new experiment does **not** revise the v0.18 selection stage and does not
train on its new test cohort. Every counterexample is independently checked
by the two existing graph-invariant implementations. The final evidence JSON
includes a parent v0.18 digest and undergoes deterministic source-replayed
audit. It does not overwrite either the historical SQLite evidence or
the original v0.18 experiment.

## CLI

    axiom graph-stratified-followup \
      --db research/knowledge/axiom.sqlite3 \
      --parent research/knowledge/affine_synthesis_v018.json \
      --output research/knowledge/stratified_followup_v019.json \
      --seed 43 --budget 24 --max-proposals 20000

    axiom graph-stratified-audit \
      --db research/knowledge/axiom.sqlite3 \
      --parent research/knowledge/affine_synthesis_v018.json \
      research/knowledge/stratified_followup_v019.json

## Evidence scope

The v0.19 conditional sampler only tests order n=7. A bounded survivor
never establishes a universal theorem, even if it passes every sampled
test. No Lean verification is done by the conditional sampler. The existing
Lean formalization lane remains separate.

Next formalization goal: a sound, closed affine-to-Lean graph semantics
translator with strictly scoped finite-order proofs, followed by a theorem
schema supporting arbitrary graph orders. These are different achievements;
a finite-order kernel proof does not imply universal validity.
