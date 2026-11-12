# AXIOM v0.2: proof semantics, checker and trust boundary

## 1. Logical fragment

A statement consists of one or two universally quantified variables selected from `x`, `y`, with domain `ℤ`, optional closed integer interval assumptions per variable, a typed exact-integer polynomial expression on each side, and a relation `==`, `>=`, or `<=`. Every expression is total on integers; operations are integer constants, variables, `+`, `−`, `×`, and nonnegative powers (individual exponent <=8). Division and potentially undefined expressions are excluded.

An unrestricted theorem asserts that the relation holds for every integer valuation; one with interval assumptions asserts the relation for each valuation satisfying those assumptions. Neither a bounded *search* window nor a random seed changes the theorem's quantification or assumptions.

## 2. Identity certificates

If `L,R ∈ ℤ[x,y]`, then `L = R` for every integer assignment whenever their coefficient maps are identical. AXIOM first constructs a possible proof with its own sparse polynomial expander and a SymPy `Poly` cross-check. It then packages both claimed coefficient maps into a certificate, SHA-256-bound to the original full statement (including assumptions and quantifiers).

The independent checker re-parses the original AST and recomputes the coefficient maps using a different stdlib implementation. It compares these maps against the supplied coefficients **and against one another**. It does not trust an empty difference list or a claimed `verified=true` field. Contradictory identities are rejected even if a certificate's statement digest is recomputed after tampering.

A certificate is accepted only when the recomputed coefficient maps equal the claimed maps and are identical. The checker does not import the symbolic engine, the conjecture generator, or SymPy. Its trust base nevertheless includes CPython, exact integer arithmetic, its parsing/normalization code, and the mathematical identity theorem. This is **not formal verification by Lean**.

## 3. Sum-of-squares certificates

For a `>=` inequality set `P=L−R`; for `<=` use `P=R−L`. A certificate supplies a *positive integer* multiplier `M`, *nonnegative integer* constant `C`, and finitely many positive-integer weights `w_i` and integer polynomials `q_i` such that:

\[
M P(x,y) = C + \sum_i w_i q_i(x,y)^2.
\]

The checker independently normalizes both sides, validates **exact** integer coefficient equality, and validates every sign constraint. Because all squares and `C` are nonnegative and `M>0`, `P >= 0` for every integer assignment. No floating-point reasoning, sampling, or unrecorded assumption is required.

The initial constructor handles *separable quadratics*:

\[
P = C + \sum_i (a_i x_i^2 + b_i x_i), \quad a_i>0,
\]

with no cross-monomials, no odd linear terms lacking a positive quadratic coefficient, and a nonnegative completed-square remainder. Let `M=4∏a_i`. Then

\[
M P = \sum_i \frac{M}{4a_i}(2a_i x_i+b_i)^2
 + \left(MC-\sum_i \frac{M b_i^2}{4a_i}\right).
\]

If the final constant is negative, no certificate is produced by this strategy. Constant nonnegative expressions are represented by an empty sum of squares and a positive multiplier. This procedure is *sufficient, not complete*: other true inequalities may remain experimentally supported or unresolved. It does not conclude an inequality merely because the test domain is finite.

## 4. Independent certificate format

The JSON artifact contains exactly:

```json
{
  "statement": {"lhs": {"op": "var", "value": "x", "args": []},
                "rhs": {"op": "var", "value": "x", "args": []},
                "relation": "==", "variables": ["x"], "bounds": []},
  "certificate": {
    "schema": "axiom.polynomial.certificate.v1",
    "statement_sha256": "<actual 64-character digest of canonical serialized statement>",
    "variables": ["x"], "method": "coefficient_identity",
    "lhs_coefficients": [[[1], 1]], "rhs_coefficients": [[[1], 1]]
  }
}
```

The digest in this explanatory example is a placeholder: use the actual generated files in `research/certificates/`. Only the generated files are intended to be directly checked. The checker enforces exact JSON field schemas for proof certificates, disallows zero coefficients, unsorted or duplicate monomial terms, out-of-fragment operations and excess resource consumption.

## 5. Falsification and witness minimization

The search enumerates valid assignments within the **intersection** of the configured search window and explicit interval assumptions. The search attempts `0,±1`, boundaries and near-boundaries early; other numbers use seeded deterministic order. A candidate failing the original AST is rechecked by a distinct iterative evaluator, then optionally improved by coordinate descent under a 64-probe budget. `original_counterexample` records the first found witness; `counterexample` records the final validated witness. Minimization never claims global optimality and never changes the original theorem assumptions.

Searches report tested points, grid cardinality, seed, per-variable intersection bounds, and whether the grid was fully exhausted *without a witness*. Search windows cannot be promoted to theorem assumptions. A zero-size search is not a proof. A confirmed witness is decisive; a failure to find one is only experimental evidence.

## 6. Evidence state machine and report auditing

Accepted paths for a persisted finding:

- `GENERATED → UNDER_TEST → REFUTED` when a witness passes independent checking.
- `GENERATED → UNDER_TEST → EXPERIMENTALLY_SUPPORTED` when bounded exploration has no witness and no proof.
- `GENERATED → UNDER_TEST → UNRESOLVED` when no proof or witness was found.
- `GENERATED → UNDER_TEST → PROOF_CANDIDATE → PROVED_IN_SUPPORTED_FRAGMENT` only after certificate checker acceptance.

A resumed campaign rechecks every persisted proof and witness, then rejects a malformed status trace or forged proof. `axiom audit-report` also regenerates the conjecture list, verifies ordinals/templates/statement hashes and counts. The engine does not emit `FORMALLY_VERIFIED`: no trusted external proof checker has run. `originality=NOT_ASSESSED` is separate from mathematical correctness.

## 7. Resource / safety limits

The standalone checker enforces a total of 128 AST nodes, <=4096 nonzero polynomial terms, <=128 total degree, <=4096-bit integer coefficients/constants, <=200000 term-pair products for each multiplication, and <=16 squares per SOS. The search window width is capped at 100000; at most 1000000 valuations are examined per candidate; counterexample minimization is capped at 64 probes. When limits prevent proof, the claim must remain unproved, never be promoted.

## 8. Open proof obligations

- Checker remains trusted Python code, not formally proven correct. An implementation error in the checker could still give a false positive.
- The syntax grammar is not a general-purpose formal logic; no induction, limits, rational domain, division, or partial functions.
- No trusted Lean kernel verification, SMT proof artifacts, formal library dependency tracking, or novelty/literature assessment.
- Exact byte-identical replay requires the same Python/SymPy/tool versions and generator semantics. Historical v0.1 campaign evidence is preserved under its original schema, never silently upgraded.
