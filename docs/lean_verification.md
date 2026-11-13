# AXIOM v0.3 Lean verification contract

## Statement interpretation

An AXIOM `Statement` denotes an integer theorem over variables `x` and/or `y`, with relations `==`, `>=`, or `<=` and optional integer interval bounds. Lean source translates each variable to `Int` and each bound `(x,lo,hi)` to a separate explicit assumption `(h : lo ≤ x ∧ x ≤ hi)`. Constants are always explicitly coerced to `Int`. Power exponents are natural literals bounded by the typed grammar. No division, quantifier alternation, user-supplied Lean tactics, or opaque strings are accepted.

## Certificate generation and backend

- **Candidate layer:** The v0.2 symbolic proof engine emits coefficient and sum-of-squares certificates. They are accepted only after exact independent replay in `axiom.certificate_checker`.
- **Translation layer:** `axiom.lean_backend.build_lean_source` produces a complete named Lean theorem with imports, exact assumptions, tactic script and `#print axioms` directive. The source is bound by SHA-256 to the original statement, and the certificate is separately SHA-256-bound to that same statement.
- **Compiler layer:** `lake env lean` executes with the pinned 4.35.0 project. Both `lean-toolchain` and `lakefile.toml` are checked, and the `lake-manifest.json` Mathlib commit is compared to the actual checked-out repository commit. Lean version and process exit status are recorded.
- **Dependency audit:** Only the empty axiom set or `{propext, Classical.choice, Quot.sound}` is accepted. Any `sorryAx`, custom axiom, unknown axiom, `native_decide` axiom, missing, or duplicate `#print axioms` report fails the verification gate.
- **Evidence layer:** Output records are separate from v0.2's existing SQLite campaign. `FORMALLY_VERIFIED` is set only upon authentic external success. Absent tools yield `LEAN_UNAVAILABLE`, not a theorem.

## Proof strategies

### Coefficient identity

The theorem is `(x : Int) (y : Int) ... : p = q`; the generated tactic is `ring`. It constructs a Lean proof in a commutative ring. The candidate must already pass the independent exact polynomial certificate checker. Lean success, not local normalizer success, determines formal verification status.

### Sum of squares

The local certificate witnesses `M * P = Σ(wᵢ * qᵢ²) + C` with strictly positive integer `M,wᵢ` and `C ≥ 0`, where `P` is `lhs - rhs` or `rhs - lhs` depending on inequality direction. AXIOM generates `sq_nonneg` hypotheses for each square, an equality `by ring` for the certified decomposition and the `nlinarith` tactic to close the integer inequality. If Lean cannot close the goal, it remains unverified even when the local certificate is mathematically sound.

## Adversarial gates

Refuse malformed statements, altered certificates, wrong proof method, missing executable, mismatched toolchain, missing or inconsistent Lake manifest, mismatched Lean version, timeout, nonzero compiler exit, stderr diagnostics, output over budget, missing/duplicate axiom declaration, disallowed transitive axioms and tampered input-source bindings. Test cases mocking a successful process exercise only Python control flow, not kernel soundness.

## Reproducibility

```bash
python3 -m pip install -e '.[dev]'
pytest -q
lake update && lake exe cache get
axiom lean-verify research/certificates/example_identity.json --project-root . --output research/lean_verified/identity.json
axiom lean-verify research/certificates/example_sos.json --project-root . --output research/lean_verified/sos.json
AXIOM_REAL_LEAN=1 pytest -q tests/test_lean_integration.py
```

GitHub workflow: `.github/workflows/lean-verification.yml`. Its actual job conclusion and attached source/evidence must be reviewed to claim a real proof. The static `research/lean_examples/*.lean` files are **generated, uncompiled examples** until proof checker execution succeeds.

## Known limitations

AXIOM's supported domain is deliberately narrow. Lean integration is optional and requires installing Mathlib. Proof source generation is deterministic; no automatic import from untrusted arbitrary Lean source exists. The adapter does not certify the entire reasoning engine and does not independently establish mathematical originality. Its offline `verify_record_integrity` API establishes internal record consistency, not a signed execution attestation.

## Verified real CI results (2026-11-13)

A genuine GitHub Actions runner executed [run 43342422453](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43342422453) (job `131613668932`, source commit `b49bf6dce45dcc663ca411c8a8ec6f77b363ad3c`). Its log records `attempted: 85, formally_verified: 85` after deterministic campaign reproduction, with no Lean checking failures, 3 successful real-Lean integration tests, and 43 Python tests passing at that commit. Actual Lean was `4.35.0`; Mathlib resolved git SHA was `56a005855ea17e0b0958f73ec801ae140b0a1679`; Lake manifest SHA-256 was `a19b8a2e5b1293ae2beadbc3ae84812adcdae07162ab07d2232d023da83841cd`. The successful run's uploaded evidence artifact ID is `13999333923` with digest `sha256:109813a97f370ff5fadd08e46ee8c88408f2e00568c30d2167aa5d9d74523300`.

The 85 source-bound JSON proofs, 85 theorem names, exact assumptions, transitive axiom dependencies, two sample Lean source files, and batch summary are preserved in `research/lean_verified/`. A deterministic NDJSON catalogue is at `research/v03_formal_results.ndjson`. Their candidate statements correspond to the audited original campaign (48 polynomial identities, 37 SOS inequalities). The original v0.2 SQLite proof statuses remain distinct from the v0.3 `FORMALLY_VERIFIED` external evidence records. No claim of novel mathematical discovery is made.

For exact internal integrity replay (not historical CI attestation):

```bash
axiom audit-report research/v03_campaign_report.json
axiom audit-lean-results research/v03_campaign_report.json \
    research/lean_verified/campaign --require-complete
```

The CI workflow includes both commands and adds a `--require-complete` gate after the full batch verification. Final release's Python suite has 44 local passes with 3 genuine Lean checks skipped only because the local environment lacks Lean.
