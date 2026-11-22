# Active graph refutation

`axiom graph-active-refute statement.json --budget 1000` runs
`portfolio-v2` by default. An optional second positional argument supplies
a JSON array of explicit seed graphs. Supplied seeds are evaluated first.
Use `--profile mutation-v1` with a seed file to reproduce the original search.

The portfolio tests structured graphs across all four supported premises.
These include cliques, stars, clique unions, barbells, complete multipartite
graphs, circulant graphs and odd cycle blow-ups. It then interleaves edge
toggles and vertex edits with structural moves such as adding a universal
vertex, cloning a vertex's neighborhood, taking the complement and applying
the Mycielski construction where applicable. Each distinct labelled graph
charged to the search consumes one evaluation, including proposals that
fail the premise. The independent witness checker validates the premise,
all invariants and the strict violation using exact enumeration.

The witness can be passed to `axiom graph-prove --external-witness`.
The search and exact witness checker support finite simple graphs through
order 12. A result of `NO_REFUTATION_OBSERVED` reports the outcome of a
bounded search.

## Equal-budget comparison

Both profiles used the same input panel and a beam of eight, with each
successful witness independently replayed. Evaluation totals include cases
that exhausted the budget. These figures compare AXIOM's profiles.

| Suite | Seed | Budget per claim | Mutation v1 | Portfolio v2 | Evaluations, v1 → v2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen historical | 1729 | 1,000 | 90/100 | 100/100 | 15,012 → 2,619 |
| Frozen historical | 2718 | 1,000 | 90/100 | 100/100 | 15,107 → 2,619 |
| Frozen historical | 2718 | 64 | 79/100 | 97/100 | 2,755 → 2,583 |
| Census challenge | 1729 | 1,000 | 47/48 | 48/48 | 15,448 → 2,612 |
| Census challenge | 2718 | 1,000 | 47/48 | 48/48 | 14,364 → 2,600 |
| Census challenge | 2718 | 64 | 19/48 | 41/48 | 2,660 → 2,668 |

The census challenge contains 12 inequalities per premise. Each was
tightened using all graphs through order five and the common seed panel.
An exact counterexample from a sampled nauty 2.9.3 stream of order seven
through nine labels each case. The fixture records stream parameters and
hashes. The benchmark confirms each label before timing and passes only
the statement and common seed panel to the search. A separate regression
test searches 24 known implications and expects zero witnesses.

## Shared-objective comparison with AutoGraphForge

At AutoGraphForge commit `4d1a8afc99447cacd2328cca20e47b6493e8dbc5`,
the comparison runs its cross-entropy, variable neighborhood, simulated
annealing and Monte Carlo tree search through the same exact objective
and input panel as AXIOM. The order cap is 12, the seed is 1729, and the
budget is 1,000 distinct labelled evaluations per claim.

| Suite | AutoGraphForge heuristic search | AXIOM portfolio | Evaluations, AutoGraphForge → AXIOM |
| --- | ---: | ---: | ---: |
| Frozen historical | 97/100 | 100/100 | 11,476 → 2,619 |
| Census challenge | 38/48 | 48/48 | 21,724 → 2,612 |

The comparison isolates heuristic search. AutoGraphForge's native corpus,
SMT, reinforcement learning and production invariant evaluator are outside
this measurement. Its dispatcher had a five-second limit per claim and
no observed run reached that limit.

```bash
python -m pytest -q tests/test_graph_active_refute.py tests/test_graph_large_witness.py
PYTHONPATH=src python scripts/benchmark_graph_active_refutation.py --frozen-100 --profile portfolio-v2 --output /tmp/historical.json
PYTHONPATH=src python scripts/benchmark_graph_active_refutation.py --census-challenge --profile portfolio-v2 --output /tmp/census.json
PYTHONPATH=src python scripts/benchmark_graph_refutation_searchers.py --autographforge /path/to/AutoGraphForge --output /tmp/searchers.json
```

The shared-objective comparison requires AutoGraphForge's search
dependencies. The run used PuLP 3.3.0 for GraphCalc compatibility.

## Claim-guided search

`axiom graph-active-refute statement.json --profile guided-v3 --budget 64`
uses inexpensive invariant bounds to decide which proposals to evaluate first.
Greedy cliques and proper colorings bound clique and chromatic numbers. The
complement gives independence bounds, and a greedy matching gives a lower
bound for matching number. The search prefers the first structured proposal
whose lower bound guarantees a violation. If none qualifies, it ranks the
structured proposals by their optimistic bound. A limited lookahead can also
bring a promising mutation forward while preserving the original mutation
order if no such candidate is found. Every returned graph still passes the
exact scorer and independent witness checker.

At 64 exact evaluations per claim, both profiles used the same seed panel
and beam. The ranking checks add work and are counted separately in the
`priority_evaluations` report field.

| Suite | Seed | Portfolio v2 | Guided v3 | Exact evaluations, v2 → v3 | v3 ranking checks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen historical | 1729 | 96/100 | 100/100 | 2,568 → 2,127 | 672 |
| Frozen historical | 2718 | 97/100 | 99/100 | 2,583 → 2,127 | 672 |
| Census challenge | 1729 | 42/48 | 48/48 | 2,616 → 1,600 | 1,130 |
| Census challenge | 2718 | 41/48 | 48/48 | 2,668 → 1,600 | 1,118 |

At 1,000 exact evaluations per claim, both profiles found every witness.
On the census challenge v3 used 1,639 exact evaluations per seed across
all 48 cases. In these runs it took about 0.62–0.69 seconds across a seed,
compared with 0.52–0.54 seconds for v2. The extra ranking work pays off
most at tighter exact-evaluation budgets. The default remains `portfolio-v2`.

For seed 2718 at the higher budget, v3's 148 witnesses came from 78 input
graphs, 67 structured proposals, two Mycielski mutations and one
universal-vertex addition. These counts describe where this search stopped
on these suites.
