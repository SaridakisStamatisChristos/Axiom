# AXIOM v0.4 Number Theory Laboratory — Mathematical and Trust Specification

## Supported mathematical universe

- Quantification: universal quantification over one or two typed integers, named `x`/`y`.
- Expression grammar: exact `Int` constants, variables, `+`, `-`, `*`, nonnegative integer powers 0–8 (including the polynomial-ring convention `0^0 = 1`).
- Divisibility `a ∣ b` means `∃ k∈ℤ, b=a*k`. Negative divisors are allowed. **Zero divides zero**, but zero never divides nonzero integers.
- Positive-modulus congruence `a ≡ b (mod m)` means `m ∣ (a-b)`, with `m∈[1,2³¹]`. Modulus 0 or negative modulus is rejected rather than silently normalized.
- Optional explicit inclusive integer bounds are logical assumptions; a search interval is only an experimental limit, not a universal quantifier restriction.
- No rational quotients or integer division in the input grammar. No claim to decide all true integer-valued polynomial congruences.

## Proof fragment and independent certificate

A candidate proves `a ∣ b` only if it supplies a polynomial `Q∈ℤ[x,y]` such that the exact **formal polynomial identity** `b=a*Q` holds in `ℤ[x,y]` (a stronger statement than pointwise integer divisibility). Congruence is proved by `a-b=m*Q`. A candidate quotient can be found by SymPy's exact polynomial division over rational coefficients, but is accepted only when all quotient coefficients are integers and the remainder is zero.

The evidence includes the original typed statement (canonical JSON), SHA-256 statement binding, exact sparse integer quotient coefficients, allowed variable order, and method name. Independent `axiom.number_theory_checker` uses only Python standard-library arithmetic and the existing standalone bounded polynomial-normalizer, **not SymPy**. It reconstructs both polynomial operands and checks their exact multiplication identity. The quotient must be canonical with no zero coefficients or duplicate terms. Counterexamples are re-evaluated by a separate iterative expression evaluator. Mutated hashes and malformed proofs are refused.

This procedure is **sound within the stated fragment but not complete** for all true divisibility properties of integer-valued polynomials: `x² ≡ x (mod 2)` is true for every integer `x`, yet `(x²-x)/2∉ℤ[x]`. Hence this valid conjecture remains experimental/unproved unless another sound method is available. Exactly the same distinction applies to restricted bounded samples that happen to be all true.

## Optional real Lean 4 verification

After independent certificate acceptance, `axiom.number_theory_lean` translates the typed statement into a theorem over `Int` and produces an existential integer divisor witness followed by `ring`. Congruences are translated **explicitly as divisibility** `m ∣ (lhs-rhs)` under positive-modulus semantics. An installed pinned Lean and Mathlib system must compile the exact theorem and emit an auditable `#print axioms` result. The adapter accepts only whitelisted standard Lean axioms and checks resolved Mathlib dependency revisions and installed Lean version; absent Lean yields `LEAN_UNAVAILABLE`. No `sorry`, custom axioms, or guessed tool output is accepted. Kernel evidence is kept separate from the locally proved evidence.

Standalone compilation verifies the statement *as encoded in Lean*. Formalization correctness remains part of the trusted translation boundary.

## Order-two linear recurrence laboratory

A second, strictly scoped component explores `u[n+2]=p*u[n+1]+q*u[n]` for `n≥0`, initial integers `a₀,a₁`, and exact integer coefficients `p,q`. The modulus is in `[1,64]`. The state `(u[n] mod m, u[n+1] mod m)` transitions deterministically to `(b,(p*b+q*a) mod m)`. At most `m²` possible states exist; after at most `m²` transitions, a repeated state must occur. An independently checked certificate records every transition through the first repeated pair, preperiod `s`, and period `t>0`.

If state `s` equals state `s+t`, determinism implies, by induction on `j≥0`, state `s+j` equals state `s+t+j`. Thus **all terms from index `s` onward repeat modulo `m`**, not just the sampled prefix. The first repeat and a collision-free preceding prefix establish the reported *first-state-repeat* decomposition, without a novelty claim. This is a complete finite-state proof checked in Python, not a Lean proof. For some systems the preperiod is positive; AXIOM never incorrectly labels such sequences periodic from index zero.

Fibonacci `(a₀,a₁,p,q)=(0,1,1,1)` mod 2 has preperiod 0 and period 3; mod 5 has period 20. These are **known benchmark facts**; other generated recurrence analyses do not imply originality.

## Evidence statuses and limits

- `REFUTED`: a witness satisfies every recorded assumption and falsifies the original relation, verified by a separate exact evaluator.
- `EXPERIMENTALLY_SUPPORTED`: no counterexample within the documented finite search, **without** a universal proof.
- `PROVED_IN_SUPPORTED_FRAGMENT`: an independently checkable integer polynomial quotient identity (or deterministic finite-state recurrence certificate).
- `FORMALLY_VERIFIED`: only a separate artifact from an actual Lean kernel checker run with exact source/assumptions, dependency and axiom audit. Not awarded by Python tests or a Lean source file alone.
- Originality always `NOT_ASSESSED` unless a separate scholarly literature comparison is performed.

The recurrence certificates do not currently have a Lean backend. Factorization proof search is not completeness-preserving for integer-valued polynomials and is not a full Diophantine theorem prover. Source grammar remains a maximum of two variables. See `CHECKPOINT.md` and CI logs for exactly what was actually executed.

## Independent offline audit of Lean result provenance

After a genuinely executed Lean batch, replay the exact source-bound evidence
against the original deterministic research campaign with:

```bash
axiom nt-audit-lean-results research/number_theory/v04_report.json \
  research/lean_verified/number_theory --expected-attempts 96 --require-verified
```

This validates canonical statements, original proof certificates, generated
Lean source hashes, allowed transitive axioms, filenames and evidence totals.
It does **not** prove that a given JSON record came from a historical CI run;
that claim must also be backed by the external GitHub Actions run and logs.
