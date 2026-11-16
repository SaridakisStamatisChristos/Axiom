# AXIOM v0.19 — assumption-guided research and genuine affine Lean subfragment

v0.19 adds two independent, non-breaking scientific capabilities.

## Assumption-aware n=7 experiments

The existing AXIOM v0.18 research lane generated conditional inequalities
but sometimes its uniform-like n=7 holdout contained zero graphs satisfying
the conjecture's antecedent. New \`graph-synthesize-guided\` generates
deterministic, **non-uniform** labelled graphs that satisfy each selected
candidate's assumption **by construction**:

- ALL: hash-derived arbitrary labelled simple graphs.
- CONNECTED: hashed spanning paths with extra random edges.
- BIPARTITE: random subgraphs of generated bipartitions.
- TRIANGLE_FREE: bipartite subgraphs mixed with triangle-free five-cycles
  (which deliberately test non-bipartite examples).

The selection/training and *full historical source preflight* are identical
to v0.18 and use only independently replay-audited earlier source records.
Graph construction happens **after** selection. All accepted holdout graphs
are checked with the independent reference invariant oracle; any witnessed
refutation is separately checked against the discovery oracle. Every accepted
graph must satisfy the typed assumption. Previously tested historical masks
and graphs tested in the same new run are excluded.

The sampling is biased intentionally toward antecedent coverage, not a
uniform or representative distribution of n=7 graphs. Do not interpret
sample counts as statistical estimates or formal mathematical proof.

    axiom graph-synthesize-guided --db research/knowledge/axiom.sqlite3 \
      --output research/knowledge/guided_v019.json \
      --holdout-budget 24 --max-candidates 4

    axiom graph-synthesize-guided-audit --db research/knowledge/axiom.sqlite3 \
      research/knowledge/guided_v019.json

Audit independently replays source data, candidate selection and all new
masks. Reports are immutable with exclusive file creation. Original reports
and older v0.18 research schemas are not changed.

## First genuine affine-graph Lean translator (strict closed fragment)

AXIOM v0.19 also adds a **real kernel-verification lane** for source-typed
affine inequalities at graph order **n=6 only**. This first supported
fragment has unconditional ALL-graph scope, terms involving *both* edges
and triangle counts with strictly positive integer coefficients, optional
coefficient on n, and a constant bound implied by the structural
ceilings |E| <= 15 and triangles <= 20.

The translator defines the fifteen independent adjacency bits, all twenty
triangle indicators, edge count and triangle count directly in Lean.
The generated theorem quantifies over all 15-bit masks of order-six simple
graphs, with an explicit proof constructed using bounds on the indicator
terms and Lean's \`omega\` tactic. The real \`lake env lean\` checker is
executed. Exact Lean version, pinned Mathlib revision, \`#print axioms\`,
whitelisted axioms, checker exit code and the full generated source hash
are checked and preserved. No \`sorry\`, \`native_decide\`, proof stubs or
injected user Lean source are accepted.

For example, \`edges + triangles <= 35\` is derivable for n=6. This
is an **elementary fixed-order theorem**, not a newly discovered all-order
result. The translator refuses even slightly tighter bounds unless it has
a sound supported proof method; statements with connectivity, bipartite
or triangle-free assumptions and other invariants are reported UNSUPPORTED.

    axiom graph-affine-lean-verify \
      research/knowledge/affine_n6_input.json \
      --project-root . --timeout 240 \
      --output research/lean_verified/affine_n6_result.json \
      --source research/lean_verified/affine_n6_source.lean

    axiom graph-affine-lean-audit \
      research/lean_verified/affine_n6_result.json

Input is a JSON object containing a single key \`statement\` with a canonical
AXIOM \`AffineGraphConjecture\` dictionary. Offline audit rechecks source
integrity and scope, but *cannot by itself attest* that external Lean ran;
CI execution logs supply separate confirmation.

**Critical scope:** a successful Lean result proves the theorem at exactly
six vertices, NOT the original universal/all-graph-orders conjecture.
Existing v0.15 fixed n=6 proof evidence remains valid and separate.
Extending this closed translator beyond simple envelopes, adding
assumption semantics, and formally proving genuinely strong generated
inequalities are future work.
