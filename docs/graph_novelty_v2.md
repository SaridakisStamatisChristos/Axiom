# Certified novelty filtering v2

Use `axiom graph-discover --novelty-profile certified-v2` on new experiments.
The certified profiles bind each decision to a versioned fact manifest.
The earlier `certified-v1` reports still replay with the original manifest.

The fact bank grows from 34 to 41 exact affine rows. The new rows cover
spanning-forest size, coloring around a maximum independent set, coloring
from a spanning tree, maximum degree versus component count, unmatched
vertices in a maximum matching, and the connected graph's minimum order
and component count. Each added row has a mathematical justification.
The connected assumptions matter. The cycle-rank bound applies to connected
graphs, and the global spanning-forest bound includes the empty graph.

The six previously unresolved replacement trials represent four distinct
inequalities. Duplicates occur across seeds. All four classify as known
in v2. The two connected bounds follow from the cycle-rank coloring
bound, nonnegativity of the number of triangles, and the connected edge
bound. The pinned Lean checks prove both relaxations and the spanning
forest and independent-coloring bounds over finite simple graphs.

## Paired campaign

| Seed | Known with v1 | Known with v2 | New known classifications |
| --- | ---: | ---: | ---: |
| 1729 | 81 | 102 | 21 |
| 2718 | 65 | 84 | 19 |

The gains cover 24 distinct statements across both seeds. Candidate
identities and generation settings matched across profiles. Every v1
known classification remained known. The frozen implication suite gave
24/24 known controls certified and 0/10 false controls accepted. Six
additional counterexamples exercise tightened and weakened-premise
variants of the added rules.

The fact bank acts as a sufficient implication filter. An unknown result
can still be a rediscovery. Novelty also requires independent mathematical
and prior-art review.

## Verification

The graph discovery audit replays the two campaigns against their
original source snapshot and checks the exact rational coefficients.
The support proof below checks the principal rows in Lean using the
same invariant definitions as the established universal graph checker.

```bash
python -m pytest -q tests/test_graph_novelty.py tests/test_graph_discovery.py tests/test_graph_proof_pipeline.py
proof=$(mktemp --suffix=.lean)
cat src/axiom/lean/GraphUniversal.lean research/autographforge/novelty-v2-support.lean > "$proof"
lake env lean -DwarningAsError=true "$proof"
rm -f "$proof"
bash scripts/replay_graph_competition.sh /path/to/v7-archive /path/to/new-run certified-v2
```
