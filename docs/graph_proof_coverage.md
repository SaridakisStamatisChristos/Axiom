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
