# Proof semantics and threat model

## Logical fragment

Statements are constructed from immutable, validated `Expr` trees: `const` (Python exact `int`), `var` (`x` or `y`), `add`, `sub`, `mul`, `pow` with a nonnegative integer exponent <=8. Each statement specifies a universal quantification of one or two integers, optional closed integer interval assumptions, and one comparison `==`, `>=`, or `<=`.

No parser evaluates user-controlled Python code. A supplied serialized expression is rejected if operation, type, arity, exponent, or variable rules fail. The scope excludes division and partial functions entirely.

## Polynomial certificate

For a purported identity `∀x∈Z, ... : lhs(x)=rhs(x)`, two distinct procedures compute the sparse coefficient map of `lhs-rhs` over `Z[x,y]`. One is a pure-Python recursive distributive expansion, the other SymPy's polynomial normalizer over the integer domain. Only if maps agree and all coefficients vanish is the candidate marked `PROVED_IN_SUPPORTED_FRAGMENT`.

The mathematical justification is the polynomial identity theorem over the infinite integral domain `Z`; zero coefficient difference implies equality for every integer valuation. Equivalently, all terms in the free commutative ring cancel exactly. The proof does not use finite sampling. Conditional identities proved globally remain valid under explicitly recorded integer bounds.

`PROVED_IN_SUPPORTED_FRAGMENT` is *not* `FORMALLY_VERIFIED`: there is no external Lean kernel acceptance, and the correctness argument assumes the host language/interpreter and both implementations work correctly. Evidence contains method name, variables, empty coefficient difference, normalizer names, and SymPy version.

## Counterexample certificate

A candidate is first subjected to a deterministic, boundary-first bounded enumeration. Each assignment satisfies every recorded interval assumption; checks use Python arbitrary-precision integer arithmetic. When a failure occurs, a separate iterative evaluator re-evaluates the original syntax trees and confirms the inequality/equality violation. The exact variable assignments and two evaluated sides are stored. Search reports its tested count, configured bounds, seed, whether the grid was fully enumerated, and its product cardinality.

The counterexample enumeration range is a search **budget**, not part of the mathematical universal domain unless explicit assumptions restrict it. A search that finds no counterexample does not prove a universal statement. Currently any non-equality without a witness is only `EXPERIMENTALLY_SUPPORTED`, even if every member of its finite specified interval was checked. This conservative policy avoids conflating universal and finite-domain conclusions.

## Status and trust policy

`GENERATED -> UNDER_TEST -> REFUTED | EXPERIMENTALLY_SUPPORTED | UNRESOLVED | PROOF_CANDIDATE -> PROVED_IN_SUPPORTED_FRAGMENT` are evidence transitions recorded per result. `FORMALLY_VERIFIED` is reserved and is never emitted by v0.1. Historical results are persisted without retroactive promotion. Originality is independent (`NOT_ASSESSED`).

## Known technical limits

- Two normalization algorithms can share a conceptual mistake; neither is a formal proof kernel.
- The seeded generator covers three polynomial algebraic templates, and a bounded inequality template in mixed mode.
- Search may miss counterexamples outside the finite configured grid; witness minimization is not implemented.
- Canonicalization catches structural commutations and symmetric equalities, not full polynomial semantic equivalence.
- This release does not integrate Z3, Lean, theorem dependency reuse, probabilistic generators, distributed execution, or global literature searching.
- Extreme integer size and exponent/nesting combinations can be expensive. AST size and exponent are limited; constant bit sizes are not yet independently capped.
