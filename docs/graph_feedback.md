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
