# Certified novelty filtering v3

Run new campaigns with `axiom graph-discover --novelty-profile certified-v3`.
The profile is opt-in. Earlier campaigns still use their original manifests
when audited.

The filter searches for a rational linear combination of known bounds. It
checks the combination with exact fractions. Since the target expression
takes integer values, any certified upper bound strictly below the target
bound plus one is sufficient. For example, on triangle-free graphs, a
rational bound of 3/2 on clique number minus matching number certifies an
integer bound of 1.

The filter can also split by whether the graph has any edges. It checks
the empty graph directly and substitutes the exact invariant values for
every nonempty edgeless graph. In the branch with an edge, it can use
additional bounds such as a clique number of at least two and a matching
number of at least one. This certifies, for example, that a bipartite
graph's chromatic number is at most twice its component count. The
verifier checks both edgeless cases before accepting a certificate from
this branch. Certificate replay needs no optimizer.

## Frozen candidate comparison

Both profiles classified the same archived v2 candidate statements for
each seed.

| Seed | Statements | Known with v2 | Known with v3 | Newly certified |
| --- | ---: | ---: | ---: | ---: |
| 1729 | 1,195 | 102 | 132 | 30 |
| 2718 | 1,161 | 84 | 112 | 28 |

Across the two seeds, v3 certified 30 distinct additional statements. The
edge split accounted for 28 and integer rounding for two. Every v2 known
classification carried over. The frozen control suite certified all 24
known implications and accepted none of the 10 false statements. Four
targeted counterexamples exercise tighter bounds and relaxed premises.

An unknown result still needs mathematical and prior-art review.

## Verification

```bash
python -m pytest -q tests/test_graph_novelty.py tests/test_graph_discovery.py tests/test_graph_proof_pipeline.py
PYTHONPATH=src python scripts/benchmark_graph_competition.py --autographforge /path/to/AutoGraphForge --novelty-profile certified-v3 --output /path/to/controls.json
bash scripts/replay_graph_competition.sh /path/to/v7-archive /path/to/new-run certified-v3
```
