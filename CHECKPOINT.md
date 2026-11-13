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
