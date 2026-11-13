# AXIOM v0.4 Number Theory — Reproducible Research Ledger

## Classification and interpretation

This ledger describes **executed mathematical experiments**, not mathematical
novelty. The generator explores pre-defined templates of integer-polynomial
relations. Its numerical throughput is not a measure of independent theorem
discovery. Local certificate checking and Lean kernel checking are distinct.

## Baseline campaign

- Campaign: `elementary_number_theory` (engine `0.4.0`).
- Configuration: seed `42`, `300` candidate positions, global search range
  `[-8,8]` per variable, `289` evaluations per unique candidate.
- Campaign identifier: `5b29ff4fd4dbcd7b73bfc7b5`.
- Outcomes: `205` unique statements, `95` duplicate positions,
  `95` independently revalidated refutations, `96` standalone checked
  integer-polynomial-factor identities, `14` experimentally supported
  statements with **no universal proof**.
- Local execution measurement (Python 3.13.5 / SymPy 1.14.0): `0.300077 s`,
  approximately `999.74` candidate positions/second, process high-water
  RSS `134232 KiB` as reported by `resource.ru_maxrss` under Linux.
- Data: `v04_baseline.sqlite3`, `v04_report.json`,
  `v04_findings.ndjson` and example certificates.
- Audit: `axiom nt-audit research/number_theory/v04_report.json` passed.

## Scale campaign

- Seed `2026`, `1000` candidate positions, range `[-8,8]`,
  `289` evaluations, separate SQLite database.
- Campaign identifier: `1faabce84488e3baacba3388`.
- Outcomes: `516` unique statements, `484` duplicates, `211` refutations,
  `289` locally certified factor identities, `16` experimentally supported.
- Local execution: `0.745276 s`, about `1341.78` positions/second,
  process high-water RSS `138816 KiB`. Throughput is specific to this
  cache, seed, workstation and very small expression grammar.
- Audit: `axiom nt-audit research/number_theory/v04_scale_report.json` passed.

## Finite-state recurrence campaign

- Seed `42`, budget `40`, second-order integer linear recurrences,
  positive moduli `1..64` (generated range narrower).
- Outcomes: `40` independent, exact transition-checker-accepted eventual
  modular-periodicity certificates. `12` required nonzero preperiods.
- Known benchmarking facts rediscovered: Fibonacci period modulo 2 is 3,
  modulo 5 is 20, both with preperiod 0.
- Audit: `axiom nt-sequence-audit research/number_theory/v04_sequences.json`
  passed. No recurrence certificate has a Lean check in v0.4.

## Formal verification

The repository includes a separate Lean 4.35.0 adapter for certified integer
polynomial divisibility and congruences. The **baseline experiment's local
96 proofs are not automatically formal proofs**. Only accepted Lean execution
records, with matching source SHA and dependency/axiom metadata, can receive
`FORMALLY_VERIFIED` status. Actual GitHub Actions [run 43365165754](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43365165754) verified **96/96** number-theory research proofs with Lean 4.35.0, rechecked 85/85 v0.3 algebraic theorems, and accepted all formal-provenance audits. Exact files are in `research/lean_verified/number_theory/`, `v04_formal_results.ndjson`, `v04_formal_results_summary.json` and `CHECKPOINT.md`. These are template-generated known results, not original theorems.

## Known limits

- Only one/two integer variables, exact polynomial operations and powers
  0–8, positive congruence modulus; no general number-theoretic induction.
- Polynomial factor witness is a sound but incomplete divisibility rule.
  For example `x(x-1)` is divisible by 2 for all integers `x`, but the
  quotient is not a polynomial in `ℤ[x]`, so this method alone cannot prove it.
- A negative bounded search cannot prove a universally quantified claim.
- Finite-state recurrence certificates rely on an independently reviewed
  standard-library checker and a straightforward deterministic-transition
  proof argument, not on Lean.
- No originality or publication-readiness assessment has occurred.
