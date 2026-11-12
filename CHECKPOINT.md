# AXIOM — Verified continuation checkpoint

- **Release:** v0.2.0, 2026-11-13.
- **Canonical repository:** https://github.com/SaridakisStamatisChristos/Axiom (branch `main`).
- **Preservation:** v0.1 project files and historical baseline report remain unchanged in `research/baseline_*`. This checkpoint describes only v0.2. Full v0.2 SQLite/report and v0.1 database are in the release archive; GitHub also carries self-contained JSON/NDJSON evidence and sample proof certificates.
- **Status:** locally executable and tested. `pytest -q`: **31 passed**; deterministic fresh-database replay of 300-position campaign: **passed**; `axiom audit-report research/v02_campaign_report.json`: **passed**; standalone checker subprocess on identity and SOS examples: **accepted**.

## Implemented and tested

1. Typed exact integer-polynomial AST (x,y, total operators `const`,`var`,`add`,`sub`,`mul`,`pow`, exponent 0–8) with closed integer interval assumptions and relations `==`,`>=`,`<=`.
2. Deterministic expanded candidate templates; structural canonicalization, SQLite deduplication, and per-candidate transactional checkpoints with version-specific campaign IDs.
3. Boundary-first deterministic bounded falsification; independent iterative witness evaluation and bounded coordinate-descent minimization (up to 64 probes); search grid = intersection of explicit assumption intervals and configured test window.
4. SymPy and sparse-Python polynomial normalization before proof construction.
5. Sound proof strategy **coefficient identity** with a SHA-256-bound standalone certificate, rechecked using `src/axiom/certificate_checker.py` without SymPy or discovery imports.
6. Sound proof strategy **sum of squares** for selected separable quadratic integer inequalities, checked by exact polynomial coefficient equality and sign restrictions in the same independent certificate checker.
7. Separate evidence auditor `src/axiom/evidence.py`: validates allowed status traces, all stored proofs and witnesses on restore; full report auditor replays seeded candidate generation, deduplication, every bounded search, certificate checks and all counts.
8. CLI `axiom run`, `axiom audit-report`, `axiom check-certificate` and standalone checker invocation; tests for tampered certificates, forged status, modified search evidence, database proof corruption, bounds, false statements, randomized quadratic regression, checkpoint restore.

## Research campaign (executed, not simulated)

- Name: `integer_polynomial_discovery`; seed 42, domain mixed, 300 generated positions, search interval −8 to 8, max 289 tests per candidate.
- Generated positions: **300**; structural duplicates: **132**; unique investigated candidates: **168**.
- Supported-fragment proofs: **85** (48 exact coefficient-identity certificates, 37 SOS inequality certificates).
- Independently confirmed counterexamples/refutations: **82**.
- Experimentally supported, not proved: **1**.
- Universal Lean/kernel formal verification: **0**, not installed/executed.
- Replayed all 85 accepted v0.2 certificates with independent checker implementation and all 82 witnesses; tested standalone checker subprocess on two representative artifacts.
- Deterministic replay in a separate SQLite database produced equal candidate statements, proof artifacts, witnesses and status records.
- Measured initial campaign: **0.329021 s**, **911.8 generated positions/s**, peak Linux process RSS **135012 KiB**. Machine/software and environment are recorded in `research/v02_summary.json`. These are local measurements only, not cross-platform promises.
- Originality: **NOT_ASSESSED**; template-generated relations are not claimed as novel mathematical discoveries.
- Evidence on GitHub: `research/v02_summary.json`, `research/v02_findings.ndjson`, `research/certificates/example_identity.json`, `research/certificates/example_sos.json`. In release ZIP: `research/v02_campaign_report.json`, `research/v02_campaign.sqlite3`, and historical v0.1 SQLite + reports.

## Mathematical trust boundary and budgets

- `PROVED_IN_SUPPORTED_FRAGMENT` means locally checker-validated exact integer-polynomial certificate. This is **not** Lean, Isabelle/HOL, or Rocq formal verification. The standalone checker itself is not formally verified.
- Universal identity is decided via coefficient-map equality; SOS inequality is accepted only if `M*P = Σ(w_i*q_i²)+C` with **strictly positive** `M,w_i` and **nonnegative** `C` and the polynomial equality independently rechecked.
- No random experiment or bounded UNSAT result is treated as universal proof. All `FORMALLY_VERIFIED` counts are zero.
- Checker budgets: 128 AST nodes, polynomial degree <=128, <=4096 nonzero terms, <=4096-bit coefficients, <=200000 term-pair multiplication work, <=16 SOS terms. Search has <=100000 grid width and <=1000000 evaluated assignments per candidate; witness minimization bounded by 64 probes. Resource-bound cases are not claimed proved.

## Known limits / unresolved work

- Integer interval assumptions only; no arbitrary formula assumptions, induction, rational expressions, nonpolynomial algebra, or general theorem proving.
- Template-based grammar; candidate deduplication is structural, not complete polynomial-equivalence deduplication.
- SOS proof strategy is only sufficient for a narrow family of separable quadratics. True inequalities outside it are often unresolved or only experimentally supported.
- No Lean 4 or Z3 backend executed. No claim of mathematical novelty or literature validation.
- Global optimality of minimized witnesses not established. Persistent SQLite is local data, while GitHub stores text evidence; binaries are preserved in the release archive.

## Reproduction / next milestone

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
axiom run --seed 42 --candidates 300 --domain mixed --lower -8 --upper 8 --max-evals 289 --db research/new.sqlite3 --report research/new.json
axiom audit-report research/new.json
axiom check-certificate research/certificates/example_sos.json
```

**Next target: AXIOM v0.3** — optional **real Lean 4** adapter with actual installed compiler/kernel invocation, declaration/axiom dependency audit, `sorry`/admit rejection, version pinning, compiled proof artifacts, and intentionally negative integration tests. Do not change a candidate's status to `FORMALLY_VERIFIED` until an authentic trusted checker result is recorded. Continue preserving verified v0.1 and v0.2 releases.
