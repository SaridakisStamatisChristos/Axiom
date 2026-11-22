# Graph proof coverage and matched CPU tactics

The frozen suite has 100 distinct typed affine inequalities, 25 for each
supported premise. Twenty anchor families contribute five combinations each.
Every combination adds a mathematically valid secondary inequality with a
positive coefficient. Existing proof-benchmark coefficient directions and
the exact anchor directions are excluded at the same premise. The frozen
statements can still share mathematical facts with prior engine development.
The benchmark measures transfer to new compositions of known graph bounds.

The runner gets canonical statements without derivations, human proof scripts,
answer hints, or a success cache. The generator provides the truth argument
for the test inputs and is used only to freeze the suite. For example,
choosing one endpoint per edge gives a vertex cover of size at most the
edge count. A matching needs distinct cover vertices. In a connected graph,
every vertex beyond a maximum-degree vertex contributes at least one to
the degree sum. Matching-edge contractions leave at least one vertex in
each component. The remaining anchor arguments use spanning trees, greedy
coloring, clique triples, independent color classes, neighborhood deletion,
or the bipartite coloring and matching identities. Two independent exact
graph oracles also screen every case through order five.

## Protocol

- Compare AXIOM retrieval indexes v7 and v9 from the same pinned engine with
  the same proof options, including 10,000 search nodes, five retrieved
  adapters, three synthesized lemmas, 16 plans, and a 45-second Lean timeout.
- Run the six tactics, in order, from the pinned AutoGraphForge local CPU
  prover against the identical integer statement and graph definitions using
  the same Lean installation and 45-second kernel limit. Each tactic must
  close all goals before it is allowed to win. The shared frontend omits
  AXIOM lemmas. The runner records native AutoGraphForge exporter vocabulary
  overlap separately so its lack of a native symbol cannot appear as a
  proof failure. This lane measures the upstream tactic portfolio through a
  shared frontend. AutoGraphForge's model-based and full discovery results
  require a separate experiment.
- Only an accepted kernel result with allowed axioms counts as a proof.
  Report all 100 cases and the common native exporter vocabulary subset.
  For each comparison, report both discordant counts and a descriptive 95%
  paired percentile interval resampling the 20 anchor families. Variants
  within an anchor share facts, and the families form a fixed benchmark.
- The AXIOM milestone requires an increase of at least 15 percentage
  points over v7. Treat the measured margin as an outcome rather than a
  reason to revise the frozen suite. Keep the discovery holdout separate.

## Results

| Premise | Statements | AXIOM v7 | AXIOM v9 | AutoGraphForge CPU tactics |
| --- | ---: | ---: | ---: | ---: |
| All graphs | 25 | 21 | 24 | 0 |
| Connected | 25 | 13 | 19 | 0 |
| Triangle-free | 25 | 18 | 19 | 0 |
| Bipartite | 25 | 15 | 14 | 0 |
| Total | 100 | 67 | 76 | 0 |

AXIOM v9 gained 14 proofs and lost five, for a net increase of nine
percentage points. The paired family bootstrap interval was −4 to +25
points. The preregistered 15-point gate did not pass. The largest increase
was on connected graphs. Nine v9 attempts exhausted bounded search and
15 reached Lean without an accepted proof.

Ten statements use only symbols in both native vocabularies. Lean checked
the equivalence of those ten AutoGraphForge exports to the corresponding
typed goals. Both AXIOM versions proved seven of those ten. AutoGraphForge's
six CPU tactics proved zero on both the shared and native-form goals. A
separate source-matched check replayed AutoGraphForge's stored
`omega_le_order` proof and checked a fresh AXIOM proof of the same bound
under the common pin. This source replay was outside scoring.

The paired interval for v9 against the shared-frontend CPU tactics was
+61 to +89 points. The frozen workload measures known affine graph bounds
and AXIOM's CPU proof search against the local tactic portfolio. The result
does not establish a comparison with AutoGraphForge's neural or discovery
lanes.

A diagnostic run of the five lost cases kept the v9 fact bank and disabled
integer rounding. It recovered P022 and P067, both of which had exhausted
their original v9 node budgets. P090 reached Lean but remained unresolved.
P046 still exhausted search, and P062 still lacked a checked proof. These
five reruns were excluded from scoring.

## Reproduce the run

Install AXIOM's development dependencies and prepare its pinned Lean and
Mathlib checkout. Check out AutoGraphForge at
`4d1a8afc99447cacd2328cca20e47b6493e8dbc5`. The output directories must be new.

```bash
python scripts/benchmark_graph_proof_coverage.py \
  --autographforge /path/to/AutoGraphForge --output /path/to/coverage --workers 5

lake exe cache get Mathlib.Data.Real.Basic Mathlib.Tactic.Linarith Mathlib.Tactic.NormNum
python scripts/check_autographforge_proof_transfer.py \
  --autographforge /path/to/AutoGraphForge --output /path/to/transfer
```

The supplement preserves each graph premise and provides equivalence proofs on
the common vocabulary subset. It uses the upstream natural-number affine
normalizer on unrestricted goals and its conditioned exporter on scoped
goals. Its kernel runs use the same pinned AXIOM environment.

The source transfer checks the theorem in the published AutoGraphForge
artifact after substituting the minimal required imports and extracting the
proved declaration. The original artifact is pinned in the transfer evidence.
[AutoGraphForge source](https://github.com/JanPastorek/AutoGraphForge/blob/4d1a8afc99447cacd2328cca20e47b6493e8dbc5/results/verified_proofs/oprover-32b_61f2701ba25e.lean)
