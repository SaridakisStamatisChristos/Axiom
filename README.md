# AXIOM v0.2 — Automated Mathematical Discovery Foundation

**AXIOM** is an executable, local-first, budgeted experimental-mathematics engine. Its research campaigns generate conjectures from deterministic grammars, look for exact counterexamples, attempt narrow algebraic proof strategies, independently check proof certificates, audit persisted evidence, and checkpoint every candidate in SQLite.

**Scientific interpretation:** A bounded search is not a proof. A `PROVED_IN_SUPPORTED_FRAGMENT` finding has a certificate checked by a separate, **stdlib-only** integer-polynomial checker, *not* by Lean, Rocq, or another formally verified kernel. `FORMALLY_VERIFIED` is never emitted. No AXIOM results have been established as mathematically novel. The v0.1 results remain preserved separately.

## Installation (Ubuntu / Linux Mint; Python 3.11+)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/SaridakisStamatisChristos/Axiom.git
cd Axiom
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest -q
```

**Optional:** No API keys, Z3, Lean, cloud services, Docker, GPU or network access is required for the core mathematical engine. SymPy is the only non-development dependency. Reproducibility comparison is most reliable under matching Python and SymPy versions.

## Conduct a fresh research campaign

```bash
axiom run --seed 42 --candidates 300 --domain mixed \
    --lower -8 --upper 8 --max-evals 289 \
    --db research/my_campaign.sqlite3 \
    --report research/latest_report.json

axiom audit-report research/latest_report.json
```

Use `--domain polynomial` for polynomial identities only or `--domain mixed` to include inequalities. `axiom run --help` shows all options. The campaign is a foreground process. It **does not** continue running after exit.

## Checkpoint and deterministic resume

```bash
axiom run --seed 31 --candidates 120 --domain mixed --step-limit 20 \
    --db research/resume.sqlite3 --report research/resume.json
# Reuse the *same* database and identical configuration to continue:
axiom run --seed 31 --candidates 120 --domain mixed \
    --db research/resume.sqlite3 --report research/resume.json
axiom audit-report research/resume.json
```

SQLite checkpoints each candidate position transactionally. The engine version is part of the campaign identifier, so v0.2 records do not silently reinterpret v0.1 campaigns. Changing the seed, candidate count, bounds or domain creates a different campaign ID. Deterministic replay compares candidate/proof/witness records; elapsed time and RSS naturally vary.

## Independent certificate checking

Proof certificates contain canonicalized coefficient claims or restricted sum-of-squares decompositions, SHA-256 linkage to the complete original serialized statement, explicit quantified variables, and the method identifier. The standalone checker parses and recomputes both sides from the *original expression AST* without importing SymPy or the discovery engine.

```bash
python src/axiom/certificate_checker.py research/certificates/example_identity.json
python src/axiom/certificate_checker.py research/certificates/example_sos.json

# Same checks, via the installed CLI:
axiom check-certificate research/certificates/example_sos.json
```

Nonzero exit code means a malformed or unaccepted certificate. **Accepted** means checked in this explicit polynomial fragment; it does **not** mean formal Lean kernel verification. The checker and its algorithmic assumptions form a Python trusted computing base; see `docs/proof_semantics.md`.

## Mathematically supported fragments

- At most two universally quantified variables, `x`, `y`, with integer values in `ℤ`, and optional closed integer interval restrictions.
- Expression nodes: exact integer constants, variables, `add`, `sub`, `mul`, and `pow` with integer exponents 0–8.
- Relations: `==`, `>=`, `<=`. No divisions, floating-point equality, symbolic partial functions, arbitrary quantifiers, or unsafe cancellations.
- **Proof strategy 1 — coefficient identity:** recompute integer-polynomial coefficients on both sides. Equal coefficient maps establish an identity for all integer assignments, hence for any explicitly restricted interval.
- **Proof strategy 2 — quadratic sum of squares:** for selected univariate or separable multivariate quadratic inequalities, verify `M * target = constant + Σ weight_i * square_i²`, with `M > 0`, `constant >= 0`, and `weight_i > 0`. This establishes the signed inequality for all integers, not just for sampled values.
- All other inequalities receive only bounded-search evidence. An exhaustive search on a finite *sample window* is not a proof of a universal statement.

Proof and checker budgets limit work: at most 128 AST nodes per statement, 4,096 polynomial terms, degree 128, 4,096 coefficient bits, 200,000 coefficient-pair products per multiplication, and 16 square terms. Inputs beyond those limits are **unsupported** rather than implicitly proved. In addition, falsification allows at most 1,000,000 sampled grid points per candidate; counterexample minimization makes at most 64 extra probes. See the checker source for exact enforcement.

## Evidence and integrity

- **Refuted:** a stored integer valuation satisfies all original assumptions and falsifies the exact original AST, checked with a separate iterative evaluator. Minimization is bounded coordinate descent, **not** a globally smallest-witness guarantee.
- **Proved in supported fragment:** the exact persisted proof certificate is checked before promotion and rechecked when persisted records are restored.
- **Experimentally supported:** no witness found in disclosed search limits, but there is no accepted proof.
- **Unresolved:** no proof or counterexample established by supported methods.
- **Formally verified:** reserved for a future external trusted kernel; **zero** in v0.2.
- **Originality:** `NOT_ASSESSED` for all v0.2 results. Heuristic ranking is not a novelty score.

`axiom audit-report REPORT.json` replays deterministic generation and deduplication, compares all candidate statements, checks every proof certificate and counterexample, validates status histories and checks counts. Evidence tampering is rejected. This checks internal coherence, **not** external novelty or trusted-kernel formal verification.

## Executed research campaigns

| Release | Seed | Generated positions | Duplicates | Refuted | Supported-fragment proofs | Experimental | Formally verified |
|---|---:|---:|---:|---:|---:|---:|---:|
| v0.1 baseline | 42 | 300 | 159 | 89 | 49 | 3 | 0 |
| v0.2 campaign | 42 | 300 | 132 | 82 | 85 | 1 | 0 |

For v0.2, the full *executed* 300-position campaign uses `--domain mixed --lower -8 --upper 8 --max-evals 289` and is preserved in `research/v02_summary.json`, `research/v02_findings.ndjson` and the release archive (SQLite + JSON report). These are template-derived known-style relations, not original mathematical discoveries. Runtime measurements and runtime/tool versions are in the summary and `CHECKPOINT.md`.

## Source structure

- `src/axiom/mathematics.py`: typed AST, semantics, assumptions, canonicalization.
- `src/axiom/generation.py`: deterministic bounded conjecture templates.
- `src/axiom/verification.py`: symbolic normalization, certificate construction, falsification and witness minimization.
- `src/axiom/certificate_checker.py`: *standalone* restricted integer-polynomial certificate checker; Python stdlib only.
- `src/axiom/evidence.py`: persisted-result status and campaign report auditor.
- `src/axiom/research.py`: SQLite persistence, campaign checkpoints, metrics and reports.
- `src/axiom/__main__.py`: research, certificate, and report-audit CLI.
- `tests/`: deterministic, adversarial, mathematical, integration and subprocess verification tests.
- `docs/`: proof semantics, limitations, roadmap; `CHECKPOINT.md`: continuation information.

## Limitations and next objective

The generator is still a bounded template grammar, and mathematical deduplication is mostly structural; it is not general theorem invention. Counterexample minimization is local, not optimal. Proof methods exclude induction, nonpolynomial algebra, generic inequalities, Z3 and external proof assistants. An external Lean 4 verification integration, including actual compiler execution, dependency and axiom auditing, and artifact preservation, is the recommended v0.3 milestone. No asynchronous research scheduling is claimed.

**Preservation rule:** keep previous releases and research evidence intact; do not overwrite historical v0.1 results. Reproduce all claimed metrics and proof artifacts before advancing any version.
