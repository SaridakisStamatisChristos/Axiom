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
