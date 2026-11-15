# AXIOM v0.16 — nonduplicative graph research campaigns

The complete v0.15 Lean proof bridge and independent research executor are
unchanged. v0.16 addresses a different problem: the bounded n=7 sampler in
v0.15 could revisit edge masks already explored by the v0.5 and v0.9
research campaigns. Repeated random sampling would waste resources and
inflate experiment counts.

This release adds \`graph-research-advance\`, a deterministic, incremental
bounded falsification engine that **excludes all previously searched labelled
masks from the independently replayed historical v0.5/v0.9 source reports**
and all earlier v0.16 iterations in its output directory.

## Usage

First construct the complete v0.14 knowledge database, including original
graph campaign imports, mathematical federation, historical formal metadata,
bounded frontier and exact-n6 findings.

    axiom graph-research-advance --db research/knowledge/axiom.sqlite3 \
      --output-dir research/knowledge/novel_runs \
      --iteration 0 --seed 42 --search-budget 64 --task-limit 2

    axiom graph-research-advance --db research/knowledge/axiom.sqlite3 \
      --output-dir research/knowledge/novel_runs \
      --iteration 1 --seed 43 --search-budget 64 --task-limit 2

    axiom graph-research-advance-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/knowledge/novel_runs/iterations/iteration_0001.json

Iterations are strictly sequential (0..64), source-fingerprint bound,
exclusive-create, and independently replayed; altered or missing predecessors
make subsequent research fail closed. Each saved JSON contains its predecessor
SHA-256 link, exact task identity, historical coverage fingerprint, individually
checked new masks and, where found, an independently checked counterexample.

The sampler uses an odd stride through the power-of-two labelled graph space
(2^21 at order seven); it is deterministic, full-period and rejects previously
seen graphs. The original seed/landmark PRNG algorithm is replayed to recover
exact historical masks. Earlier v0.16 task refutations are skipped in later
iterations, even if original v0.14 source evidence has not been rewritten.

**Evidence boundary:** Every result is either REFUTED with an independently
checked graph witness, or SURVIVED_BOUNDED_SEARCH. Even a large sample of
two million graphs is not promoted to a theorem without full coverage and
an independently audited proof. The new bounded lane does not itself invoke
Lean, and does not claim any new Lean formal verification. Use the existing
v0.15 \`graph-research-cycle\` for real Lean kernel proof attempts.

**Scope:** n=7 typed graph statements only. Historical v0.5/v0.9 sampling
is excluded; original v0.15 per-run experimental artifacts, if stored
elsewhere, are not automatically imported. No research output is written
into the immutable original knowledge tables.
