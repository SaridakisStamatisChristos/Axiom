# Held-out graph proof benchmark

The v1 suite contains 32 hand-authored affine statements, with eight in
each of the four supported premises. It has 24 proof challenges and
eight deliberately false controls. The challenges have no prescribed
outcome. The canonical statements differ from those in the existing
benchmark fixtures and the six historical discovery statements. Some
share mathematical families with previously known targets. The suite
measures transfer to fresh statements within those families and across
the supported premises.

The suite was committed before any benchmark proof or witness checks.
Its SHA-256 is
`70c5d5022b723f31942791d84c75735e5feda90415a4564d3282c151202e9a88`.
Each engine sees the same canonical input, up to three lemmas and
coefficient three for exact combination search, 10,000 search nodes,
one Lean invocation capped at 45 seconds, and exhaustive witness
screening through five vertices. The current profiles add up to five
retrieved lemmas, three synthesized lemmas, an order split, edge
induction and 16 tactic plans within the engine's limits. External
hints are disabled. The profiled runs are sequential, with a rotating
profile order. CLI timings include process startup, witness screening,
proof search and any Lean invocation. Evidence audits and independent
oracle checks run outside the timing interval.

The baseline is the original v0.21 release candidate as merged in
`f283c09`. The three current profiles use the same follow-up commit
`fa29880` and differ only in the retrieval index. Strategy attribution
records the successful pipeline stage and cited lemmas. The profile
comparison measures the effect of changing the index in that pipeline.

## Reproduce

From a checkout containing this benchmark, install AXIOM's development
dependencies and prepare the pinned Lean and Mathlib environment as in
the [core proof engine guide](core_proof_engine.md). Include
`Mathlib.Combinatorics.Hall.Basic` in the Mathlib cache download.

```bash
git worktree add --detach ../axiom-benchmark-v021 f283c09f5269470369e1c9695b5dbc978913b0b9
git worktree add --detach ../axiom-benchmark-current fa2988031c1431eefd6311e72cf6db139893e68d

python scripts/benchmark_graph_heldout.py \
  --baseline ../axiom-benchmark-v021 --current ../axiom-benchmark-current \
  --output ../axiom-heldout-evidence
```

The output directory must be new. It retains the input, generated Lean
source when available, proof attempt with checker logs and offline
audit for every case and profile. The summary includes the exact
resource limits, toolchain, outcome counts, timings, derivations and
counterexample witnesses. Two graph invariant oracles check every
labelled graph of orders zero through five for each statement.

## Measured results

The run used Python 3.12.14 on Linux x86-64, Lean 4.35.0, and
Mathlib `56a005855ea17e0b0958f73ec801ae140b0a1679`.
All 128 attempt records passed their version's evidence audit.
All 10 counterexamples agreed across profiles and with the independent
exhaustive check. They include all eight false controls and two
unlabelled challenges (C06 and T08).

| Engine and profile | Lean proofs | Counterexamples | Unresolved | Median CLI time | Worst CLI time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original v0.21 | 0 | 10 | 22 | 0.365 s | 0.566 s |
| Current, extended v1 | 2 | 10 | 20 | 3.127 s | 10.157 s |
| Current, structural v2 | 12 | 10 | 10 | 3.024 s | 3.545 s |
| Current, matching v3 | 14 | 10 | 8 | 3.026 s | 4.291 s |

All accepted proofs quantify over graphs of arbitrary order. The
strongest profile's proof paths and open cases break down as follows.

| Premise | Proved | Refuted | Unresolved |
| --- | --- | --- | --- |
| All graphs | A02, A04, A05 | A03, A06 | A01, A07, A08 |
| Bipartite | B01, B02, B04, B06, B08 | B03, B05 | B07 |
| Connected | C03 | C01, C05, C06 | C02, C04, C07, C08 |
| Triangle-free | T01, T02, T04, T06, T07 | T03, T05, T08 | |

- **Retrieval** finished ten proofs (B01, B02, B04, B06, B08, C03,
  T01, T02, T06, T07). The switch from v1 to v2 added ten proofs in
  the full pipeline. Switching from v2 to v3 added B04 and B08,
  both citing the retrieved Hall-based reverse inequality. B06 was
  already proved under v2 and also uses that inequality under v3.
- **Proof plans** finished A04 using the edge-induction bound and A05
  using a retrieved coloring bound. **Order splitting** finished A02
  with a retrieved matching bound. **Edge induction** finished T04
  alongside a retrieved triangle-free fact. These stages can share facts;
  the counts describe the finishing stage.
- The baseline exhausted its bounded composition search on all 22
  non-refuted statements. For the eight remaining v3 cases, Lean
  reported that the generated tactic plans exhausted their alternatives.
  Small-graph agreement leaves those statements unresolved.

Components occur in all eight remaining cases. A first reusable proof
target is `chromatic + components <= n + 1` (A07), obtained by
bounding the largest component's order and coloring each component
from the same palette. It would also supply the bound in B07 and,
with `clique <= chromatic`, explain A01. Any implementation should be
measured on a new suite once these cases inform development.
