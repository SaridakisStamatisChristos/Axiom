# AXIOM v0.9 — Graph-conjecture frontier and bounded counterexample discovery

## Research objective

The first **active mathematical exploration** milestone after the mathematical
evidence federation (v0.6–v0.8). A finite simple-graph statement *proved by
independent complete enumeration at exactly n=5* may motivate testing a
similar-looking statement at n=6 or n=7, but does NOT prove it at the larger
order.

AXIOM v0.9 derives a deterministic family of exact typed target statements,
replays original evidence, selects missing or under-tested targets, runs a
bounded falsification campaign against actual generated simple graphs, and
independently checks any discovered counterexample using the existing distinct
graph reference invariant engine.

## Evidence status contract

- Original n=5 proof: **PROVED_IN_SUPPORTED_FRAGMENT** at EXACT n=5 only.
- A target n=6/7 found false: **REFUTED**, with explicit counterexample graph
  whose independent checker verifies the claim fails.
- No counterexample found in a bounded n=6/7 search:
  **EXPERIMENTALLY_SUPPORTED**, never PROVED or FORMALLY_VERIFIED.
- Originality: **NOT_ASSESSED** until external literature review.
- Candidate selection excludes original target-order statements already
  REFUTED. Existing experimental targets are retested only if the new search
  budget is strictly larger than their previously recorded budget.
- Only nonvacuous n=5 proofs enter the candidate bank.
- Source report provenance is complete: exact source digest, original
  candidate ID and original certificate digest.

No cross-order implication is asserted. Experiments at n=6 and n=7 do not
establish a theorem for all graph orders. A future *separate* project may
expand exact independent finite-order proof verification to n=6, but v0.9
does not.

## Reproduction on Ubuntu / Linux Mint

From repository root with Python >=3.11:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'

    axiom graph-frontier-run \
      --target-order 6 --seed 42 --search-budget 256 \
      --output research/graphs/frontier_n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-audit research/graphs/frontier_n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-run \
      --target-order 7 --seed 42 --search-budget 256 \
      --output research/graphs/frontier_n7.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

    axiom graph-frontier-audit research/graphs/frontier_n7.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

The run writes a fully deterministic JSON report through atomic file
replacement. Its independent audit regenerates all source candidates,
replays every original source report, reruns every selected bounded graph
search from the same seed/budget and verifies every counterexample witness.

## Algorithm and complexity boundary

Let **F** be the number of distinct n=5 proven, nonvacuous (template,k)
families; **R** the count of distinct input campaign reports; **B** the
per-candidate bounded graph search budget (1..2048); **K** the number of
selected target candidates (<=200); **N** the target graph order (6 or 7).

Source ingestion uses each original audit (including finite-order exact proof
verification). New target sampling costs O(K*B) graph invariant evaluations
plus witness checks and source replay. The discovery graph-property oracle may
itself perform exponential subsets/colourings in N; this is small for N<=7
but is not a polynomial-time general graph oracle.

Candidate ranking is deterministic: entirely untested target statements
first, then previously experimentally supported targets with search budgets
below the current budget, with stable template/k ties. This heuristic is
not a novelty estimate, logical proof score, or calibrated scientific value.

The original v0.5 reports contain 21 distinct n=5 proven nonvacuous
(template,k) families in the preserved baseline+scale campaigns; 19 have
n=6 targets eligible at a 256-graph follow-up budget. These figures can be
re-derived from the reports and may change with different source sets.

## Verification and preservation

    pytest -q tests/test_graph_frontier.py
    pytest -q

GitHub CI .github/workflows/graph-frontier.yml runs source-bounded research
for both target orders on Python 3.11 and 3.13, independently audits the
resulting reports and uploads JSON evidence artifacts. The original graph,
knowledge-federation, formal-provenance and pinned Lean workflows continue
as mandatory release gates on the pull request.

All v0.1–v0.8 mathematical evidence is immutable; the new reports are
additional research artifacts.

## Next mathematical milestone

Evaluate whether a **separately justified, independently validated** n=6
exhaustive checker can expand the exact finite-order proof boundary beyond
n<=5. This requires proving coverage of ALL n=6 labelled simple graphs,
not simply the surviving 256 bounded samples.
