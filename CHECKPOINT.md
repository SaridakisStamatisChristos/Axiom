# AXIOM — Continuation checkpoint

- **Release:** v0.1.0; 2026-11-13.
- **Status:** locally executed and tested; source and baseline reproducible.
- **Supported domain:** universally quantified one/two-variable integer polynomials, bounded integer inequalities, integer interval assumptions.
- **Allowed operators:** `const`, `var`, `add`, `sub`, `mul`, and integer `pow` with exponent 0–8. Comparisons `==`, `>=`, `<=`.
- **Proof procedure:** pure-Python sparse coefficient expansion and independent SymPy `Poly(..., domain=ZZ)` agreement. Proven statuses only `PROVED_IN_SUPPORTED_FRAGMENT`. **No Lean kernel or other external formal verification.**
- **Falsification:** deterministic boundary-first exact enumerator plus independent iterative witness evaluator.
- **Tests:** `pytest -q` **16 passed** (local execution). Covers exact large integers, known identities and non-identities, soundness gates, bounded evidence, assumptions, deterministic resumption, database consistency, malformed expressions, randomized algebraic identities.
- **Baseline campaign:** `axiom run --seed 42 --candidates 300 --domain mixed --max-evals 289 --db research/baseline.sqlite3 --report research/baseline_report.json`.
- **Observed baseline results:** 300 candidate positions; 159 rejected duplicates; 141 unique; 89 independently refuted, 49 proved in polynomial fragment, 3 experimentally supported, 0 formally verified.
- **Measured baseline:** 0.301678 seconds, 994.44 candidate positions/s and maximum process RSS 134128 KiB on Linux in the actual run (not a cross-machine performance promise).
- **Persistence:** SQLite transactions per position; see `src/axiom/research.py`, `research/baseline_summary.json` and `research/baseline_findings.ndjson`.
- **Versions:** Python 3.13.5 in execution runtime; exact SymPy version in baseline summary; pytest version via `pytest --version` when reproducing. Z3 and Lean were not executed or installed as AXIOM backends.
- **Originality:** not assessed; template benchmark patterns are known mathematical identities, not novel results.
- **Known defects / limits:** no independent standalone certificate kernel, no Lean/Z3 adapters, no general theorem proof search, incomplete algebraic equivalence deduplication, no counterexample minimization, maximum constants not capped by bit length, no external literature check.
- **Next milestone:** v0.2 independent proof certificate checker, explicit stronger evidence-state transition tests, expanded assumption reasoning and adversarial search.

## Resume

On Python 3.11+, run `python -m pip install -e '.[dev]'` then `pytest -q`. For a fresh baseline experiment use `axiom run --seed 42 --candidates 300 --domain mixed --max-evals 289`. The original baseline SQLite file is included in the downloadable archive; the GitHub repository preserves the full logical result set in NDJSON and a self-describing summary, from which reruns may be compared.
