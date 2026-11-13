# AXIOM v0.5 — Finite Simple Graph Mathematics

## Precise mathematical fragment

A graph is a pair \(G=(V,E)\), where \(V=\{0,\ldots,n-1\}\), \(0\le n\le7\), and \(E\subseteq\{\{i,j\}:0\le i<j<n\}\). Graphs are undirected, simple, and labelled. Invalid edges, loops, multiple edges, unsorted serialization, out-of-range endpoints, and invalid vertex counts are rejected. Empty graph order zero is admitted; under the v0.5 convention it is **not connected** and has chromatic number zero.

The expression language is deliberately **closed**: `GraphStatement(n, template, k)` fixes an exact vertex count, one named relation from `graph_claims.TEMPLATES`, and an optional bounded integer parameter. An assumption such as `connected`, `tree`, `forest`, `bipartite`, or `triangle_free` narrows the graphs quantified over; `n` itself never remains free. A statement about five-vertex graphs is not a theorem about arbitrary graphs.

Exact invariants implemented: number of vertices/edges, vertex degrees, connected components, connectedness, forests and trees, bipartiteness, triangles, clique number \(\omega\), independence number \(\alpha\), chromatic number \(\chi\), and maximum matching number \(\nu\). Maximum-clique, independent-set, coloring and matching algorithms deliberately use exponential enumeration/backtracking and have a strict order cap rather than offering approximations silently.

## Vertex-isomorphism canonicalization

Every simple graph is represented by a bit mask indexed by ordered pairs \((i,j)\), \(i<j\). Canonicalization first partitions vertices into nondecreasing degree classes, then enumerates every permutation *within* the equal-degree blocks, and selects the lexicographically minimal relabelled adjacency encoding. Every isomorphism preserves degree. Conversely, all mappings between identically sized degree classes are included, making the resulting canonical code exact, not heuristic. The identity of vertices is not preserved by the canonical code, but the graph order is.

For \(n=0,1,2,3,4,5\), enumeration produced **1, 1, 2, 4, 11, 34** unlabelled simple graphs respectively. The complete labelled counts are \(2^{\binom{n}{2}}\). The discovery engine exploits these isomorphism representatives only when \(n\le5\), where every class is enumerated.

## Scientific evidence levels and trust boundary

1. `REFUTED` requires a concrete graph that satisfies the antecedent and independently violates the exact original claim; minimized examples are selected by edge count, then deterministic edge mask *within the structures explored*.
2. `PROVED_IN_SUPPORTED_FRAGMENT` requires order \(n\le5\), no discovered counterexample, and an accepted `axiom.graph.exhaustive_finite.v1` certificate. The separate checker re-enumerates **every labelled simple graph** of the specified order, uses a separate reference implementation of graph invariants, evaluates the same declared statement grammar, and confirms the exact number of graphs satisfying the antecedent. This is a mathematically complete proof for that **finite order only**. The certificate explicitly records vacuous implication instances.
3. `EXPERIMENTALLY_SUPPORTED` applies to no-witness sampled orders \(n=6,7\). A search of 128 or 2,048 cases out of a much larger graph space cannot prove a universal statement. For n>5 the proof checker unconditionally rejects certificates.
4. `FORMALLY_VERIFIED` is **not claimed for graph statements** in v0.5. The previous v0.3/v0.4 Lean proof records are preserved unchanged; a Python finite-domain checker is not a Lean kernel.

The two graph invariant implementations are intentionally separate: `graph_invariants.py` searches graph properties directly, while `graph_checker.py` reconstructs them using independent vertex-coloring, subsets, matchings and finite enumeration. Both use the `graph_claims.py` statement semantics; this shared declarative interpreter is part of the trusted mathematical specification. Tests inject false values into the discovery engine and confirm the certificate checker prevents false promotion.

## Reproducibility and computational budget

For each campaign, `graph_campaign.py` records a seed, candidate budget, graph-order cap, sampling cap, engine version, typed statements, deterministic duplicate keys, candidate provenance, counterexamples, proof certificates, status transitions and experiment timings. A SQLite WAL database checkpoints every generated position. On resume, persisted statements and proof evidence are rechecked against deterministic generation. `axiom graph-audit` regenerates the candidates and re-evaluates all evidence, independently checking finite certificates. Reports and the v0.5 local SQLite databases are saved under `research/graphs`.

Graph generator templates include both true and deliberately false known propositions, such as the handshake lemma, the bound \(\chi\le\Delta+1\), the false implication 'triangle-free implies bipartite', and the false claim \(\chi\le\omega\). A five-cycle is an explicit counterexample to the latter two. These are **benchmarks and template instantiations**, not mathematical inventions.

Seed 42, 240-position baseline (Python 3.13.5, single Linux process): 133 distinct statements, 107 duplicate positions, 102 fixed-order proofs (98 with nonempty antecedent coverage and 4 vacuous), 20 refutations, 11 experiments, 0 Lean graph proofs. The 700-position seed-2026 scale campaign produced 224 unique statements, 139 fixed-order proofs (133 nonvacuous, 6 vacuous), 50 refutations, and 35 experiments. Raw timings and peak resident memory are in the machine-readable reports. Results and rates are highly dependent on the selected small-graph grammar and should **not** be extrapolated to arbitrary graph-theory research.

## Additional finite combinatorics

The `graph_combinatorics.py` module computes the distribution of the number of edges among all labelled graphs of exact order n. It cross-checks the binomial formula \(\binom{\binom{n}{2}}{k}\) by independently enumerating all adjacency masks, for \(n\le5\). This is a known identity; the executable checker validates these **specific finite instances**, without claiming a Lean proof of the general binomial theorem.

## Reproduce

```bash
python -m pip install -e '.[dev]'
pytest -q
axiom graph-enumerate --max-order 5
axiom graph-count --max-order 5
axiom graph-run --seed 42 --candidates 240 --max-order 6 --search-budget 128 \
  --db research/graphs/replay.sqlite3 --report research/graphs/replay.json
axiom graph-audit research/graphs/replay.json
# Every fixed-order certificate is rechecked over all labelled graphs:
axiom graph-check-certificate research/graphs/examples/handshake_n5.json
```

The core is fully local and needs no external AI models, GPU, paid service, Neo4j, or Lean. For completeness and honest scope, no automatic general graph proof synthesis, arbitrary graph order, random-graph limit theorem, planarity proof, graph-embedding algorithm, or novelty assessment is claimed in this release.
