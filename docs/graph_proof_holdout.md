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
