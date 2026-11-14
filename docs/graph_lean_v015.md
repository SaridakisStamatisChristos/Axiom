# AXIOM v0.15 — Real Graph Lean Verification and Research Executor

AXIOM v0.15 adds **actual Lean 4 kernel checking** to a restricted subset
of independently certified exact-six-vertex graph claims. It does not treat
the existing Python exhaustive certificates as Lean proofs.

## Supported formal translations

The initial Lean generator supports three templates:

- Handshake: sum of vertex degrees is twice the number of edges.
- Degree bound: maximum degree is at most five.
- Triangle upper bound: at most twenty triangles.

The universe is exactly six labelled vertices and 15 possible undirected edges,
encoded as bit positions 0 through 14. The generated theorem explicitly quantifies
over edge masks below 32768 and states the invariant via six-vertex definitions.
This is not a theorem over every possible vertex count.

Four additional existing exact-n6 templates remain pending formal translation.
An unsupported task is never promoted to formal verification.

## Installation

Install AXIOM and the pinned Lean toolchain from the repository root:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'
    lake update
    lake exe cache get

## Direct verification

Generate and audit the original Python certificates:

    axiom graph-n6-run --templates handshake degree_bound triangle_upper_bound \
      --output research/graphs/v015_n6_source.json
    axiom graph-n6-audit research/graphs/v015_n6_source.json

Extract any proved finding into a JSON artifact containing exactly two keys:
statement and certificate. Then invoke the real Lean checker:

    axiom graph-n6-lean-verify research/graphs/handshake_artifact.json \
      --project-root . --timeout 240 \
      --source research/lean_verified/graph_n6/handshake.lean \
      --output research/lean_verified/graph_n6/handshake.json

The command exits nonzero unless the actual pinned Lean process succeeds
and its theorem axiom report passes the trusted whitelist.

## Source-replayed research execution

After constructing the original v0.14 knowledge database with graph reports,
federation, bounded n6/n7 experiments and exact-n6 campaigns:

    axiom graph-lean-autopilot \
      --db research/knowledge/axiom.sqlite3 \
      --output-dir research/lean_verified/graph_n6 \
      --project-root . --max-proofs 3 --timeout 240

    axiom graph-lean-autopilot-audit \
      --db research/knowledge/axiom.sqlite3 \
      research/lean_verified/graph_n6

The executor obtains fully audited exact-source agenda entries, selects supported
Lean tasks, verifies that each matches the original certificate, calls Lean,
and saves immutable standalone JSON evidence. Unsupported and budget-deferred
tasks remain explicitly pending; original research findings are never rewritten.

The standalone offline audit validates source binding and consistency but
**does not independently attest actual Lean execution**. Trust a real checked
run or its recorded GitHub Actions job logs for that separate claim.

## Verification

GitHub Actions workflow graph-lean-v015.yml runs source replay, Python safety
tests, and real Lean proof checks, and preserves result artifacts on failures.
No unproved axioms, sorry, admit, native_decide, user-provided Lean source
or all-order generalization is introduced by this adapter.
