# AXIOM v10 and v11 proof holdout

Protocol v4 compares the frozen v10 and v11 proof engines from PR #50 on 100
new affine statements. The manifest was committed before either lane ran
against it. The generator only reads previous statement fixtures. It samples
five directions per anchor using a fixed seed and excludes previously tested
canonical premise/direction pairs. Each premise contributes 25 statements.

The primary outcome is the paired difference in accepted Lean proofs at
10,000 search nodes and a 45-second Lean timeout per statement and profile.
The comparison reports wins, losses, and a descriptive 95% bootstrap interval
resampling the 20 anchor families. Secondary bounds recur across families, so
the interval describes this benchmark and its chosen grouping. These synthetic
compositions measure transfer within the supported affine vocabulary. They
share mathematical ingredients with earlier suites.

## Anchor justifications

Let (n) denote vertices, (m) edges, (chi) the chromatic number, (omega)
the clique number, (alpha) the independence number, (Delta) the maximum
degree, (
u) the matching number, (c) components, and (t) triangles.

| Scope | Anchor | Justification |
| --- | --- | --- |
| All | (Deltale n) | A vertex has at most (n-1) neighbors when it exists. The empty graph has degree zero. |
| All | (chi le 2
u+1) | The endpoints of a maximum matching form a vertex cover. Each endpoint can have its own color and the remaining vertices share one color. |
| All | (clealpha) | Pick one vertex per component. |
| All | (chi+alphale n+1) | Color a maximum independent set with one color and give the other vertices distinct colors. |
| All | (
ule m) | Matching edges are graph edges. |
| Connected | (nge1) | The premise includes nonemptiness. |
| Connected | (Deltale n-1) | Simplicity prohibits loops and the graph is nonempty. |
| Connected | (cge1) | A connected graph has exactly one component. |
| Connected | (chile m+1) | Combine (chile n) and the spanning-tree bound (nle m+1). |
| Connected | (alpha+cle n+1) | Use (alphale n) and (c=1). |
| Triangle-free | (chilealpha+1) | Greedy coloring gives (chileDelta+1), and a maximum-degree neighborhood is independent. |
| Triangle-free | (omegalealpha+1) | A nonempty graph has (alphage1) and triangle exclusion gives (omegale2). The empty case has (omega=0). |
| Triangle-free | (tge0) | Triangles form a finite set. |
| Triangle-free | (Deltale n) | The universal degree bound also applies under this premise. |
| Triangle-free | (omegale
u+1) | A clique of size two supplies a matching edge. All remaining clique sizes are at most one. |
| Bipartite | (chile2) | The parts provide the two colors. |
| Bipartite | (omegalechi) | Each clique vertex requires a distinct color. |
| Bipartite | (omegale n) | Clique vertices are graph vertices. |
| Bipartite | (
ulealpha) | A matching has at most one edge per vertex of either part, and either part is independent. |
| Bipartite | (clealpha) | One vertex per component gives an independent set. |

The generator adds positive multiples of secondary bounds to these anchors.
Of the two less immediate secondary bounds, (nlealpha+m) follows by
selecting one endpoint per edge to obtain a vertex cover. The inequality
(omegale n+t) follows from (omegale n). The development generator
defines the remaining secondary catalog. Before proof attempts, two graph
oracles check each applicable statement on every labelled graph through order
five.

```bash
python scripts/freeze_graph_proof_holdout.py /tmp/proof_holdout_100_v1.json
cmp /tmp/proof_holdout_100_v1.json research/proof_engine/proof_holdout_100_v1.json
python scripts/benchmark_graph_proof_coverage.py --protocol v4 --workers 8 \
  --output /path/to/new/holdout-results
```

## Results

| Premise | Statements | v10 Lean proofs | v11 Lean proofs |
| --- | ---: | ---: | ---: |
| All graphs | 25 | 17 | 18 |
| Connected | 25 | 20 | 21 |
| Triangle-free | 25 | 21 | 24 |
| Bipartite | 25 | 20 | 24 |
| Total | 100 | 78 | 87 |

v11 gained nine proofs and retained all 78 v10 proofs. The paired family
bootstrap interval was +3 to +17 percentage points. The gains span six
anchor families. Restoring the v10 inventory in the v11 fallback reproduced
the identical accepted Lean source for all nine gains, isolating the gain to
the full-inventory search on this workload.

Thirteen statements remain unresolved. Eleven come from three families
based on the maximum-matching vertex cover, connected-component uniqueness,
and coloring a maximum independent set. All 200 attempts passed offline
evidence replay, and the graph oracles checked 1,100 labelled graphs. The
[aggregate results](../research/proof_engine/proof_holdout_results_v1.json)
are stored with the protocol.

## v12 palette certificates

The opt-in v12 profile colors an independent set with one color and assigns a
distinct color to each remaining vertex. A second certificate recursively removes
the endpoints of an edge, extending a matching and a coloring together. This
gives a coloring using at most twice the matching number plus one colors.
Connected graphs also expose both directions of the component-count equality.
The discovery profile is `palette`. For individual statements use
`graph-prove --retrieval-index v12 --retrieve-lemmas 5 --synthesize-lemmas 3 --split-order --induct-edges --proof-plans 16`.

| 100-statement suite | v11 | v12 | New proofs | Lost proofs |
| --- | ---: | ---: | ---: | ---: |
| Original development suite | 91 | 95 | 4 | 0 |
| First holdout, used for v12 development | 87 | 97 | 10 | 0 |
| Second holdout, frozen before scoring | 86 | 99 | 13 | 0 |

Each run used the same 10,000-node cap and 45-second Lean timeout. The first
two comparisons use archived v11 attempts and newly executed v12 attempts.
The second holdout ran both engines and replayed all 200 attempts. Its 100
premise/direction pairs are distinct from both earlier suites. It samples the
same 20 anchor families. The 13 gains were concentrated in component uniqueness
(5), independent-set coloring (4), and matching-based coloring (4). The
descriptive paired family bootstrap interval is 0 to 28 percentage points.
H092 in this second holdout remains unresolved in the bipartite matching family.

Reproduce the fresh paired evaluation from this revision using the pinned Lean
toolchain and Mathlib checkout.

```bash
PYTHONPATH=src python scripts/benchmark_graph_proof_coverage.py \
  --protocol v5 --workers 8 --output /tmp/axiom-palette-fresh
```

Protocols v6 and v7 rerun both lanes on the original and first-holdout suites,
respectively. The [regression results](../research/proof_engine/proof_palette_regression_results.json)
include each statement's outcome and the v12 attempt digest. The
[fresh results](../research/proof_engine/proof_holdout_results_v2.json)
give the paired comparison and breakdown by premise.
