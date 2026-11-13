# Changelog

## 0.2.0 — 2026-11-13

Independently replayable stdlib coefficient identity and sum-of-squares proof certificates; sound restricted complete-square inequalities; SHA-256 binding to original statements; strict evidence state-machine and persisted-record audit; `axiom audit-report` and `axiom check-certificate` CLI; bounded counterexample minimization; stronger mixed-domain deterministic grammar; new adversarial tests; executed v0.2 campaign and standalone proof artifacts. No external proof-assistant verification or novelty claims.


## 0.1.0 — 2026-11-13

Initial runnable local-first mathematical investigation pipeline. Typed integer-polynomial AST, seeded conjecture generator, exact bounded falsification, two agreement-checked coefficient normalizers, conservative status transitions, SQLite resume, CLI, baseline research report, automated mathematical tests. No Lean, Z3, or originality claims.

## v0.3 — Lean integration implementation

- Added deterministic AST/certificate-to-Lean theorem compiler for polynomial identities and SOS integer inequalities, preserving explicit quantified variables and bounds.
- Added real `lake env lean` execution adapter with Lean 4.35.0 and Mathlib v4.35.0 pins, actual manifest/checkout check, strict axiom dependency audit, source-hash evidence.
- Added individual and bounded audited-report verification CLIs with separate output records, no automatic promotion of v0.2 findings.
- Added dedicated GitHub Actions kernel job and negative real-Lean integration tests, plus adversarial local tests.
- Retained original v0.1/v0.2 research artifacts; local compiler unavailable and formal verification must be determined from actual CI run.
