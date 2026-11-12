# AXIOM v0.1 — Mathematical Discovery Foundation

AXIOM is a **local-first, reproducible experimental mathematics engine**. It autonomously generates bounded numbers of candidate statements about integer polynomials, searches for exact counterexamples, and certifies identities in a restricted, explicitly defined polynomial fragment.

**Evidence matters:** A bounded search is not a proof. `PROVED_IN_SUPPORTED_FRAGMENT` is an exact polynomial-coefficient identity checked by two separate normalization implementations (a sparse Python integer polynomial expander and SymPy `Poly(..., domain=ZZ)`). This is **not** `FORMALLY_VERIFIED` by Lean or another kernel. No theorem in v0.1 is presented as novel.

## Install (Linux Mint / Ubuntu / Python 3.11+)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
# after cloning this repository:
cd Axiom
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest -q
```

## Execute the autonomous research campaign

```bash
axiom run --seed 42 --candidates 300 --domain mixed \
    --max-evals 289 --db research/axiom.sqlite3 \
    --report research/latest_report.json
```

Alternative: `python -m axiom run ...` using the active virtual environment. Run `axiom run --help` for options. `--domain polynomial` tests only integer polynomial equalities; `--domain mixed` also includes bounded inequalities.

## Checkpoint and resume

The SQLite database checkpoints **each candidate position** in a transaction. To demonstrate interruption and resume:

```bash
axiom run --seed 31 --candidates 120 --step-limit 20 --db research/resume.sqlite3
axiom run --seed 31 --candidates 120 --db research/resume.sqlite3
```

Reusing the **same config and SQLite path** resumes the existing campaign. A different configuration derives a different campaign identifier. Duplicate candidates are rejected by canonical AST identity (commutativity of addition and multiplication; symmetry of equality). Uniqueness is **not** equivalence under all algebraic rewrites.

## Mathematical scope (v0.1)

- Scalar integer variables `x` and `y`, universally quantified over `ℤ`.
- Constants and total operations `+`, `-`, `*`, and `**n` for integer exponents `0 <= n <= 8`.
- Relations: equality, greater/equal, less/equal; integer interval bounds may constrain quantifiers.
- No division, fractions, floats, uninterpreted functions, arbitrary quantifier alternations, or symbolic denominator cancellations.
- For polynomial **equality** only: a zero coefficient-difference polynomial proves equality over all integer assignments. Nonzero polynomials are **not** automatically promoted to refuted without a confirmed witness.
- For inequalities: finite/range-limited testing only. Even exhaustive checking over a small interval is labeled `EXPERIMENTALLY_SUPPORTED`, never a universal theorem over `ℤ`.

All created results have an `originality` field (`NOT_ASSESSED` in v0.1), a status history, the exact serialized statement, optional counterexample, search budget, proof certificate, tool versions, and a transparent complexity-based ranking score. Ranking is **not** a claim of significance or novelty.

## Data outputs

- SQLite: `campaigns` and `findings`, with atomic progress cursor, generation provenance, status, search and proof evidence.
- JSON: full campaign record with generated unique candidates, exact witnesses, proof certificates, wall-clock measurement, RSS on Linux, versions, and counts.
- Checked-in baseline report: `research/baseline_summary.json` and `research/baseline_findings.ndjson` provide an auditable baseline with fully reproducible config.
- Benchmarks in `tests/` contain known mathematical identities and falsifiable relations; these are **not novel AXIOM discoveries**.

## Trust and limitations

The Python interpreter, SymPy polynomial implementation, and integer arithmetic are part of the execution trust base. The pure-Python normalizer is a second algorithmic cross-check, **not** a formally verified kernel. Z3 and Lean 4 are **not integrated** and no output is marked `FORMALLY_VERIFIED`. The generator is a narrow, seeded template grammar, not open-ended mathematical creativity. The CLI operates only while the process is running; it does not do research after the process exits. Time and memory limits are modest and large search spaces are capped. See `docs/proof_semantics.md` and `CHECKPOINT.md`.
