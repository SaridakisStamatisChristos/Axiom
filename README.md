# AXIOM v0.13 — Source-Bound Exact Graph Proof Knowledge (development)

AXIOM now preserves independently checked **exact n=6 finite certificates**
and refutations in the same SQLite mathematical research laboratory as
the earlier historical proof graph, four-domain federation, original
Lean metadata and n6/n7 bounded experimental frontier.

Importing the exact reports cannot silently alter older findings.
The new source-replay knowledge overlay cross-checks exact-n6 statements
against any previously recorded bounded frontier findings of exactly the
same statement and graph order. A valid counterexample is never overwritten
by a supposed proof, and bounded survival does not count as a proof.

    axiom knowledge-exact-n6-import --db research/knowledge/axiom.sqlite3 \
      research/graphs/n6_exact_report.json
    axiom knowledge-exact-n6-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-exact-n6-query --db research/knowledge/axiom.sqlite3 \
      --status PROVED_IN_SUPPORTED_FRAGMENT

All exact n6 certificates remain finite **Python independently checked**
results, not universal all-order theorems or Lean kernel verification.
See [v0.13 source-bound evidence documentation](docs/knowledge_exact_n6.md).

---

# AXIOM v0.12 — Independently Checked Exact-Order-Six Graph Proofs (development)

AXIOM v0.12 extends the **exhaustively checked finite graph proof boundary**
from five to **six vertices** for seven structural graph templates.
Every certificate now covers **all 32,768 labelled simple graphs at exactly
n=6**, using a primary discovery evaluator and an independently implemented
bitset/BFS verifier. Two deliberately false structural claims are included
as counterexample controls.

These are known mathematical results, not original discoveries; the new
contribution is runnable exhaustive checking, independently auditable proof
artifacts and precise exact-order evidence. No all-order theorem or new Lean
kernel proof is claimed.

    axiom graph-n6-run --output research/graphs/n6_exact_report.json
    axiom graph-n6-audit research/graphs/n6_exact_report.json

Full reproducibility, invariants, complexity and epistemic boundaries:
[AXIOM v0.12 exact n=6 specification](docs/exact_n6.md). Previous v0.11
source-bound frontier and all historical results remain preserved below.

---

# AXIOM v0.11 — Source-Bound Graph Frontier Lineage (development)

AXIOM v0.11 connects the **real v0.9 bounded n=6/n=7 graph
experiments** to the cumulative v0.6–v0.8 mathematical knowledge store
without modifying previous results or claiming any new graph theorem.

It separately materializes exact typed experimental statements, independently
checked counterexamples, campaign-specific bounded searches, and
non-entailing links to the original complete n=5 source proofs. Every import
and audit deterministically replays the full original mathematical sources,
historical Lean proof provenance and the actual v0.9 experiment algorithm.

Once the original database is populated (see v0.10/v0.8 instructions):

    axiom graph-frontier-run --target-order 6 --search-budget 256 \
      --max-candidates 40 --output research/graphs/n6.json \
      research/graphs/v05_baseline_report.json research/graphs/v05_scale_report.json

    axiom graph-frontier-run --target-order 7 --search-budget 256 \
      --max-candidates 40 --output research/graphs/n7.json \
      research/graphs/v05_baseline_report.json research/graphs/v05_scale_report.json

    axiom knowledge-frontier-import --db research/knowledge/axiom.sqlite3 \
      research/graphs/n6.json research/graphs/n7.json

    axiom knowledge-frontier-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-frontier-query --db research/knowledge/axiom.sqlite3 \
      --order 6 --status REFUTED

See [the v0.11 frontier lineage specification](docs/frontier_lineage.md)
for evidence boundaries, complete setup, independent audits, testing and CI.
The existing v0.10 and older research architecture follows unchanged.

---

# AXIOM v0.10 — Evidence-Gated Mathematical Research Agenda (development)

AXIOM v0.10 adds a deterministic, provenance-checked research task planner
across **finite graphs, polynomial algebra, number theory and modular
recurrences**. Its output recommends the next concrete falsification or
proof-verification action without claiming that any action was performed.

The agenda re-audits the original graph source records, the typed
mathematical federation, and any source-bound historical Lean proof records
before scheduling. It **excludes already refuted statements**, never turns a
bounded experiment into a proof, and distinguishes historical offline Lean
record integrity from a fresh real kernel execution.

After building and federating the historical knowledge database:

    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --limit 30 --output research/knowledge/research_agenda_v010.json
    axiom knowledge-plan-audit --db research/knowledge/axiom.sqlite3 \
      research/knowledge/research_agenda_v010.json
    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --domain graph --limit 10
    axiom knowledge-plan --db research/knowledge/axiom.sqlite3 \
      --limit 100 --offset 100

For complete installation and the reproducible build of the knowledge
database, see [the v0.10 research agenda protocol](docs/research_agenda.md).
This component prioritizes work but does not itself execute new research
or formally prove new mathematical claims. The older AXIOM releases and
original experiment records follow unchanged.

---

# AXIOM v0.9 — Graph Conjecture Frontier (development)

AXIOM v0.9 starts a new bounded mathematical discovery campaign: it uses
**nonvacuous n=5 exact-order graph proofs** as motivation to generate and
falsify similarly structured statements at n=6 and n=7. A surviving
higher-order statement is only experimentally supported; a false statement
requires an actual independently rechecked counterexample.

Run from the project root after installing AXIOM:

    axiom graph-frontier-run --target-order 6 --search-budget 256 \
      --output research/graphs/frontier_n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json
    axiom graph-frontier-audit research/graphs/frontier_n6.json \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json

See [AXIOM v0.9 graph frontier research protocol](docs/graph_frontier.md)
for the n=7 campaign, independent audit, limitations and CI. No new
universal graph theorem is claimed. All previous v0.8/v0.7/v0.6 materials
and mathematical evidence are preserved below.

---

# AXIOM v0.8 — Source-bound Lean proof provenance (development)

AXIOM v0.8 connects the complete historical algebra and number-theory Lean
records to their exact statements and local certificates in the v0.7
cumulative knowledge federation. Original proof status is **never upgraded
on the basis of an offline JSON record**; existing externally verified Lean
runs remain separately attestable through GitHub CI.

Reproduce after installation:

    axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
      research/graphs/v05_baseline_report.json research/graphs/v05_scale_report.json

    axiom knowledge-federate --db research/knowledge/axiom.sqlite3 \
      research/v03_campaign_report.json research/number_theory/v04_report.json \
      research/number_theory/v04_sequences.json

    axiom knowledge-formal-import --db research/knowledge/axiom.sqlite3 \
      --algebra-ndjson research/v03_formal_results.ndjson \
      --number-index research/number_theory/v04_formal_results.ndjson \
      --number-records-dir research/lean_verified/number_theory

    axiom knowledge-formal-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-formal-query --db research/knowledge/axiom.sqlite3 --domain algebra

See the [v0.8 formal provenance specification](docs/formal_provenance.md)
for semantics, limitations, trust boundaries and CI reproduction. The previous
v0.7/v0.6/v0.5 documentation follows unchanged.

---

# AXIOM v0.7 — Cross-domain mathematical evidence federation (development)

AXIOM v0.7 adds a fail-closed typed evidence federation to the existing v0.6 SQLite knowledge graph. It connects **finite graphs, integer-polynomial algebra, elementary number theory, and modular recurrences** without changing original mathematical claims, verification statuses, or historical research files. Each imported report is replayed with its original mathematical auditor.

After installation:

    axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
      research/graphs/v05_baseline_report.json \
      research/graphs/v05_scale_report.json
    axiom knowledge-federate --db research/knowledge/axiom.sqlite3 \
      research/v03_campaign_report.json \
      research/number_theory/v04_report.json \
      research/number_theory/v04_sequences.json
    axiom knowledge-federation-audit --db research/knowledge/axiom.sqlite3
    axiom knowledge-cross-query --db research/knowledge/axiom.sqlite3 --domain recurrence

See [v0.7 federation specifications](docs/knowledge_federation.md). This is **not** a new mathematical theorem prover or formal Lean re-verification: source Lean proof artifacts remain separate, and federation never invents FORMALLY_VERIFIED statuses. The remaining v0.6/v0.5 documentation below is preserved.

---

# AXIOM v0.6 — Mathematical Knowledge Graph (development branch)

Version 0.6 adds an **auditable cumulative knowledge graph** for the v0.5 finite-graph campaigns, preserving source evidence, exact-order proof boundaries, counterexamples, historical evidence states, checker dependencies, and navigable higher-order analogues without inferring any universal theorem. The old research modules and v0.5 reports are preserved.

Run after installation:

```bash
axiom knowledge-build --db research/knowledge/axiom.sqlite3 \
  research/graphs/v05_baseline_report.json research/graphs/v05_scale_report.json
axiom knowledge-audit --db research/knowledge/axiom.sqlite3
axiom knowledge-query --db research/knowledge/axiom.sqlite3 --template handshake --order 5
```

Full design, limits, tests and provenance model: [Knowledge Graph v0.6](docs/knowledge_graph.md). **Proof-status policy:** no new graph Lean verifications, originality claims, or all-order graph theorems are asserted. The remainder of this README documents the fully preserved v0.5 capabilities.

---

# AXIOM v0.5 — Mathematical Discovery, Number Theory, and Finite Graphs

**AXIOM** is an executable, local-first, reproducible mathematical research laboratory. Version 0.5 adds a **Combinatorics and Graph Mathematics** module to the already developed integer polynomial, number-theory and Lean 4 workflows. Autonomous campaigns generate exact typed conjectures, search for counterexamples, independently validate proof certificates within narrowly specified fragments, checkpoint to SQLite, and produce reproducible experiment reports.

**Version 0.5 evidence:** the local release suite passed **117 tests**, with **6 genuine-Lean tests skipped locally**; the previous v0.4 real-Lean CI run (96/96 number-theory and 85/85 algebraic proofs) remains separately recorded. The v0.5 independent graph CI [run 43371399269](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43371399269) also succeeded under Python 3.11 and 3.13 (116 passed, 7 skipped per runner; optional NetworkX and actual Lean tests skipped). The new graph module has **no Lean kernel-verification claims**. It produces finite-domain proofs only for simple graphs with a *specific* n≤5 using an independent checker which enumerates every labelled graph of that fixed order. The project never infers all-n graph theorems from these results.

**Important:** All graph-generation methods use known templates. Originality is `NOT_ASSESSED`, and statements valid for exactly five vertices must not be described as theorems for all graph orders. Finite sampled graph searches for n=6 or 7 yield only bounded evidence. See [graph trust boundaries and proofs](docs/graph_mathematics.md) and [the exact checkpoint](CHECKPOINT.md).

## v0.5 — Run the graph mathematics laboratory

```bash
# After installing the project as shown below:
axiom graph-enumerate --max-order 5
axiom graph-count --max-order 5
axiom graph-run --seed 42 --candidates 240 --max-order 6 --search-budget 128 \
  --db research/graphs/new.sqlite3 --report research/graphs/new.json
axiom graph-audit research/graphs/new.json
axiom graph-check-certificate research/graphs/examples/handshake_n5.json
```

The first example enumerates **1, 1, 2, 4, 11, 34** unlabelled graphs for orders zero through five. The second verifies the labelled edge-count distribution via complete enumeration. Campaign outputs classify candidates into independently checked finite-order proofs, confirmed counterexamples, and unresolved sampled claims. `--step-limit N` permits checkpointed interruption; reusing the identical configuration and database resumes the next position. All capabilities work locally without paid AI APIs, a GPU, or external formal tools.

**Executed v0.5 baseline:** 240 positions → 133 distinct statements, 107 duplicates, 102 fixed-order proofs (98 nonvacuous + 4 vacuous), 20 refutations, 11 experimentally supported statements. **Scale test:** 700 positions → 224 distinct statements, 139 finite-order proofs (133 nonvacuous + 6 vacuous), 50 refutations, 35 experimental statements. The experiment databases, full reports, statement-linked examples, and measurements are under `research/graphs/`; no result is presented as novel. These rates are specific to the bounded template grammar and are not measures of general mathematical intelligence.

## Existing v0.1–v0.4 capabilities (preserved)

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
- **Formally verified:** **zero in the original v0.2 campaign**; v0.3 separately preserved 85 successful external Lean 4 checks. The original SQLite statuses are deliberately unchanged.
- **Originality:** `NOT_ASSESSED` for all v0.2 results. Heuristic ranking is not a novelty score.

`axiom audit-report REPORT.json` replays deterministic generation and deduplication, compares all candidate statements, checks every proof certificate and counterexample, validates status histories and checks counts. Evidence tampering is rejected. This checks internal coherence, **not** external novelty or trusted-kernel formal verification.

## Executed research campaigns

| Release | Seed | Generated positions | Duplicates | Refuted | Supported-fragment proofs | Experimental | Formally verified |
|---|---:|---:|---:|---:|---:|---:|---:|
| v0.1 baseline | 42 | 300 | 159 | 89 | 49 | 3 | 0 |
| v0.2 campaign | 42 | 300 | 132 | 82 | 85 | 1 | 0 |
| v0.3 Lean audit of reproducible v0.2-style campaign | 42 | 300 | 132 | 82 | 85 | 1 | **85** |

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

The generator is still a bounded template grammar, and mathematical deduplication is mostly structural; it is not general theorem invention. Counterexample minimization is local, not optimal. Proof methods exclude induction, nonpolynomial algebra, generic inequalities, and Z3. v0.3 now includes actual Lean 4 proof assistant verification only in the supported fragment; broader mathematics and additional certified proof strategies are the recommended next objectives. No asynchronous research scheduling is claimed.

**Preservation rule:** keep previous releases and research evidence intact; do not overwrite historical v0.1 results. Reproduce all claimed metrics and proof artifacts before advancing any version.

---

## AXIOM v0.3 — optional Lean 4 kernel verification

The v0.3 adapter does **not** treat a locally accepted algebraic certificate as a Lean theorem. It builds a separate, uniquely named Lean theorem from the exact typed statement, exact assumptions and locally validated certificate, runs an actual external Lean 4 process, checks the theorem's transitive axioms with `#print axioms`, and writes source-bound execution evidence. The existing v0.2 research database and statuses are never silently overwritten.

**Pinned verification environment:** Lean `leanprover/lean4:v4.35.0`, Mathlib revision tag `v4.35.0` as declared in `lakefile.toml`. A genuine success record also requires the actual `lake-manifest.json` and checked-out Mathlib commit to agree. All other axiom names, including `sorryAx`, custom axioms and native evaluation axioms, are rejected. The generated source contains neither `sorry` nor arbitrary user-supplied Lean text. The only current proof strategies are integer polynomial ring normalization and an SOS decomposition with `sq_nonneg`/`nlinarith`. Not all locally certified proofs are guaranteed to be accepted by Lean tactics.

### Install Lean on Linux Mint / Ubuntu

Install the Python package as above. Follow the official Lean 4 `elan` instructions to install the toolchain manager, then from this repo:

```bash
lake update
lake exe cache get
lake env lean --version
pytest -q
```

The first Mathlib cache download can be large. No Lean or Mathlib installation is required to run the v0.2 discovery engine, verify local certificates, or execute the Python unit tests. The actual Lean integration tests require a working pinned installation:

```bash
AXIOM_REAL_LEAN=1 pytest -q tests/test_lean_integration.py
```

### Verify and retain proof artifacts

```bash
axiom lean-verify research/certificates/example_identity.json \
  --project-root . \
  --output research/lean_verified/identity.json \
  --source research/lean_verified/identity.lean

axiom lean-verify research/certificates/example_sos.json \
  --project-root . \
  --output research/lean_verified/sos.json \
  --source research/lean_verified/sos.lean

axiom lean-verify-report research/v03_campaign_report.json \
  --project-root . --output-dir research/lean_verified/my_campaign --limit 85

# Audit source-bound GitHub CI results against replayed exact research statements:
axiom audit-lean-results research/v03_campaign_report.json \
  research/lean_verified/campaign --require-complete
```

Exit code `0` indicates that actual Lean invocation succeeded and the transitive axiom policy accepted the theorem. Exit code `1` means unavailable, incomplete, rejected or failed verification; `2` indicates invalid configuration or inputs. The saved JSON captures theorem, imports, exact assumptions, full proof source, source hash, statement and certificate, pinned toolchain, actual Lean version, Mathlib revision and manifest hash, axiom dependencies, checker exit status and time. A Python-only audit of this JSON is **not** authentication that Lean actually executed: retain GitHub Actions CI logs and artifact provenance for external verification.

When Lean is unavailable, AXIOM exits nonzero, saves a record labeled `LEAN_UNAVAILABLE`, and reports no formally verified theorems. There is no hidden fallback that promotes status based on symbolic proof or simulated compiler output.

The GitHub Actions workflow `.github/workflows/lean-verification.yml` installs pinned Lean and Mathlib, reruns the full Python suite, compiles the two saved proof benchmarks, audits admitted axiom dependencies, and attaches the generated proof source and evidence JSON as a workflow artifact. **Actual verified evidence:** [GitHub Actions run 43342422453](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43342422453) passed with 85 attempted and 85 accepted research theorems; its individual source-bound JSON outputs and two benchmark sources are archived in `research/lean_verified/`, with a machine-readable catalogue in `research/v03_formal_results.ndjson`. Mathlib resolved SHA: `56a005855ea17e0b0958f73ec801ae140b0a1679`. The local non-Lean environment did not itself run the kernel. Originality remains unassessed.

### Trust limitations

- Lean kernel checks the generated Lean theorem, not necessarily every nuance of the mathematical interpretation of a human's informal description. The typed AST-to-Lean translator therefore remains part of the trusted interface.
- A GitHub Action is execution evidence only after its actual run and logs are checked; a workflow file alone proves nothing.
- Local `FORMALLY_VERIFIED` labels never imply novelty, independent human review or a machine-checked specification of the entire AXIOM application.
- Python unit tests mock subprocesses in some cases to test failure boundaries. Those mock results are never counted as real kernel verifications.
- Algebraic certificates still use the independent Python verifier from v0.2 and do not depend on paid model services.


### Verified v0.3 research evidence and reproduction

The **actual** completed GitHub run [43342422453](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43342422453) reported 85/85 kernel-checked research candidates, 3/3 real-Lean integration tests, 43/43 Python tests at that commit, and a successful regenerated-campaign audit. The final post-run release incorporates one additional local audit test (44 passed, three genuine Lean tests skipped where Lean is unavailable).

- `research/v03_campaign_report.json` and `research/v03_campaign.sqlite3`: reproducible 300-position research experiment.
- `research/lean_verified/campaign/`: 85 individual, fully source-bound JSON proof execution records plus batch summary, downloaded from the successful GitHub Actions artifact.
- `research/v03_formal_results.ndjson`: all 85 formal-verification records in deterministic candidate ordering.
- `research/v03_formal_results_summary.json`: reproducible CI run/job/commit IDs, mathlib SHA, digest, counts and independent evidence audit.
- `research/lean_verified/ci_identity.*`, `ci_sos.*`: exact individual known-benchmark proof source and execution records.
- `.github/workflows/lean-verification.yml`: official automation to install Lean/Mathlib, regenerate the research campaign, formally verify proof candidates and audit the output.

The 85 proofs comprise 48 polynomial identities and 37 supported sum-of-squares inequalities. They are **not 85 novel mathematical theorems**. `audit-lean-results` checks data integrity and exact source/statement binding but cannot by itself establish a signed attestation that historical CI ran; the independently accessible GitHub Actions logs establish that execution.

**Now implemented:** v0.4 integer number theory and recurrence laboratory; see below. **Next:** v0.5 combinatorics and graph mathematics.

## v0.4 Number Theory Laboratory

The v0.4 research engine adds exact typed integer divisibility `a ∣ b`, strictly
positive integer modular congruence `a ≡ b (mod m)` (represented as `m ∣ a-b`),
independent integer-polynomial-factor proof certificates, adversarial bounded
falsification and resumable SQLite campaigns. It also includes an independently
checked finite-state periodicity engine for order-two integer recurrences.

```bash
# Run and independently replay an autonomous number theory research campaign.
axiom nt-run --seed 42 --candidates 300 --lower -8 --upper 8 --max-evals 289 \
  --db research/nt_replay.sqlite3 --report research/nt_replay.json
axiom nt-audit research/nt_replay.json

# Exact modular recurrence proofs (not Lean verification):
axiom nt-sequence-run --seed 42 --budget 40 --report research/nt_sequences.json
axiom nt-sequence-audit research/nt_sequences.json

# Independently check a saved number-theory quotient certificate:
axiom nt-check-certificate research/number_theory/nt_example_74754e364917.json

# Optional real Lean 4 + Mathlib: pin resolution and verification:
lake update && lake exe cache get
axiom nt-lean-verify-report research/nt_replay.json \
  --project-root . --output-dir research/nt_lean_verify --limit 96
AXIOM_REAL_LEAN=1 pytest -q tests/test_number_theory_lean_integration.py
axiom nt-audit-lean-results research/nt_replay.json research/nt_lean_verify \
  --expected-attempts 96 --require-verified
```

Full mathematical semantics, trust boundaries and limitations: [`docs/number_theory.md`](docs/number_theory.md).
For direct research artifacts: [`research/number_theory/`](research/number_theory/).
A locally accepted number-theory certificate is not automatically a Lean-verified theorem.
Fibonacci periods 3 mod 2 and 20 mod 5 are known benchmarks, not discoveries.
The generated candidate grammar is deliberately small; originality remains unassessed.


### AXIOM v0.4 measured formal verification results

The actual successful [GitHub Actions run 43365165754](https://github.com/SaridakisStamatisChristos/Axiom/actions/runs/43365165754) accepted **96/96 new supported-fragment integer number-theory proofs** and independently rechecked **85/85 v0.3 algebraic proofs**. The v0.4 number-theory result archive contains individual Lean input sources, statement binding, resolved Mathlib revision and checker axiom lists. Three genuine Lean number-theory integration tests and the independent provenance audit also passed.

The 40 separate recurrence periodicity certificates are checked by the standalone Python finite-state checker **only**, not by the Lean kernel. None of the statements have been assessed for novelty. Full measured campaign and resource data are in [`research/number_theory/RESULTS.md`](research/number_theory/RESULTS.md). See `CHECKPOINT.md` for actual CI run, artifact ID, exact toolchain and current limitations.

To package all checked source and research data reproducibly:

```bash
python scripts/build_release.py --output ../AXIOM_v0.4_Number_Theory_Laboratory.zip
```

The build includes a per-file SHA-256 manifest; generating the ZIP does **not** substitute for running tests or Lean checks.
