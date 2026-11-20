# Universal Lean graph proof dispatch

`graph-discover-universal` replays a committed discovery campaign and matches
surviving affine relations against a closed bank of kernel-checked lemmas.
Weighted integer terms, their signs, the relation operator, and the exact graph
premise are translated to a theorem quantified over arbitrary `n : Nat` and
`G : SimpleGraph (Fin n)`. The matcher uses integer normal forms and the same
exact bound implication as discovery filtering. A match selects a lemma.
Lean checks that the lemma entails the complete generated claim. Equality
requires a usable bound in each direction.

The semantics count edges and unordered triangle cliques, use Mathlib
independence and clique numbers, convert the finite chromatic number to a
natural, take maximum degree, maximize edge count over matching subgraphs,
and count the reachability quotient for components. The proof bank includes
clique versus chromatic number, the triangle-free neighborhood and degree
bounds, the connected component and edge bound, and clique versus triangle
count. The last uses the distinct triangles obtained by fixing two vertices
of a maximum clique and varying the third.

```bash
common=(--db science.sqlite3 --ledger discovery.sqlite3 --campaign first)
axiom graph-discover-universal "${common[@]}" > universal.json
axiom graph-discover-universal-audit "${common[@]}" --artifact universal.json
```

Supply the same legacy report flags used to populate the ledger. Dispatch
reuses the replayed observations and allocates no graph masks. The
ledger and nonuniform premise-aware sampler described in
[affine discovery](graph_synthesis_v018.md) remain the source of experimental
evidence. Proof and claim states are recorded separately from assessments
of mathematical novelty. Unsupported claims stay pending. A refuted claim
retains its replayed witness. An offline audit reconstructs source and
checks provenance fields. A live pinned Lean execution is the source of
kernel attestation.

CI archives the actual proof, its source and digests, the claim record and
the independently replayed campaign. The fixed-order commands and historical
artifacts are still available under their original formats.
