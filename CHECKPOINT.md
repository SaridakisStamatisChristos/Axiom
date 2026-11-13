# AXIOM v0.6 — Active development checkpoint (13 November 2026)

**Based on verified main commit:** 119b1a72aa554ec50723e42aaab7df709923c2bf (v0.5). **Development branch:** axiom-v0.6-knowledge-graph. **Engineering state:** implementation and tests committed; CI review/promotion not yet claimed in this checkpoint.

## Added architecture

- src/axiom/knowledge_graph.py: deterministic materialization of typed campaign/statement/finding/search/proof/counterexample/checker/template-family nodes and provenance relationships into SQLite.
- Existing complete v0.5 graph reports are re-audited before import and replayed again during full-graph audits. An imported campaign is immutable and identified by its original campaign ID.
- Graph-order analogy relationships carry explicit non-entailment metadata. No generalization is claimed from fixed-order finite proofs. The existing graph Lean verification count remains zero.
- New commands: knowledge-build, knowledge-audit, knowledge-query, knowledge-neighbors; tests/test_knowledge_graph.py includes adversarial integrity checks.
- Graph database built by CI from both preserved reports is uploaded as a run artifact; the source research artifacts are not overwritten.

## Reproduce

```bash
python -m pip install -e '.[dev]'
pytest -q
axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
  research/graphs/v05_baseline_report.json research/graphs/v05_scale_report.json
axiom knowledge-audit --db research/knowledge/axiom.sqlite3
```

**Trust boundary:** v0.6 is an evidence index, not a generalized theorem prover. The current adapter only imports v0.5 graph reports; v0.1–v0.4 scientific and Lean evidence remains preserved separately. Mathematical originality NOT_ASSESSED.

---

# AXIOM v0.5.0 — Continuation checkpoint

**Release classification:** v0.5 graph research validated locally **and** in real GitHub CI on Python 3.11/3.13; v0.4 Lean proof evidence preserved unchanged. Graph finite-order proofs remain Python-checked, not Lean kernel-verified.

**Date:** 2026-11-13. **Repository:** https://github.com/SaridakisStamatisChristos/Axiom

## Actual new v0.5 capabilities

- Typed `SimpleGraph(n,edges)` domain for simple undirected graphs on exactly `n` vertices, `0<=n<=7`; strictly rejects malformed vertices, duplicate edges, loops, and invalid edge masks.
- Exact graph isomorphism canonicalization by degree-class permutation; exhaustive unlabeled simple graph classes for n=0..5: `1,1,2,4,11,34`.
- Exact graph invariants: degree sequence, edge count, components, connectivity, forest/tree, bipartiteness, triangles, chromatic number, clique number, independence number, matching number.
- Closed typed grammar of 25 finite-graph claim templates with explicit antecedents, known benchmarks, negative cases and optional bounded integer parameter k. Every graph statement quantifies over ALL simple graphs of **a fixed exact order n**, never freely over all n.
- Two intentionally independent invariant implementations; `graph_checker.py` checks concrete counterexamples and, for n<=5 only, enumerates **every labelled simple graph** to check a finite-domain proof certificate. The declarative claim interpreter is shared and is part of the trusted specification. Certificates have statement SHA-256 linkage, order, full labelled graph count, and coverage/vacuity metadata.
- For n=6,7, seeded explicit bounded sampling only, never proof. Counterexample minimization is within the enumerated/sampled graph set, not globally for sampled higher orders.
- SQLite candidate-per-position checkpoints, fail-closed persisted-evidence replay before resume, independent report audit, deterministic seed, deduplication, timings/RSS and version details.
- Finite combinatorial edge-count distribution `C(C(n,2), k)` compared against brute-force enumeration for each n<=5.
- New CLI: `graph-run`, `graph-audit`, `graph-enumerate`, `graph-count`, `graph-check-certificate`. Complete source semantics: `docs/graph_mathematics.md`.

## Executed local validation

- **Regression suite:** `117 passed, 6 skipped` on Python 3.13.5, Linux. The skipped cases are actual Lean-integrated tests gated by `AXIOM_REAL_LEAN`; no Lean is locally installed and no graph Lean results are asserted.
- **GitHub graph CI:** [run 43371399269](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43371399269), development commit `a2acb6d5b46df35ea7c39387ee9bb3f94aa641bc`, completed successfully in both Python 3.11 and 3.13 jobs. Each job reported **116 passed, 7 skipped** (the optional NetworkX test and six real-Lean integrations were unavailable); both independently replayed graph campaigns and the combinatorial count checks passed. The local Python 3.13 environment additionally had NetworkX, yielding **117 passed, 6 skipped**. The final release-builder manifest-collision regression was also tested locally.
- **Graph baseline** (seed 42; budget 240, max order 6, max sampled graphs 128): 133 unique / 107 duplicate; 102 finite-order proofs (**98 nonvacuous + 4 vacuous**), 20 independently verified refutations, 11 bounded experiments. 0 Lean graph proofs. Time 0.362387s, peak RSS 133336 KiB. Campaign ID `6df4269cf6caccee554e042f`.
- **Scale campaign** (seed 2026; budget 700, max order 7, sampled cap 160): 224 unique / 476 duplicate; 139 finite-order proofs (**133 nonvacuous + 6 vacuous**), 50 refuted, 35 experimental. Time 1.190172s, peak RSS 139360 KiB. Campaign ID `fc067ac1c4bf0f64403987e1`.
- Both full reports pass `axiom graph-audit`, both SQLite databases pass `PRAGMA integrity_check`.
- Independent invariant-reference equality checked for all labelled n<=5 graph masks, with additional random n=6,7 masks; count of n=5 isomorphism classes is 34. Explicit five-cycle refutations preserved.

## Exact proof epistemology

`PROVED_IN_SUPPORTED_FRAGMENT` means a Python checker completely enumerated the finite class of labelled simple graphs with **exactly n<=5** vertices for the given statement. It does not mean the result holds for any other n. Graph `FORMALLY_VERIFIED` count is **zero**: no Lean kernel has yet verified the new graph statements. A vacuous antecedent is recorded but should not be called an interesting discovery. The older v0.3/v0.4 algebra/number-theory Lean proof records remain preserved and unchanged; they are separate from these new graph findings. Mathematical originality remains `NOT_ASSESSED`.

## Local reproduction

```bash
python -m pip install -e '.[dev]'
pytest -q
axiom graph-enumerate --max-order 5
axiom graph-count --max-order 5
axiom graph-run --seed 42 --candidates 240 --max-order 6 --search-budget 128 \
    --db research/graphs/replay.sqlite3 --report research/graphs/replay.json
axiom graph-audit research/graphs/replay.json
axiom graph-run --seed 2026 --candidates 700 --max-order 7 --search-budget 160 \
    --db research/graphs/replay_scale.sqlite3 --report research/graphs/replay_scale.json
axiom graph-audit research/graphs/replay_scale.json
axiom graph-check-certificate research/graphs/examples/handshake_n5.json
```

## Preserved research artifacts

`src/axiom/graph_model.py`, `graph_invariants.py`, `graph_claims.py`, `graph_checker.py`, `graph_campaign.py`, `graph_combinatorics.py`; `tests/test_graph_*.py`; `research/graphs/v05_baseline_report.json`, `v05_scale_report.json`, `v05_summary.json`, `v05_baseline.sqlite3`, `v05_scale.sqlite3`, `research/graphs/examples/`; `.github/workflows/graph-research.yml`; the previous release archive and `research/lean_verified/` remain unchanged.

## Known open limitations and next milestone

- Only up to seven graph vertices; global finite exhaustiveness stops at five. Fixed-template search can rediscover known identities and refute known errors but cannot generate novel graph-theoretical concepts reliably. Exact graph algorithms are intentionally exponential.
- Certificate checker is an independent **Python** verifier, not a Lean kernel. The statement interpreter is shared and its correctness is trusted; a formalized graph model with independently kernel-checked finite certificates could be added later.
- No proof beyond the fixed-n finite fragment, no graph planarity proofs, graph minors, general induction, literature novelty assurance, or autonomous open-problem resolution.
- **Next target v0.6** — a cumulative graph-backed mathematical knowledge store with typed nodes/edges, provenance constraints, theorem dependency tracking, and source-bound lemma reuse, preserving all earlier verified artifacts.

---

## Preserved historical v0.4 checkpoint

# AXIOM v0.4.0 — Number Theory Laboratory continuation checkpoint

**Status:** **v0.4.0 VERIFIED RELEASE** — all 96 supported-fragment number-theory research proofs accepted by Lean 4.35.0 in the actual recorded CI run; recurrence certificates remain Python checked only.

**Date:** 13 November 2026. **Base:** verified v0.3 commit `f32a66977eb3e523aca75721e4bbcb4c16c53535`. **Development branch:** `axiom-v0.4-number-theory`; first source commit `193e5d6a1c5a310206e1d7de42c76a870cb27b97`; extended formal-audit commit `aeb077175c6c7fa9fa5b8bdac4494ebf616b77e7`.

## Current v0.4 verified capabilities

1. Typed `NTStatement` over one/two integer variables and exact polynomial syntax: `divides` and `congruent` (positive modulus only). Zero divides zero and never divides a nonzero integer. All bounds are explicit logical assumptions.
2. Autonomous seed-driven number-theory template generation, canonical deduplication, boundary-first finite counterexample search, independently checked witnesses and bounded minimization.
3. Sound *incomplete* exact divisibility proof procedure: SymPy polynomial quotient in `Q[x,y]`, accepted only when integer coefficients exist with zero remainder; independently reconstructed and checked using `axiom.number_theory_checker` (stdlib only). Congruence is proven as `m | (lhs-rhs)`. No general claim of completeness, and no finite testing promoted to proof.
4. SQLite persisted per-position checkpoints, reproducible reports, exact seed/configuration, replay audit and explicit statuses separated from originality.
5. Second-order integer linear recurrence module with exact state transition and certified eventual periodicity modulo m via first-repeated residue pair; independent finite-state checker. **Not Lean-verified.**
6. Lean 4 adapter for the supported integer-polynomial factor fragment: fixed source translation, explicit bounds, existential divisor witness plus `ring`, exact toolchain/Mathlib checks, transitive axiom audit and fail-closed statuses. Formal result records remain independent of local polynomial certificates.
7. Deterministic SHA-256 manifested release packager and regression tests.

## Actual local tests and experiments

- Local Python 3.13.5 / SymPy 1.14.0: **94 passed, 6 skipped**; 6 tests require an actual installed Lean kernel and are not counted as local Lean successes. Python 3.11 runner CI tests for the earlier source commit were successful.
- Primary seed 42 campaign: 300 positions; **205 unique**, **95 duplicates**, **95 refuted**, **96 locally proved in the supported factor fragment**, **14 experimentally supported**; **96/96 formally verified by the actual Lean 4 kernel**, preserved in separate records. Duration 0.300077s; RSS 134232 KiB. Campaign ID `5b29ff4fd4dbcd7b73bfc7b5`.
- Scaling seed 2026 campaign: 1000 positions, 516 unique, 484 duplicates, 211 refuted, 289 locally proved, 16 experimental; duration 0.745276s, RSS 138816 KiB. Campaign ID `1faabce84488e3baacba3388`.
- Recurrence seed 42 campaign: 40 independently certified eventual-periodicity statements, 12 with nonzero preperiod. Fibonacci mod 2 period 3 and mod 5 period 20 are known benchmarks.
- Both SQLite databases pass `PRAGMA integrity_check`; both experiment reports pass deterministic `axiom nt-audit`; sequence report passes `axiom nt-sequence-audit`.
- Initially completed Lean CI [43364305615](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43364305615) accepted 15/15 sampled number-theory proofs and rechecked 85/85 legacy v0.3 proofs; the first 15 proof records have been downloaded and source-bound audited.
- Expanded full Lean CI [43365165754](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43365165754) (job `131687747272`, source commit `aeb077175c6c7fa9fa5b8bdac4494ebf616b77e7`): **96/96 number-theory proofs accepted, 85/85 v0.3 algebraic proofs rechecked, and new evidence provenance audit passed.** Exact Mathlib SHA `56a005855ea17e0b0958f73ec801ae140b0a1679`; Lake manifest SHA-256 `a19b8a2e5b1293ae2beadbc3ae84812adcdae07162ab07d2232d023da83841cd`. Artifact ID `14010447259` with downloaded records individually audited, digest `sha256:547a4e746a5ffb0d7628be0617e591231f3129fa5e575394b08ea23e8cc7e3ea`.

## Mathematical and engineering boundaries

- Modular congruence requires strictly positive modulus in `[1, 2³¹]`; divisibility by zero uses `0|0` true and `0|nonzero` false.
- Polynomial quotient evidence proves a stronger identity in `Z[x,y]`, and therefore is sound for integer assignments. It is incomplete for integer-valued polynomial divisibility (e.g. `2 | x(x-1)`).
- Finite testing does not prove unbounded statements; candidate novelty has **not been assessed**.
- Recurrence checker relies on exact finite-state enumeration plus mathematical induction over deterministic transition equality; no separate Lean kernel checker has yet accepted these recurrence results.
- Lean proof validity depends on trusted AST→Lean semantics and the actual kernel, not on the generated tactic text alone. Offline JSON audits establish consistency, not historical CI attestation.
- Default maximum typed expression power 8, two integer variables, bounded denominators disallowed. No arbitrary Diophantine completeness, no independent mathematical originality claims.

## Reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
axiom nt-run --seed 42 --candidates 300 --lower -8 --upper 8 --max-evals 289 \
  --db research/nt_replay.sqlite3 --report research/nt_replay.json
axiom nt-audit research/nt_replay.json
axiom nt-sequence-run --seed 42 --budget 40 --report research/nt_sequences.json
axiom nt-sequence-audit research/nt_sequences.json
lake update && lake exe cache get # only after installing pinned elan/Lean/Mathlib
axiom nt-lean-verify-report research/nt_replay.json --project-root . \
  --output-dir research/nt_lean_verify --limit 96 --timeout 180
axiom nt-audit-lean-results research/nt_replay.json research/nt_lean_verify \
  --expected-attempts 96 --require-verified
```

## Next engineering target

AXIOM v0.5 — Combinatorics and Graph Mathematics: typed finite undirected simple graphs, exhaustive structure enumeration, graph-isomorphism canonicalization, invariant conjectures, independent counterexamples, and sound restricted graph proof/verification strategies. An additional number-theory proof enhancement may later introduce binomial-coefficient bases or modular induction for true integer-valued-polynomial divisibility beyond the `Z[x,y]` factor fragment.

---

## Preserved historical v0.3 continuation checkpoint

# AXIOM — verified continuation checkpoint (v0.3.0)

**Release:** AXIOM v0.3.0 — 13 November 2026.

**Repository:** https://github.com/SaridakisStamatisChristos/Axiom

**Last successfully executed external formal-verification campaign:** GitHub Actions run https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43342422453 — job `131613668932`, source commit `b49bf6dce45dcc663ca411c8a8ec6f77b363ad3c`. **85 attempted, 85 formally verified**; 3 real Lean integration tests passed. Originality remains `NOT_ASSESSED`.

## Verified features

- v0.1 core: typed integer polynomial AST, exact bounded falsification, seeded reproducible generation, SQLite checkpoints, CLI and deterministic tests.
- v0.2 core: independent stdlib polynomial coefficient and sum-of-squares certificate checkers; exact statement hashes, witness validation/minimization, adversarial evidence and report auditors.
- v0.3: exact AST/certificate-to-Lean translation, explicit quantified integer variables and optional bounds, ring and SOS tactics, actual compiler invocation, strict version/dependency checks, `#print axioms` proof dependency audit, fail-closed error statuses, persisted source-bound individual/batch formal evidence, CLI and genuine kernel-negative CI tests.
- Proof methods are restricted to integer coefficient identities and certificate-backed SOS inequalities; no claims about arbitrary number theory, induction, real analysis, topology, open problems or novelty.
- All 85 generated study results from the supported proof fragment have separate **real external Lean formal verification evidence**, without changing the original v0.2 SQLite statuses.

## Exact formal environment and evidence

- **Lean:** `leanprover/lean4:v4.35.0`, executed version 4.35.0; **Mathlib:** `v4.35.0`, actual checkout SHA `56a005855ea17e0b0958f73ec801ae140b0a1679`.
- **Lake manifest SHA-256:** `a19b8a2e5b1293ae2beadbc3ae84812adcdae07162ab07d2232d023da83841cd`.
- **CI:** run `43342422453`, job `131613668932`, source commit `b49bf6dce45dcc663ca411c8a8ec6f77b363ad3c` (**completed: success**).
- **Published GitHub Actions evidence artifact:** `13999333923`, SHA-256 `109813a97f370ff5fadd08e46ee8c88408f2e00568c30d2167aa5d9d74523300`. Artifact was retrieved and 85 individual source-bound records were independently replayed.
- **Results:** 48 verified identities, 37 verified SOS inequalities, 82 refuted candidates, 1 experimentally supported unproved inequality, 132 structural duplicate positions; 300 generated positions, 168 unique investigated findings.
- **Allowed actual reported axioms:** only `propext`, `Classical.choice`, `Quot.sound`, depending on theorem. No `sorryAx` or other unapproved axioms. No LLM-generated proof accepted by suggestion alone.
- **Python local tests (post-CI release):** `44 passed, 3 skipped` (the three real-Lean tests are gated and run on CI). The real CI's earlier source commit recorded 43 Python tests passing plus three genuine Lean integration tests passing, with the full 85-proof run accepted.
- **Local Lean availability:** Lean/lake absent from this working container; claims are grounded in actual CI run logs and artifact, not local mock execution.

## Reproducible campaign / checkpoints

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
axiom run --seed 42 --candidates 300 --domain mixed --lower -8 --upper 8 --max-evals 289 \
  --db research/replay.sqlite3 --report research/replay.json
axiom audit-report research/replay.json
# After elan, pinned Mathlib and cached mathlib installation:
lake update && lake exe cache get
axiom lean-verify-report research/replay.json --project-root . \
  --output-dir research/replay_lean --limit 85 --timeout 180
axiom audit-lean-results research/replay.json research/replay_lean --require-complete
```

The original v0.1/v0.2 research archives have been preserved. Source of truth for v0.3 is `src/axiom/lean_backend.py`, `src/axiom/formal_campaign.py`, `.github/workflows/lean-verification.yml` and this checkpoint. All 85 CI output JSON records live under `research/lean_verified/campaign/`, additionally indexed in `research/v03_formal_results.ndjson`, with machine-readable summary `research/v03_formal_results_summary.json`.

## Known defects / trust boundaries

1. Core integer grammar is deliberately restricted (up to two integer variables, powers 0–8, no divisions, partial functions, induction, arbitrary quantifiers).
2. Original proof certificates rely on a Python trusted computing base, while formal results rely on typed-translation correctness plus Lean kernel trust. Translation has not been itself formally proved semantics-preserving.
3. Offline JSON integrity auditing is not a cryptographic attestation of historical GitHub execution; externally accessible CI logs and checked-out source are necessary independent provenance.
4. Results are rediscoveries within a narrowly templated grammar. Mathematical originality has not been assessed.
5. CI pin is Lean 4.35.0 / Mathlib v4.35.0, but `lake update` resolves dependencies in the workflow; the resolved Mathlib checkout SHA and manifest hash are therefore recorded per actual run. Pin and audit dependency hashes for improved long-term reproducibility in future work.
6. CI job runtime/download/cache can be substantial. A formal verification is not implied by a partially completed job.

## Next milestone: AXIOM v0.4 — Number Theory Laboratory

Introduce typed divisibility, congruences and modular constraints with explicit zero-modulus policy, deterministic small-domain falsification, sound certificate/Lean proof strategies for supported fragments, and cumulative research evidence. Maintain all v0.3 85 proof records and rerun the current adversarial gates.
