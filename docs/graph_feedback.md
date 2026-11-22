# Counterexample-guided graph discovery

`graph-discover-feedback` runs a fixed number of development rounds in one
SQLite campaign. Each round fits affine claims, applies the `certified-v3`
novelty filter, screens a bounded development corpus panel, and sends the
remaining candidates to `guided-v3` active refutation. The independent exact
checker replays each witness before it can affect fitting.

Unique witness feature rows from round one become fitting inputs in
round two. This includes orders outside the base training orders 5–7.
The report records training fingerprints, the originating statement and
stage of each admitted witness, per-stage work and the candidate bank
fingerprint. The base training and seed stay fixed across rounds.
`--no-feedback` uses the same searches and budgets for a control run.

The campaign freezes the last round's development survivors in the ledger.
`graph-discover-feedback-audit` reconstructs the ordered corpus panel and
replays fitting, certificates, screens, refutation and witness admission.
Reusing a campaign name with different parameters is rejected.

## Seal and score the final corpus

Build separate SQLite databases with `axiom.graph_corpus.ingest`. Use
`split="development"` for the development corpus and `split="final"` for
the sealed corpus. Give final families distinct names. Choose a development
order cutoff from 7 to 11. Both development searches respect this cutoff,
and every final graph must have a higher order, up to 12. This prevents
the mutator from independently generating a final graph under another
labelling.

Checkpoint and close the final SQLite database. Before fitting, pass its
SHA-256 as `--final-sha256`. The development and audit commands receive
only the development path. The final command requires the committed file
and uses the frozen candidates and the same declared corpus budgets.
Final outcomes are stored separately from the development rounds.
Final families must fit within the declared scan budget. A fitted
campaign with no final hash can still run and replay on development data.

```bash
final_sha=$(sha256sum final.sqlite3 | cut -d' ' -f1)
axiom graph-discover-feedback --corpus development.sqlite3 --ledger campaigns.sqlite3 \
  --campaign study --rounds 2 --final-sha256 "$final_sha" > development.json
axiom graph-discover-feedback-audit --corpus development.sqlite3 --ledger campaigns.sqlite3 \
  --campaign study > development-audit.json
cmp development.json development-audit.json
axiom graph-discover-feedback-final --corpus final.sqlite3 --ledger campaigns.sqlite3 \
  --campaign study > final.json
```

The reports describe bounded empirical outcomes. The corpus screen records
premise coverage and missing exact features by order.

## Two-seed replay

The smoke comparison used two rounds, 16 candidates per round, a
256-graph development panel and budgets of 64 exact corpus evaluations
and 64 active evaluations per claim. Development stopped at order 10.
Both lanes committed to the same five-graph final corpus at orders 11–12
before either lane fit any candidates.

| Seed | Witness rows admitted | Already-refuted round-one claims tested again, control → feedback | Round-two development survivors, control → feedback |
| --- | ---: | ---: | ---: |
| 1729 | 4 | 7 → 0 | 9 → 1 |
| 2718 | 3 | 6 → 0 | 10 → 2 |

All four development exports matched their replay byte for byte. The
five-graph final panel refuted zero frozen candidates in either lane.
This run verifies feedback and split isolation. The final sample is too
small to establish a survivor-quality advantage.

## Fresh candidates and a carried frontier

Use `--profile frontier-v2 --development-order 11` to spend each round's
candidate slots on distinct claims. The profile retains survivors across
rounds. It also checks them against previously verified development
witnesses and stores a new independent certificate for any cross-refutation.
With order 11 enabled, the active refuter starts from the Mycielski graph
of the five-cycle where applicable. This uses the same per-claim search
budget and makes the triangle-free four-chromatic case available to fitting.

Use a separate, precommitted order-12 final corpus for that campaign.
With `--profile frontier-v2 --no-feedback`, the control uses the same
search, candidate cache, frontier and cross-refutations. Its fitting data
stay fixed, allowing the study to isolate witness-driven refitting.
Existing reports without a profile continue to use their recorded
behavior.

### Matched order-12 check

Eight fresh seeds each received two rounds of 16 candidate slots. The
precommitted panel contained 108 order-12 graphs from nine families,
including 12 triangle-free four-chromatic extensions and no graphs from
the earlier study. Both frontier lanes shared order-11 development,
identical per-claim budgets, and the same cache and cross-refutation rules.
The legacy lane used order-10 development and its original round policy.

| Measure | Legacy | Frontier, fixed fitting data | Frontier, witness feedback |
| --- | ---: | ---: | ---: |
| Distinct attempts summed across seeds | 128/256 | 256/256 | 256/256 |
| Candidates refuted on final panel | 30/62 | 0/51 | 0/50 |
| Final survivors summed across seeds | 32 | 51 | 50 |
| Distinct final survivors across seeds | 5 | 7 | 8 |
| Distinct final survivors after implication deduplication | 4 | 5 | 6 |

All 24 development reports replayed identically. The order-11 seed
refuted all nine previously missed statements in one active evaluation
each. The frontier comparison measures the combined order and round-policy
changes. Within the two new lanes, witness refitting increased cross-seed
diversity and yielded nearly the same per-slot survivor count.

## Component stress and certified clique bounds

Use `--profile frontier-v3 --development-order 11` to test disjoint
five-cycles and use the newer certified novelty bank. The disconnected seed
can enter active search at order 10 when a cheap invariant bound allows a
violation. The active budget still accounts for each exact graph evaluation.
The two cycles refute `n - independence - matching <= 1` under the
triangle-free premise. Their order is 10, and both their independence and
matching numbers are 4. Verified development witnesses follow the usual
feedback and cross-refutation rules.

The `v8` retrieval index adds two reusable estimates for finite graphs.

- `2 * clique - triangles <= 5` counts triples in a maximum clique.
- `2 * chromatic - clique - n <= 0` colors a nonadjacent pair with one
  additional color after inducing on the remaining vertices.

Use `graph-prove --retrieve-lemmas 5 --retrieval-index v8` for an individual
claim, or `graph-discover-universal --proof-profile clique-bounds` for a
compositional proof dispatch. The frontier uses these same two Lean-checked
bounds in its novelty fact bank. On replay of the eight prior survivors,
the two bounds verified four statements across the unrestricted and
connected scopes. The disconnected witness resolved one more statement.
Three remained unresolved at the original 25-second Lean budget.

Historical profiles retain their recorded novelty and search settings.

## Decomposition proofs and integer rounding

Use `--profile frontier-v4` to include the two decomposition bounds in
the certified novelty bank during feedback campaigns. This profile keeps
the component seeds, witness replay, and final order separation of
`frontier-v3`.

- For triangle-free graphs, `chromatic - matching <= 1`. The proof removes
  a vertex with its neighborhood, adds a disjoint matching edge, and uses
  one additional color for the independent neighbors.
- For connected graphs, `2 * chromatic - edges + n <= 6`. The proof uses
  the minimum degree of a smallest induced subgraph requiring the full
  chromatic number. Its excess edges are bounded by those beyond an
  ambient spanning tree. Composition with `clique <= chromatic` gives
  `2 * clique - edges + n <= 6` under the same premise.

Use `graph-prove STATEMENT --retrieve-lemmas 5 --retrieval-index v9` or
`graph-discover-universal --proof-profile decomposition`. The `v9` index
can combine integer bounds to prove a positive multiple of a target
strictly below the next integer. For example, in a connected graph the
bounds on `2 * clique - edges + n` and `n - edges` sum to
`2 * (clique - edges + n) <= 7`. The unscaled conclusion is
`clique - edges + n <= 3`. The proof record includes the multiplier.
Composition, retrieval, and rounding share the configured search-node
limit, and Lean checks the original unscaled theorem.

Run the same frozen 32-case proof and refutation regression for either
index with `scripts/benchmark_graph_competition.py --proof-index v7` or
`--proof-index v9`, supplying a fresh output directory for each.
