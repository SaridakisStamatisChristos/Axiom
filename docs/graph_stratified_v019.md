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


## Closed affine-to-Lean finite-order bridge

The first trusted translator is deliberately restricted to **exactly three
vertices**, unconditional inequalities using *edges* and *triangles* (with
optional n). It computes graph semantics in Lean from the three bits of the
labelled edge mask and a three-edge conjunction for triangle presence.
The checker runs over the finite mask type \`Fin 8\` and accepts only a real
successful pinned Lean/Mathlib kernel execution with audited permitted axioms.

Before constructing any Lean source, two independent Python invariant
engines verify the input inequality on all eight labelled n=3 graphs.
A source counterexample or any unsupported invariant or graph antecedent
is rejected, not approximated.

Generate a source statement file using:

    python - <<'PY'
    import json
    from axiom.graph_affine import AffineGraphConjecture
    stmt=AffineGraphConjecture.normalized(
        {"triangles": 1, "edges": -1}, 0)
    open("affine_n3_statement.json","w").write(
        json.dumps(stmt.to_dict(),indent=2)+"\n")
    PY

Then run with the pinned Lean environment installed:

    axiom graph-affine-n3-lean affine_n3_statement.json \
      --project-root . --timeout 240 \
      --output affine_n3_verified.json --source AffineN3.lean

    axiom graph-affine-n3-lean-audit affine_n3_verified.json

The generated theorem proves only its **n=3 finite graph instance**, even
though the input source statement has an all-orders quantifier. No all-order
generalization is made. Offline source-integrity replay **does not attest**
that an external Lean process ever executed; only the original instrumented
CI/command execution and retained runner logs can support that claim.

This is not yet a generic Lean translator for the v0.18 graph grammar:
invariants such as independence number, clique number, chromatic number,
matching number and connected components require formal semantic definitions
and proofs. Conditional assumptions and arbitrary graph order n likewise
remain unsupported and are rejected.
