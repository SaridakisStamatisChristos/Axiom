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
