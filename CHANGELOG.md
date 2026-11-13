# Changelog

## 0.3.0 — 2026-11-13 — Lean 4 mathematical formal verification

- Real Lean 4.35.0 with Mathlib v4.35.0, pinned dependency and transitive axiom check.
- 85/85 generated known-template research certificates accepted by the actual Lean kernel in GitHub Actions [run 43342422453](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43342422453): 48 identities and 37 SOS inequalities; no new-mathematics originality claim.
- Individual proof source, compiler evidence, axiom list, configuration, Mathlib commit and CI provenance preserved; real Lean negative tests passed.
- New independent `axiom audit-lean-results` command validates complete correspondence with original regenerated research findings, with explicit non-authentication warning for detached JSON.
- Added regression tests, source generation audit and separate formal evidence archive; preserved v0.1/v0.2 SQLite states and artifacts unchanged.

## 0.2.0 — 2026-11-13

Independently replayable stdlib coefficient identity and sum-of-squares proof certificates; sound restricted complete-square inequalities; SHA-256 binding to original statements; strict evidence state-machine and persisted-record audit; `axiom audit-report` and `axiom check-certificate` CLI; bounded counterexample minimization; stronger mixed-domain deterministic grammar; new adversarial tests; executed v0.2 campaign and standalone proof artifacts. No external proof-assistant verification or novelty claims.


## 0.1.0 — 2026-11-13

Initial runnable local-first mathematical investigation pipeline. Typed integer-polynomial AST, seeded conjecture generator, exact bounded falsification, two agreement-checked coefficient normalizers, conservative status transitions, SQLite resume, CLI, baseline research report, automated mathematical tests. No Lean, Z3, or originality claims.

