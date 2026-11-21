# Core graph proof engine

The [frozen baseline](../research/proof_engine/baseline.json) dispatches one
lemma per inequality direction. Its documented [all-orders lemma bank](graph_universal_v020.md)
is separate from the historical n=3 and n=6 Lean checks. The v0.21.0rc1 candidate
extends proof construction while retaining all three paths and their scopes.

## From canonical JSON to an all-orders proof

With the repository's pinned Lean 4 toolchain on PATH, run these commands from
the repository root:

```bash
python -m pip install -e '.[dev]'
MATHLIB_NO_CACHE_ON_UPDATE=1 lake update
lake exe cache get Mathlib.Combinatorics.SimpleGraph.Acyclic \
  Mathlib.Combinatorics.SimpleGraph.Bipartite \
  Mathlib.Combinatorics.SimpleGraph.Matching
python - <<'PY'
import json
from pathlib import Path
from axiom.graph_relations import AffineRelation

claim = AffineRelation.normalized(
    {"matching": 1, "clique": 1, "edges": -1, "chromatic": -1}, 0)
Path("statement.json").write_text(json.dumps(claim.to_dict()))
PY
axiom graph-prove statement.json --project-root . \
  --max-lemmas 3 --max-coefficient 3 --max-nodes 10000 \
  --output proof_attempt.json --source proof_attempt.lean
axiom graph-prove-audit proof_attempt.json
lake env lean proof_attempt.lean
```

Input is a canonical integer affine inequality or equality over the nine
invariants in `graph_affine.VARIABLES`. The existing three-term bound schema
continues to represent the legacy grammar. A separate bound schema covers
proof-only shapes up to six nonzero terms. Each relation carries one premise
(`ALL`, `CONNECTED`, `TRIANGLE_FREE`, or `BIPARTITE`). Current search uses a
conditional lemma only if its premise matches exactly. The current bank has
no bipartite-specific lemma.

## Search and evidence

Search enumerates supports from smallest to largest, ordering lemmas by
theorem name and coefficients by increasing integer value. It prunes impossible
signed residuals and memoizes failed states. A certificate must match every
target coefficient exactly and imply an upper bound no greater than the
target's. Equality requires a certificate for both directions. In the worst case
a search of size `k` tries combinations on the order of `binom(bank_size,k) *
max_coefficient**k`. The node budget limits the aggregate work over the
directions and suffices for deterministic replay. Lean has a separate process
timeout. The search uses the existing bank and does not infer new lemmas.

The attempt carries source and statement digests, ordered integer terms and
lemma coefficients per direction, the configurations, original checker output
and the dependency revisions. `FORMALLY_VERIFIED` requires acceptance of
the whole generated theorem by Lean under the configured pins and a successful
audit for permitted axioms. The generated proposition quantifies over every
natural order and simple graph on `Fin n`; a conditional result also quantifies
over evidence for its premise. The checker and pinned environment are trusted
runtime inputs. Offline replay binds the proof source, trace, recorded streams
and claim together. It cannot attest past execution or authenticate a fully
replaced evidence package. Use the original CI run and archived artifacts or
rerun Lean on the exact source.

Counterexamples are sought in increasing graph order and edge-mask order
through n=5 by default and cross-checked with a second graph-invariant oracle.
`COUNTEREXAMPLE` carries a witness. `SEARCH_EXHAUSTED` means the finite
combination search did not derive the claim. `UNSUPPORTED` indicates an input
outside the typed proof grammar. `LEAN_UNAVAILABLE` and `LEAN_REJECTED` carry
separate environment or checker diagnostics. Novelty is recorded independently.

## Optional pinned Mathlib lemma retrieval

Add `--retrieve-lemmas K` to `graph-prove` to opt in, with `K` from 1
through 32. The first pass uses the existing bank. If it finds no derivation
and leaves nodes in the budget, the second pass retrieves up to `K` adapters
and reuses only those remaining nodes. Applicable adapters are ranked by
exact direction, signed term overlap, sparsity, and stable theorem name.
The index contains curated affine adapters to declarations at the pinned
Mathlib revision. Coverage currently includes bounds on clique number,
independence number, chromatic number, maximum degree and bipartite colorings.

The versioned proof record includes the index digest, ranked selections,
Mathlib declaration names, and the initial derivation when fallback runs.
Only selected adapters used in the certificate appear in the generated
source. Lean checks each emitted adapter and the final all-orders statement.
Offline audit replays the selection and verifies the artifact's integrity.
Existing attempts without the option retain their original schema and source.

Run `python scripts/benchmark_graph_retrieval.py --output retrieval-benchmark`
after installing pinned Lean. The benchmark compares the fixed bank and
retrieval on five frozen composite goals, retains both modes' proof records,
and cross-checks the statements with two small-graph oracles.

## Optional intermediate-lemma synthesis

Add `--synthesize-lemmas K` to `graph-prove` to try up to `K` synthesized
lemmas after the enabled search stages exhaust their candidates. It uses
applicable fixed-bank lemmas and any adapters selected by the optional
Mathlib retrieval stage. For each parent pair with opposite signs on a
shared invariant, it computes positive integer multipliers that eliminate
that invariant. The remaining coefficients are divided by their GCD and the
right-hand side is rounded down because the invariants are integers.

The engine ranks the projected bounds, retains the strongest for each
coefficient vector, and retries composition within the remaining node
budget. This is one projection layer. Certificates name the two original
parents, their multipliers, the eliminated invariant and the normalization
divisor. Generated Lean source proves each used projection from its parents
before proving the original goal. Offline replay checks the ancestry.
Existing v1 and v2 attempts retain their source and record formats.

```bash
axiom graph-prove statement.json --retrieve-lemmas 5 --synthesize-lemmas 3
python scripts/benchmark_graph_retrieval.py --synthesis --output synthesis-benchmark
```

The synthesis benchmark compares retrieval alone with retrieval followed by
projection on four frozen composite bounds. The final proof search uses the
same default three-lemma limit in both modes. Its output retains the
original statement, both attempt records, Lean source and the two-oracle
bounded check.

## Optional graph-order case splitting

Add `--split-order` to try one partition into `n = 0` and `n > 0` after
the enabled proof searches exhaust their candidates. The positive-order
search uses the remaining node budget and can apply bounds that need a
nonempty vertex type. Lean proves the empty branch from zero-valued
invariants or from the fact that a connected graph has a vertex. Lean then
checks both branches of the original universally quantified statement.

The v4 attempt records whether the partition ran, the prior derivation,
the positive-order facts used, and the empty-branch strategy. Offline
audit replays the search and checks the generated source. Counterexample
search still runs before any proof search.

```bash
axiom graph-prove statement.json --retrieve-lemmas 5 --synthesize-lemmas 3 --split-order
python scripts/benchmark_graph_retrieval.py --order-split --output order-split-benchmark
```

The benchmark compares the same retrieval and synthesis settings with
case splitting disabled and enabled on six frozen graph bounds, archives
the attempts and checked source, and checks each goal against two
small-graph oracles.

## Optional edge-count induction

Add `--induct-edges` to retry within the remaining node budget after the
enabled fallbacks. It adds one general-purpose bound, `n ≤ edges + independence`,
to the affine search. Lean proves it by strong induction on the number of
edges. With no edges all vertices form an independent set. Otherwise, delete
one edge, apply the induction hypothesis to the smaller graph, and discard
one endpoint from its maximum independent set to obtain an independent set
of the original graph.

The engine can combine this bound with fixed or retrieved lemmas, synthesized
bounds, and local case facts when order splitting is enabled. It emits the
induction proof only if the final derivation uses the bound. The v5 record
includes the preceding search and the selected induction fact. The offline
auditor regenerates the same source and checks its digest. The induction
rule is specific to this bound on finite simple graphs.

```bash
axiom graph-prove statement.json --retrieve-lemmas 5 --synthesize-lemmas 3 --split-order --induct-edges
python scripts/benchmark_graph_retrieval.py --edge-induction --output edge-induction-benchmark
```

The benchmark keeps the earlier fallbacks enabled in both modes. It archives
the exact statements, proof records and checked Lean source, and cross-checks
the targets with two independent small-graph oracles.

## Optional Lean proof-plan search

Add `--proof-plans K` (1–16) after the existing fallbacks. AXIOM tries
`omega` on the goal alone, then ranked bundles of facts from the enabled
proof stages. Bundles draw from at most seven eligible facts and respect
`--max-lemmas`. The remaining search-node budget also caps how many plans
are emitted. The earlier coefficient cap applies to exact composition.
Lean's arithmetic tactic can combine facts with other coefficients and
use the nonnegativity of natural-number invariants. A plan that uses a
positive-order fact proves both graph-order branches.

Lean tries the plans in one invocation under the existing timeout. A
plan must close every goal to reach its trace marker. The v6 record keeps
the ordered plans, the accepted index from the checked Lean log, and the
exact generated source. Offline audit regenerates that source and checks
the index against the recorded log. Exhausting all plans yields a Lean
rejection. The ordinary counterexample search still runs first.

```bash
axiom graph-prove statement.json --retrieve-lemmas 5 --synthesize-lemmas 3 \
  --split-order --induct-edges --proof-plans 16
python scripts/benchmark_graph_retrieval.py --proof-plans --output proof-plan-benchmark
```

The benchmark compares the same earlier fallbacks with and without tactic
plans and retains both attempts, checked source, and two-oracle graph checks.

## Optional external proof hints

Use `--proof-hint-context` with the desired proof options to export the
statement, eligible fact names and coefficient vectors, local or global
scopes, and a response template. This option does not invoke Lean. An
external model or a person can fill the template's `plans` array with
ordered suggestions. Each suggestion is an array of eligible fact names.
Keep the template's schema and statement digest intact.

```bash
common=(--retrieve-lemmas 5 --synthesize-lemmas 3 --split-order --induct-edges --proof-plans 2)
axiom graph-prove statement.json "${common[@]}" --proof-hint-context --output context.json
axiom graph-prove statement.json "${common[@]}" --proof-hints hints.json --output attempt.json --source attempt.lean
axiom graph-prove-audit attempt.json
python scripts/benchmark_graph_retrieval.py --proof-hints --output proof-hint-benchmark
```

AXIOM reserves the first plan for arithmetic alone, then tries eligible
hint bundles, then fills remaining slots with ranked plans. Hints can displace ranked plans within
the same cap. It records unavailable facts, over-budget bundles and
duplicates, and uses only its own templates to generate Lean. The v7
attempt stores the input, rejected proposals, and the mapping from
scheduled plans to hint indices. Lean checks the original statement under
the same timeout and axiom policy. AXIOM runs this interface offline.

The benchmark compares three frozen suggestions against ordinary
two-plan search. It tests whether suggestions can improve a tight budget
on those goals.

## Discovery and benchmark

Use a source database built by the reconstruction step in
[the existing synthesis workflow](../.github/workflows/graph-synthesis-v018.yml).
The beam preserves the old candidate lane and ranks additional three- and
four-term statements on training data. It evaluates training-derived
expressions and general pairwise sums from the certified bank. The latter are
proof opportunities. Selection is complete before the sampler allocates any
new holdout graph. Replayed provenance includes the campaign, the historical
source and training digests, the exact selected statement and checked masks.

```bash
DB=research/knowledge/axiom.sqlite3
LEDGER=research/knowledge/discovery.sqlite3
axiom graph-discover --db "$DB" --ledger "$LEDGER" \
  --campaign proof-engine-v021 --proof-beam 8 --holdout-budget 8 --max-candidates 2
axiom graph-discover-universal --db "$DB" --ledger "$LEDGER" \
  --campaign proof-engine-v021 --compose > discovery_proof_report.json
axiom graph-discover-universal-audit --db "$DB" --ledger "$LEDGER" \
  --campaign proof-engine-v021 --compose --artifact discovery_proof_report.json
python scripts/benchmark_graph_proof.py --output proof-engine-benchmark
```

`KNOWN_OR_DERIVABLE_PROOF_TARGET` and `OPEN_PROOF_TARGET` label selection
queues. An open target can be an established theorem and needs prior-art
review before any novelty claim. The benchmark records the legacy grammar
restriction, actual kernel outcomes, independent exhaustive small-graph checks,
witnesses, and timings with their distinct measurement scopes. See the
workflow's retained artifacts for the execution and replay evidence.

### Run the extended engine on a campaign

`--proof-profile extended` uses retrieval (5), synthesis (3), order
splitting, edge induction, and up to 16 Lean plans on the campaign's
audited statements. It uses the same selected statements and witnesses as
`--compose`. The v2 report records the profile, timeout, optional hints,
and each proof attempt. The audit command identifies the report format and
checks that every attempt used the reported configuration.

```bash
common=(--db "$DB" --ledger "$LEDGER" --campaign proof-engine-v021)
axiom graph-discover-universal "${common[@]}" --proof-profile extended > extended.json
axiom graph-discover-universal-audit "${common[@]}" --artifact extended.json
```

To supply hints, wrap one or more statement-bound hint files in a manifest
with schema `axiom.graph_campaign_proof_hints.v1` and a `hints` array.
Each entry uses the single-statement schema described above. Pass the
manifest with `--proof-profile extended --proof-hints campaign-hints.json`.
Each entry must match a distinct selected statement digest. Entries affect
only proof attempts after campaign selection and holdout replay.
