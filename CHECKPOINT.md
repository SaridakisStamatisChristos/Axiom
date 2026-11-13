# AXIOM — continuation checkpoint (v0.3 Lean integration)

- **Development target:** AXIOM v0.3, Lean 4 proof verification adapter, 13 November 2026.
- **Upstream verified stable release:** AXIOM v0.2; commit `a0723b61f492768a9cd695b1175fe93a6fc69520`, branch `main`, https://github.com/SaridakisStamatisChristos/Axiom.
- **Current code state:** Lean adapter/source generation implemented and Python-tested. The local sandbox **does not have `lean` or `lake` installed**, and has no network access for toolchain downloads. Therefore actual kernel success **cannot be claimed locally**; CI must be inspected separately. The presence of a workflow file is not proof of its successful execution.
- **Research originality:** `NOT_ASSESSED`; no new theorem novelty claim.

## Verified local engineering

- Complete v0.2 discovery, proof-certificate and counterexample pipeline preserved without semantic changes.
- Optional formalizer `src/axiom/lean_backend.py`: source generation only from exact independently checked certificates; explicit integer variables and bounds; SHA-256 statement/source hashes; `ring` for identities; SOS `sq_nonneg`/`ring`/`nlinarith` proof source for inequalities; `#print axioms` transitive dependency audit; allowed only empty or standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`).
- Pinned toolchain `leanprover/lean4:v4.35.0`, Mathlib tag `v4.35.0`; runtime checks exact actual `lake-manifest.json` Mathlib commit against installed checkout and records version, dependency manifest digest, sources, process result, diagnostic excerpt and axiom output.
- CLI `axiom lean-verify` writes a single proof execution record and optional `.lean` source; `axiom lean-verify-report` first audits complete campaign, then attempts at most N formal proofs without mutating the original campaign.
- Local `pytest -q` **43 passed, 3 skipped** (real-Lean integration tests deliberately skipped when no pinned Lean environment exists). Local tests use mocked subprocess outputs for parsing/error branches, which are **not actual kernel proof evidence**.
- Local negative tests: tampered certificates, false candidate, altered assumptions, missing compiler, invalid version, timeout, missing axiom output, duplicate output, `sorryAx`/custom axioms, nonzero exit, stderr and forged source binding.
- Local `AXIOM_REAL_LEAN=1 pytest -q tests/test_lean_integration.py` **not executed**: Lean unavailable. GitHub workflow `.github/workflows/lean-verification.yml` is intended to run genuine Lean tests when executed.

## Actual local research rerun

- `PYTHONPATH=src python -m axiom run --seed 42 --candidates 300 --domain mixed --lower -8 --upper 8 --max-evals 289 --db research/v03_campaign.sqlite3 --report research/v03_campaign_report.json` completed.
- `PYTHONPATH=src python -m axiom audit-report research/v03_campaign_report.json` **ACCEPTED**, 168 findings audited.
- Generated positions 300; structural duplicates 132; investigated candidates 168; locally checked certificates 85; refutations with valid counterexamples 82; experimentally supported, not proved 1.
- Rerun measured: 0.383581 s, 782.1 generated positions/second and peak Linux process RSS 135128 KiB, on Python 3.13.5 and SymPy 1.14.0. Workload is identical to v0.2; these are measurements, not claims of improved performance.
- Local `lean-verify-report` attempt on 3 historical locally proved findings: **3 `LEAN_UNAVAILABLE`; 0 actual kernel verified**, exit nonzero. This is correct fail-closed behavior.
- `research/lean_examples/example_identity.lean` and `example_sos.lean` are generated **but not locally compiled**; CI must verify.

## Required real formal verification gate

1. Obtain actual GitHub Actions workflow run and inspect `lean-kernel` job conclusion and log.
2. Confirm pinned Lean version 4.35.0, Mathlib revision in `lake-manifest.json`, successful core test suite.
3. Confirm actual Lean execution for `research/certificates/example_identity.json` and `example_sos.json`, success exit codes, `#print axioms` with no disallowed axioms and evidence artifact `axiom-v03-lean-kernel-evidence`.
4. Confirm real-negative test observes the forbidden `sorryAx` dependency in Lean's theorem audit.
5. Only after all succeed may the kernel-verified example count be raised; do not infer success from Python mocks, documentation, or source generation.
6. Actual mathlib build/bandwidth requirements may prevent CI from completing; if so preserve the v0.3 implementation branch and leave the milestone labeled pending.

## Reproduction

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
lake update && lake exe cache get
axiom lean-verify research/certificates/example_identity.json --project-root . --output research/lean_verified/identity.json --source research/lean_verified/identity.lean
axiom lean-verify research/certificates/example_sos.json --project-root . --output research/lean_verified/sos.json --source research/lean_verified/sos.lean
AXIOM_REAL_LEAN=1 pytest -q tests/test_lean_integration.py
```

## Known limitations and next engineering action

- Lean generated proof for arbitrary certified SOS inequalities may fail `nlinarith`; compiler failure remains UNVERIFIED and is not hidden.
- No formal proof that the Python AST-to-Lean translation is semantics-preserving; only manually audited restricted grammar and explicit source records.
- Offline JSON evidence audits cannot authenticate a forged Lean execution record; preserve actual independent CI logs or re-run checker locally.
- No arbitrary external Lean imports, custom axioms, quantifier alternation, induction, rational expressions, or mathematical novelty assessment.
- **Next:** complete real Lean 4 CI proof execution and close any actual compiler or tactic failures. If verification succeeds, promote the v0.3 branch to `main`; then progress to v0.4 number theory.
