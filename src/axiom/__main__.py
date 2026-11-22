from __future__ import annotations
import argparse
import json
from .research import run_campaign


def main() -> None:
    p = argparse.ArgumentParser(prog="axiom", description="AXIOM v0.15 mathematical research")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="create or resume a deterministic research campaign")
    run.add_argument("--db", default="research/axiom.sqlite3")
    run.add_argument("--report", default="research/latest_report.json")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--candidates", type=int, default=100)
    run.add_argument("--domain", choices=("polynomial", "mixed"), default="polynomial")
    run.add_argument("--lower", type=int, default=-8)
    run.add_argument("--upper", type=int, default=8)
    run.add_argument("--max-evals", type=int, default=300)
    run.add_argument("--step-limit", type=int, default=None,
                     help="process only N additional positions to demonstrate checkpoint/resume")
    audit = sub.add_parser("audit-report", help="independently recheck research report evidence and totals")
    audit.add_argument("report_file", help="research campaign JSON report")
    check = sub.add_parser("check-certificate", help="check a saved standalone JSON proof artifact")
    check.add_argument("artifact", help="JSON with statement and certificate fields")
    lean = sub.add_parser("lean-verify", help="invoke real Lean 4 on a saved, certified theorem")
    lean.add_argument("artifact", help="JSON object containing exact statement and certificate")
    lean.add_argument("--project-root", default=".")
    lean.add_argument("--output", help="path to full source-bound verification record JSON")
    lean.add_argument("--source", help="path to generated Lean proof source (pending until checker accepts)")
    lean.add_argument("--timeout", type=int, default=120)
    batch = sub.add_parser("lean-verify-report", help="run bounded Lean checks over an audited campaign")
    batch.add_argument("report_file")
    batch.add_argument("--project-root", default=".")
    batch.add_argument("--output-dir", default="research/lean_verified")
    batch.add_argument("--limit", type=int, default=10)
    batch.add_argument("--timeout", type=int, default=120)
    formal_audit = sub.add_parser("audit-lean-results", help="replay campaign and audit Lean result source binding")
    formal_audit.add_argument("report_file")
    formal_audit.add_argument("result_dir")
    formal_audit.add_argument("--require-complete", action="store_true")
    nt = sub.add_parser("nt-run", help="create or resume typed elementary number-theory campaign")
    nt.add_argument("--db", default="research/number_theory.sqlite3")
    nt.add_argument("--report", default="research/number_theory_latest.json")
    nt.add_argument("--seed", type=int, default=42)
    nt.add_argument("--candidates", type=int, default=200)
    nt.add_argument("--lower", type=int, default=-8)
    nt.add_argument("--upper", type=int, default=8)
    nt.add_argument("--max-evals", type=int, default=300)
    nt.add_argument("--step-limit", type=int, default=None)
    nta = sub.add_parser("nt-audit", help="replay number-theory campaign and verify all evidence")
    nta.add_argument("report_file")
    ntc = sub.add_parser("nt-check-certificate", help="check integer polynomial divisibility certificate")
    ntc.add_argument("artifact")
    ntl = sub.add_parser("nt-lean-verify", help="check number-theory certificate using actual Lean kernel")
    ntl.add_argument("artifact")
    ntl.add_argument("--project-root", default=".")
    ntl.add_argument("--output")
    ntl.add_argument("--source")
    ntl.add_argument("--timeout", type=int, default=120)
    ntb = sub.add_parser("nt-lean-verify-report", help="submit audited number-theory research proofs to Lean")
    ntb.add_argument("report_file")
    ntb.add_argument("--project-root", default=".")
    ntb.add_argument("--output-dir", default="research/lean_verified/number_theory")
    ntb.add_argument("--limit", type=int, default=20)
    ntb.add_argument("--timeout", type=int, default=120)
    seq = sub.add_parser("nt-sequence-run", help="explore and certify modular periodicity of order-two recurrences")
    seq.add_argument("--seed", type=int, default=42)
    seq.add_argument("--budget", type=int, default=30)
    seq.add_argument("--report", default="research/sequence_latest.json")
    seq_audit = sub.add_parser("nt-sequence-audit", help="replay independent finite-state recurrence certificates")
    seq_audit.add_argument("report_file")
    ntfa = sub.add_parser("nt-audit-lean-results", help="replay original number-theory candidates against saved Lean records")
    ntfa.add_argument("report_file")
    ntfa.add_argument("result_dir")
    ntfa.add_argument("--expected-attempts", type=int, default=None)
    ntfa.add_argument("--require-verified", action="store_true")
    graph = sub.add_parser("graph-run", help="research exact finite simple-graph conjectures")
    graph.add_argument("--db", default="research/graphs/axiom_graphs.sqlite3")
    graph.add_argument("--report", default="research/graphs/latest.json")
    graph.add_argument("--seed", type=int, default=42)
    graph.add_argument("--candidates", type=int, default=240)
    graph.add_argument("--max-order", type=int, default=6)
    graph.add_argument("--search-budget", type=int, default=128)
    graph.add_argument("--step-limit", type=int, default=None)
    graph_audit = sub.add_parser("graph-audit", help="independently replay graph experiment and certificates")
    graph_audit.add_argument("report_file")
    graph_cert = sub.add_parser("graph-check-certificate", help="recheck finite proof over all labelled graphs")
    graph_cert.add_argument("artifact")
    graph_enum = sub.add_parser("graph-enumerate", help="enumerate exact graph isomorphism classes for n<=5")
    graph_enum.add_argument("--max-order", type=int, default=5)
    graph_hist = sub.add_parser("graph-count", help="independently check binomial edge histograms for n<=5")
    graph_hist.add_argument("--max-order", type=int, default=5)
    knowledge = sub.add_parser("knowledge-build", help="import audited graph research into the cumulative knowledge graph")
    knowledge.add_argument("reports", nargs="+", help="complete v0.5 graph campaign reports")
    knowledge.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    kn_audit = sub.add_parser("knowledge-audit", help="replay and audit ALL persisted graph evidence")
    kn_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    kn_query = sub.add_parser("knowledge-query", help="query statements and evidence without upgrading proof status")
    kn_query.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    kn_query.add_argument("--template")
    kn_query.add_argument("--order", type=int)
    kn_query.add_argument("--status")
    kn_query.add_argument("--limit", type=int, default=20)
    kn_neighbors = sub.add_parser("knowledge-neighbors", help="inspect auditable proof, checker and analogue links")
    kn_neighbors.add_argument("node_id")
    kn_neighbors.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    kn_neighbors.add_argument("--limit", type=int, default=100)
    federation = sub.add_parser("knowledge-federate", help="attach audited algebra/number-theory/recurrence evidence to v0.6 graph DB")
    federation.add_argument("reports", nargs="+", help="complete historical domain-specific campaign reports")
    federation.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    fed_audit = sub.add_parser("knowledge-federation-audit", help="replay all native source auditors and verify the typed federation")
    fed_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    fed_q = sub.add_parser("knowledge-cross-query", help="query domain-separated mathematical findings")
    fed_q.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    fed_q.add_argument("--domain", choices=("graph", "algebra", "number_theory", "recurrence"))
    fed_q.add_argument("--status")
    fed_q.add_argument("--limit", type=int, default=20)
    fed_q.add_argument("--replay-lean", action="store_true",
                       help="kernel-check audited formal records for the selected statements")
    fed_q.add_argument("--project-root", default=".")
    fed_q.add_argument("--timeout", type=int, default=180)
    form_imp = sub.add_parser("knowledge-formal-import", help="source-bind preserved complete Lean records; no offline formal promotion")
    form_imp.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    form_imp.add_argument("--algebra-ndjson")
    form_imp.add_argument("--number-index")
    form_imp.add_argument("--number-records-dir")
    form_audit = sub.add_parser("knowledge-formal-audit", help="replay complete research and Lean source-record lineage")
    form_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    form_q = sub.add_parser("knowledge-formal-query", help="query exact source-bound Lean evidence (execution not independently attested)")
    form_q.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    form_q.add_argument("--domain", choices=("algebra", "number_theory"))
    form_q.add_argument("--limit", type=int, default=20)
    form_replay = sub.add_parser("knowledge-formal-replay",
                                 help="recheck audited historical proof records in pinned Lean")
    form_replay.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    form_replay.add_argument("--project-root", default=".")
    form_replay.add_argument("--timeout", type=int, default=180)
    graph_frontier = sub.add_parser(
        "graph-frontier-run",
        help="boundedly falsify n=6/7 graph conjectures motivated by n=5 finite proofs")
    graph_frontier.add_argument("reports", nargs="+", help="complete v0.5 source graph campaigns")
    graph_frontier.add_argument("--output", default="research/graphs/v09_frontier_report.json")
    graph_frontier.add_argument("--target-order", type=int, choices=(6, 7), default=6)
    graph_frontier.add_argument("--search-budget", type=int, default=512)
    graph_frontier.add_argument("--max-candidates", type=int, default=200)
    graph_frontier.add_argument("--seed", type=int, default=42)
    graph_frontier_audit = sub.add_parser(
        "graph-frontier-audit", help="independently replay a bounded n=6/7 frontier report")
    graph_frontier_audit.add_argument("report", help="saved research frontier JSON")
    graph_frontier_audit.add_argument("reports", nargs="+", help="original source graph campaigns")
    agenda = sub.add_parser("knowledge-plan", help="derive reproducible evidence-gated next research actions")
    agenda.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    agenda.add_argument("--domain", choices=("graph", "algebra", "number_theory", "recurrence"))
    agenda.add_argument("--limit", type=int, default=30)
    agenda.add_argument("--offset", type=int, default=0,
                        help="skip earlier ranked tasks; supports complete paged exploration")
    agenda.add_argument("--output", help="optional deterministic research agenda JSON artifact")
    agenda_audit = sub.add_parser("knowledge-plan-audit", help="replay all sources and audit a saved agenda")
    agenda_audit.add_argument("report_file")
    agenda_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    frontier_import = sub.add_parser(
        "knowledge-frontier-import",
        help="import fully replayed n=6/7 bounded graph experiments into separate evidence overlay")
    frontier_import.add_argument("reports", nargs="+", help="v0.9 exact source-bound frontier reports")
    frontier_import.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    frontier_audit = sub.add_parser(
        "knowledge-frontier-audit", help="independently recheck all imported graph frontier findings")
    frontier_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    frontier_query = sub.add_parser(
        "knowledge-frontier-query", help="query typed n=6/7 experimental evidence with provenance")
    frontier_query.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    frontier_query.add_argument("--order", type=int, choices=(6, 7))
    frontier_query.add_argument("--status", choices=("REFUTED", "EXPERIMENTALLY_SUPPORTED"))
    frontier_query.add_argument("--offset", type=int, default=0)
    frontier_query.add_argument("--limit", type=int, default=20)
    n6run = sub.add_parser(
        "graph-n6-run", help="exhaustively examine 32768 labelled simple graphs at exactly n=6")
    n6run.add_argument("--templates", nargs="+",
                       help="closed list of supported structural claim templates")
    n6run.add_argument("--output", default="research/graphs/n6_exact_report.json")
    n6audit = sub.add_parser(
        "graph-n6-audit", help="independently replay all exact-n6 finite proofs and refutations")
    n6audit.add_argument("report_file")
    n6cert = sub.add_parser(
        "graph-n6-check-certificate",
        help="independently check a saved exact-six-vertex finite proof certificate")
    n6cert.add_argument("artifact")
    exact_import = sub.add_parser(
        "knowledge-exact-n6-import",
        help="index fully independently checked n=6 certificates without touching historical evidence")
    exact_import.add_argument("reports", nargs="+", help="complete exact-n6 source reports")
    exact_import.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    exact_audit = sub.add_parser(
        "knowledge-exact-n6-audit", help="replay all source mathematics, frontier experiments and finite n=6 certificates")
    exact_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    exact_query = sub.add_parser(
        "knowledge-exact-n6-query", help="inspect independently audited exact n=6 proofs and refutations")
    exact_query.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    exact_query.add_argument("--status", choices=("REFUTED", "PROVED_IN_SUPPORTED_FRAGMENT"))
    exact_query.add_argument("--offset", type=int, default=0)
    exact_query.add_argument("--limit", type=int, default=20)
    reconciled = sub.add_parser(
        "knowledge-graph-plan",
        help="plan next graph research using full source-replayed exact n6 proofs and bounded frontier")
    reconciled.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    reconciled.add_argument("--order", type=int, choices=range(8))
    reconciled.add_argument("--limit", type=int, default=30)
    reconciled.add_argument("--offset", type=int, default=0)
    reconciled.add_argument("--output")
    reconciled_audit = sub.add_parser(
        "knowledge-graph-plan-audit", help="replay all exact/bounded graph evidence and audit graph plan")
    reconciled_audit.add_argument("report_file")
    reconciled_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    graph_lean = sub.add_parser(
        "graph-n6-lean-verify", help="kernel-verify one independently audited exact n6 graph proof")
    graph_lean.add_argument("artifact", help="JSON {statement,certificate} exact six-vertex artifact")
    graph_lean.add_argument("--project-root", default=".")
    graph_lean.add_argument("--output")
    graph_lean.add_argument("--source")
    graph_lean.add_argument("--timeout", type=int, default=180)
    graph_exec = sub.add_parser(
        "graph-lean-autopilot",
        help="execute supported formalization tasks from full source-replayed graph research agenda")
    graph_exec.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    graph_exec.add_argument("--output-dir", default="research/lean_verified/graph_n6")
    graph_exec.add_argument("--project-root", default=".")
    graph_exec.add_argument("--max-proofs", type=int, default=3)
    graph_exec.add_argument("--timeout", type=int, default=180)
    graph_exec_audit = sub.add_parser(
        "graph-lean-autopilot-audit",
        help="replay source-bound graph Lean records, without attesting offline execution")
    graph_exec_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    graph_exec_audit.add_argument("output_dir")
    cycle = sub.add_parser(
        "graph-research-cycle",
        help="execute source-replayed Lean proofs and independent n7 falsification in separate evidence lanes")
    cycle.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    cycle.add_argument("--output-dir", default="research/research_cycles")
    cycle.add_argument("--project-root", default=".")
    cycle.add_argument("--proof-quota", type=int, default=3)
    cycle.add_argument("--experiment-quota", type=int, default=2)
    cycle.add_argument("--search-budget", type=int, default=64)
    cycle.add_argument("--seed", type=int, default=42)
    cycle.add_argument("--timeout", type=int, default=240)
    cycle_audit = sub.add_parser(
        "graph-research-cycle-audit",
        help="replay proof source bindings, independent graph samples, and evidence hash chain")
    cycle_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    cycle_audit.add_argument("run_dir")
    advance = sub.add_parser(
        "graph-research-advance",
        help="run an incremental nonduplicative n7 falsification iteration using source-replayed evidence")
    advance.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    advance.add_argument("--output-dir", default="research/knowledge/novel_runs")
    advance.add_argument("--iteration", type=int, default=0)
    advance.add_argument("--seed", type=int, default=42)
    advance.add_argument("--search-budget", type=int, default=64)
    advance.add_argument("--task-limit", type=int, default=2)
    advance_audit = sub.add_parser(
        "graph-research-advance-audit",
        help="independently replay historical masks and a linked series of research iterations")
    advance_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    advance_audit.add_argument("report_file")
    discovery = sub.add_parser(
        "graph-research-discover",
        help="source-probed adaptive seven-vertex candidate discovery and bounded testing")
    discovery.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    discovery.add_argument("--output", default="research/knowledge/discovery_v017.json")
    discovery.add_argument("--seed", type=int, default=42)
    discovery.add_argument("--source-probe", type=int, default=96)
    discovery.add_argument("--experiment-budget", type=int, default=48)
    discovery.add_argument("--task-limit", type=int, default=4)
    discovery_audit = sub.add_parser(
        "graph-research-discover-audit",
        help="replay and independently audit source-probed candidate selection")
    discovery_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    discovery_audit.add_argument("report_file")
    synth = sub.add_parser(
        "graph-synthesize",
        help="synthesize affine graph conjectures with source-audited training and sealed holdout")
    synth.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    synth.add_argument("--output", default="research/knowledge/affine_synthesis_v018.json")
    synth.add_argument("--seed", type=int, default=42)
    synth.add_argument("--n6-training", type=int, default=64)
    synth.add_argument("--n7-training", type=int, default=64)
    synth.add_argument("--holdout-budget", type=int, default=32)
    synth.add_argument("--max-candidates", type=int, default=4)
    synth_audit = sub.add_parser(
        "graph-synthesize-audit",
        help="replay mathematical source and test affine conjecture synthesis and holdout evidence")
    synth_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    synth_audit.add_argument("report_file")
    strata = sub.add_parser(
        "graph-stratified-followup",
        help="source-audited premise-aware independent holdout for v0.18 affine conjectures")
    strata.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    strata.add_argument("--parent", required=True,
                        help="immutable v0.18 source-replayable synthesis report")
    strata.add_argument("--output", default="research/knowledge/stratified_followup_v019.json")
    strata.add_argument("--seed", type=int, default=43)
    strata.add_argument("--budget", type=int, default=24)
    strata.add_argument("--max-proposals", type=int, default=20000)
    strata_audit = sub.add_parser(
        "graph-stratified-audit",
        help="independently replay source, parent synthesis and stratified holdout")
    strata_audit.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    strata_audit.add_argument("--parent", required=True)
    strata_audit.add_argument("report_file")
    affine_lean = sub.add_parser(
        "graph-affine-n3-lean",
        help="execute the real pinned Lean checker on supported exact-n3 affine graph statements")
    affine_lean.add_argument("statement_file", help="typed affine conjecture JSON")
    affine_lean.add_argument("--project-root", default=".")
    affine_lean.add_argument("--timeout", type=int, default=180)
    affine_lean.add_argument("--source")
    affine_lean.add_argument("--output")
    affine_lean_audit = sub.add_parser(
        "graph-affine-n3-lean-audit",
        help="audit exact-n3 Lean source integrity without claiming offline execution attestation")
    affine_lean_audit.add_argument("record_file")
    guided = sub.add_parser(
        "graph-synthesize-guided",
        help="run v0.19 assumption-aware n7 source-disjoint graph holdout")
    guided.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    guided.add_argument("--output", default="research/knowledge/guided_v019.json")
    guided.add_argument("--seed", type=int, default=42)
    guided.add_argument("--n6-training", type=int, default=64)
    guided.add_argument("--n7-training", type=int, default=64)
    guided.add_argument("--holdout-budget", type=int, default=24)
    guided.add_argument("--max-candidates", type=int, default=4)
    ga = sub.add_parser(
        "graph-synthesize-guided-audit",
        help="replay and audit complete v0.19 assumption-aware experiment")
    ga.add_argument("--db", default="research/knowledge/axiom.sqlite3")
    ga.add_argument("report_file")
    affine = sub.add_parser(
        "graph-affine-lean-verify",
        help="execute real Lean kernel on only closed-form exact-n6 affine envelope proofs")
    affine.add_argument("artifact")
    affine.add_argument("--project-root", default=".")
    affine.add_argument("--timeout", type=int, default=240)
    affine.add_argument("--output")
    affine.add_argument("--source")
    aa = sub.add_parser(
        "graph-affine-lean-audit",
        help="offline source audit of exact-n6 affine Lean result (NOT kernel reexecution)")
    aa.add_argument("report_file")
    proof = sub.add_parser("graph-prove", help="search and Lean-check a canonical graph relation")
    proof.add_argument("statement_file")
    proof.add_argument("--project-root", default=".")
    proof.add_argument("--timeout", type=int, default=180)
    proof.add_argument("--max-lemmas", type=int, default=3)
    proof.add_argument("--max-coefficient", type=int, default=3)
    proof.add_argument("--max-nodes", type=int, default=10_000)
    proof.add_argument("--retrieve-lemmas", type=int, default=0, metavar="K",
                       help="retry exhausted composition with up to K pinned Mathlib adapters")
    proof.add_argument("--retrieval-index", choices=("v1", "v2", "v3", "v4", "v5", "v6", "v7"), default="v1",
                       help="select the Mathlib retrieval index version")
    proof.add_argument("--synthesize-lemmas", type=int, default=0, metavar="K",
                       help="retry exhausted search with up to K projected intermediate lemmas")
    proof.add_argument("--split-order", action="store_true",
                       help="retry with a checked split between zero and positive order")
    proof.add_argument("--induct-edges", action="store_true",
                       help="retry with a bound certified by strong induction on the number of edges")
    proof.add_argument("--proof-plans", type=int, default=0, metavar="K",
                       help="try up to K ranked Lean tactic plans after composition exhausts search")
    hint_mode = proof.add_mutually_exclusive_group()
    hint_mode.add_argument("--proof-hint-context", action="store_true",
                           help="export the eligible facts and hint schema without invoking Lean")
    hint_mode.add_argument("--proof-hints", metavar="FILE",
                           help="try statement-bound JSON fact bundles in the proof plan fallback")
    proof.add_argument("--witness-order", type=int, default=5)
    proof.add_argument("--external-witness", metavar="FILE")
    proof.add_argument("--output")
    proof.add_argument("--source")
    proof_audit = sub.add_parser("graph-prove-audit", help="replay proof evidence integrity offline")
    proof_audit.add_argument("report_file")
    witness = sub.add_parser("graph-witness", help="independently certify an explicit counterexample")
    witness.add_argument("statement_file")
    witness.add_argument("graph_file")
    witness.add_argument("--origin", required=True)
    witness.add_argument("--minimize", action="store_true")
    active = sub.add_parser("graph-active-refute", help="search typed affine counterexamples by graph mutation")
    active.add_argument("statement_file")
    active.add_argument("seed_graphs_file", help="JSON array of explicit-order graphs")
    active.add_argument("--seed", type=int, default=42)
    active.add_argument("--budget", type=int, default=1000)
    active.add_argument("--beam", type=int, default=8)
    transfer = sub.add_parser("graph-transfer-check", help="evaluate a typed literature claim exactly")
    transfer.add_argument("statement_file")
    transfer.add_argument("graph_file")
    corpus = sub.add_parser("graph-corpus-screen", help="refute a typed claim on a canonical graph corpus")
    corpus.add_argument("statement_file")
    corpus.add_argument("--db", required=True)
    corpus.add_argument("--split", choices=("development", "validation", "final"), default="development")
    corpus.add_argument("--exact-budget", type=int, default=1000)
    for command, help_text in (
        ("graph-discover", "synthesize and test affine graph relations in a persistent campaign"),
        ("graph-discover-audit", "replay a campaign and its predecessor history"),
        ("graph-discover-lean", "send audited discovery survivors to the real fixed-order Lean checker"),
        ("graph-discover-universal", "send audited survivors to supported all-order Lean proofs"),
        ("graph-discover-universal-audit", "replay all-order proof dispatch and audit its evidence"),
        ("graph-discover-benchmark", "measure deterministic candidate replay and report its workload"),
    ):
        discovery = sub.add_parser(command, help=help_text)
        discovery.add_argument("--db", required=True, help="existing historical evidence database")
        discovery.add_argument("--ledger", required=True, help="separate SQLite holdout ledger")
        discovery.add_argument("--campaign", required=True)
        discovery.add_argument("--legacy-v18")
        discovery.add_argument("--legacy-guided")
        discovery.add_argument("--legacy-stratified")
        if command == "graph-discover":
            discovery.add_argument("--seed", type=int, default=42)
            discovery.add_argument("--n6-training", type=int, default=64)
            discovery.add_argument("--n7-training", type=int, default=64)
            discovery.add_argument("--holdout-budget", type=int, default=24)
            discovery.add_argument("--max-candidates", type=int, default=4)
            from .graph_novelty import PROFILES

            discovery.add_argument("--novelty-profile", choices=PROFILES,
                                   help="check exact implications against a versioned graph fact bank")
            discovery.add_argument("--proof-beam", type=int, default=0,
                                   help="opt in to the four-term candidate lane at this beam width")
        elif command == "graph-discover-audit":
            discovery.add_argument("--artifact", help="compare an exported report with replay")
        elif command in ("graph-discover-lean", "graph-discover-universal"):
            discovery.add_argument("--project-root", default=".")
            discovery.add_argument("--timeout", type=int, default=180)
        elif command == "graph-discover-universal-audit":
            discovery.add_argument("--artifact", required=True)
        if command == "graph-discover-universal":
            discovery.add_argument("--proof-profile",
                                   choices=("extended", "structural", "matching", "components",
                                            "component-independence", "matching-cardinality", "clique-independence"),
                                   help="use the extended proof engine on the audited selections")
            discovery.add_argument("--proof-hints", metavar="FILE",
                                   help="statement-bound campaign hint manifest for the chosen profile")
        if command in ("graph-discover-universal", "graph-discover-universal-audit"):
            discovery.add_argument("--compose", action="store_true",
                                   help="use the bounded multi-lemma proof engine")
    args = p.parse_args()
    if args.command == "graph-active-refute":
        from pathlib import Path
        from .graph_active_refute import search
        from .graph_explicit import ExplicitGraph
        from .graph_relations import AffineRelation

        try:
            claim = AffineRelation.from_dict(json.loads(Path(args.statement_file).read_bytes()))
            candidates = json.loads(Path(args.seed_graphs_file).read_bytes())
            if type(candidates) is not list:
                raise ValueError("expected an array of seed graphs")
            report = search(claim, [ExplicitGraph.from_dict(data) for data in candidates],
                            seed=args.seed, budget=args.budget, beam=args.beam)
            print(json.dumps(report, indent=2, sort_keys=True))
        except (ValueError, OSError, TypeError, KeyError) as error:
            p.exit(2, f"REJECTED: {error}\n")
        return
    if args.command == "graph-transfer-check":
        from pathlib import Path
        from .graph_explicit import ExplicitGraph
        from .graph_transfer import TransferStatement, check, replay

        try:
            statement = TransferStatement.from_dict(json.loads(Path(args.statement_file).read_bytes()))
            graph = ExplicitGraph.from_dict(json.loads(Path(args.graph_file).read_bytes()))
            result = check(statement, graph)
            replay(statement, result)
            print(json.dumps(result, indent=2, sort_keys=True))
        except (ValueError, OSError, TypeError, KeyError) as error:
            p.exit(2, f"REJECTED: {error}\n")
        return
    if args.command == "graph-corpus-screen":
        from pathlib import Path
        import sqlite3
        from .graph_corpus import screen
        from .graph_relations import AffineRelation

        try:
            claim = AffineRelation.from_dict(json.loads(Path(args.statement_file).read_bytes()))
            report = screen(args.db, claim, args.exact_budget, split=args.split)
            print(json.dumps(report, indent=2, sort_keys=True))
        except (ValueError, OSError, TypeError, KeyError, sqlite3.Error) as error:
            p.exit(2, f"REJECTED: {error}\n")
        return
    if args.command == "graph-witness":
        from pathlib import Path
        from .graph_explicit import ExplicitGraph
        from .graph_large_witness import certify_witness, minimize_witness
        from .graph_relations import AffineRelation

        try:
            claim = AffineRelation.from_dict(json.loads(Path(args.statement_file).read_bytes()))
            path = Path(args.graph_file)
            graph = (ExplicitGraph.from_graph6(path.read_text(encoding="ascii"))
                     if path.suffix == ".g6" else ExplicitGraph.from_dict(json.loads(path.read_bytes())))
            if args.minimize:
                graph = minimize_witness(claim, graph)
            report = certify_witness(claim, graph, origin=args.origin)
            print(json.dumps(report, indent=2, sort_keys=True))
        except (ValueError, OSError, TypeError, KeyError) as error:
            p.exit(2, f"REJECTED: {error}\n")
        return
    if args.command in {"graph-prove", "graph-prove-audit"}:
        from pathlib import Path
        from .graph_lemma_retrieval import (
            CLIQUE_INDEPENDENCE_INDEX, COMPONENT_INDEX, COMPONENT_INDEPENDENCE_INDEX, INDEX_VERSION,
            MATCHING_CARDINALITY_INDEX,
            MATCHING_INDEX, STRUCTURAL_INDEX,
        )
        from .graph_proof import audit, hint_context, prove
        from .graph_proof_hints import read_hints
        from .graph_proof_search import SearchLimits

        try:
            if args.command == "graph-prove-audit":
                record = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
                audit(record)
                print(json.dumps({"audit": "PASSED", "execution_attested": False}))
                return
            if args.output and args.source and Path(args.output).resolve() == Path(args.source).resolve():
                raise ValueError("JSON evidence and Lean source require distinct paths")
            statement = json.loads(Path(args.statement_file).read_text(encoding="utf-8"))
            indexes = {"v1": INDEX_VERSION, "v2": STRUCTURAL_INDEX, "v3": MATCHING_INDEX,
                       "v4": COMPONENT_INDEX, "v5": COMPONENT_INDEPENDENCE_INDEX,
                       "v6": MATCHING_CARDINALITY_INDEX, "v7": CLIQUE_INDEPENDENCE_INDEX}
            options = dict(witness_order=args.witness_order, retrieval_limit=args.retrieve_lemmas,
                           retrieval_index=indexes[args.retrieval_index],
                           synthesis_limit=args.synthesize_lemmas, split_order=args.split_order,
                           induct_edges=args.induct_edges, plan_limit=args.proof_plans,
                           limits=SearchLimits(args.max_lemmas, args.max_coefficient, args.max_nodes))
            if args.proof_hint_context:
                if args.source or args.external_witness:
                    raise ValueError("proof hint context accepts neither source output nor a witness")
                record = hint_context(statement, **options)
            else:
                hints = read_hints(args.proof_hints) if args.proof_hints is not None else None
                external = json.loads(Path(args.external_witness).read_bytes()) if args.external_witness else None
                record = prove(statement, **options, project_root=args.project_root,
                               timeout=args.timeout, proof_hints=hints, external_witness=external)
            text = json.dumps(record, indent=2, sort_keys=True) + "\n"
            if args.output:
                path = Path(args.output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
            if args.source and record["generated"] is not None:
                path = Path(args.source)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(record["generated"]["source"], encoding="utf-8")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        return
    if args.command in {"graph-discover", "graph-discover-audit",
                        "graph-discover-lean", "graph-discover-benchmark",
                        "graph-discover-universal", "graph-discover-universal-audit"}:
        import sqlite3
        from pathlib import Path

        from .graph_discovery import audit_campaign, benchmark_campaign
        from .graph_discovery import run_campaign as run_graph_discovery
        from .graph_discovery_lean import dispatch_lean
        from .graph_lean import LeanBackendError
        from .graph_universal_lean import audit_dispatch, dispatch_universal
        from .graph_proof_hints import read_hints
        from .graph_proof_pipeline import DISPATCH_SCHEMAS, audit_composed_dispatch, dispatch_composed

        legacy = {key: path for key, path in (
            ("v18", args.legacy_v18), ("guided", args.legacy_guided),
            ("stratified", args.legacy_stratified)) if path is not None}
        params = (args.db, args.ledger, args.campaign)
        try:
            if args.command == "graph-discover":
                result = run_graph_discovery(
                    *params, seed=args.seed, n6_training=args.n6_training,
                    n7_training=args.n7_training, holdout_budget=args.holdout_budget,
                    max_candidates=args.max_candidates, legacy_reports=legacy, proof_beam=args.proof_beam,
                    novelty_profile=args.novelty_profile)
            elif args.command == "graph-discover-audit":
                result = audit_campaign(*params, legacy_reports=legacy, artifact=args.artifact)
            elif args.command == "graph-discover-lean":
                result = dispatch_lean(*params, legacy_reports=legacy,
                                       project_root=args.project_root, timeout=args.timeout)
            elif args.command == "graph-discover-universal":
                options = dict(legacy_reports=legacy, project_root=args.project_root, timeout=args.timeout)
                if args.proof_profile:
                    hints = read_hints(args.proof_hints) if args.proof_hints is not None else None
                    result = dispatch_composed(*params, **options, proof_profile=args.proof_profile,
                                               proof_hints=hints)
                elif args.proof_hints is not None:
                    raise ValueError("campaign proof hints require a non-fixed proof profile")
                else:
                    dispatch = dispatch_composed if args.compose else dispatch_universal
                    result = dispatch(*params, **options)
            elif args.command == "graph-discover-universal-audit":
                artifact = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
                composed = args.compose or (type(artifact) is dict and artifact.get("schema") in DISPATCH_SCHEMAS)
                replay = audit_composed_dispatch if composed else audit_dispatch
                result = replay(*params, artifact, legacy_reports=legacy)
            else:
                result = benchmark_campaign(*params, legacy_reports=legacy)
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError, LeanBackendError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if args.command in {"graph-affine-n3-lean", "graph-affine-n3-lean-audit"}:
        from pathlib import Path
        from .graph_affine_lean_n3 import verify_n3_affine, audit_n3_affine
        from .graph_lean import LeanBackendError
        try:
            if args.command == "graph-affine-n3-lean":
                statement = json.loads(Path(args.statement_file).read_text(encoding="utf-8"))
                record = verify_n3_affine(statement, project_root=args.project_root,
                                          timeout_seconds=args.timeout)
                if args.output:
                    target = Path(args.output)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                                      encoding="utf-8")
                if args.source:
                    target = Path(args.source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(record["source"], encoding="utf-8")
                shown = {key: record[key] for key in (
                    "status", "accepted", "theorem", "formal_scope",
                    "all_order_generalization", "lean_kernel_executed", "axioms")}
                print(json.dumps(shown, indent=2, sort_keys=True))
                if not record["accepted"]:
                    p.exit(1)
            else:
                record = json.loads(Path(args.record_file).read_text(encoding="utf-8"))
                audit_n3_affine(record)
                print(json.dumps({
                    "audit": "SOURCE_BINDING_ACCEPTED",
                    "offline_audit_is_execution_attestation": False,
                    "theorem": record["theorem"],
                    "all_order_generalization": "NOT_PROVED",
                }, sort_keys=True, indent=2))
        except (LeanBackendError, ValueError, KeyError, TypeError,
                OSError, json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        return

    if args.command in {"graph-stratified-followup", "graph-stratified-audit"}:
        from .graph_stratified import save_followup, audit_followup
        import sqlite3
        try:
            if args.command == "graph-stratified-followup":
                record = save_followup(
                    args.db, args.parent, args.output,
                    seed=args.seed, budget=args.budget,
                    max_proposals=args.max_proposals)
                shown = {
                    "schema": record["schema"],
                    "source_fingerprint": record["historical_source_fingerprint"],
                    "parent_sha256": record["parent_report_sha256"],
                    "checked_new_graphs": record["new_distinct_masks_checked"],
                    "independently_verified_counterexamples":
                        record["independently_verified_counterexamples"],
                    "formally_verified": 0, "output": args.output,
                }
            else:
                record = audit_followup(args.db, args.parent, args.report_file)
                shown = {k: v for k, v in record.items() if k != "report"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return

    if args.command in {"graph-synthesize-guided", "graph-synthesize-guided-audit"}:
        from .graph_guided import save_guided, audit_guided
        import sqlite3
        try:
            if args.command == "graph-synthesize-guided":
                report = save_guided(
                    args.db, args.output, seed=args.seed,
                    n6_training=args.n6_training, n7_training=args.n7_training,
                    holdout_budget=args.holdout_budget,
                    max_candidates=args.max_candidates)
                shown = {
                    "schema": report["schema"], "output": args.output,
                    "source_fingerprint": report["source_fingerprint"],
                    "generated": report["generated_canonical_candidates"],
                    "selected": len(report["selected"]),
                    "holdout_graphs": report["guided_holdout"]["distinct_new_graphs_checked"],
                    "refutations": report["guided_holdout"]["refutations"],
                    "nonvacuous_survivals": report["guided_holdout"]["nonvacuous_survivals"],
                    "lean_formal_verification": "NOT_PERFORMED",
                }
            else:
                result = audit_guided(args.db, args.report_file)
                shown = {key: val for key, val in result.items() if key != "report"}
        except (ValueError, KeyError, TypeError, OSError,
                json.JSONDecodeError, sqlite3.DatabaseError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return
    if args.command in {"graph-affine-lean-verify", "graph-affine-lean-audit"}:
        from pathlib import Path
        from .graph_affine_lean import (
            verify_affine_lean, audit_affine_lean_record,
            save_affine_lean_record,
        )
        from .lean_backend import LeanBackendError
        try:
            if args.command == "graph-affine-lean-verify":
                payload = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
                if type(payload) is not dict or set(payload) != {"statement"}:
                    raise ValueError("affine proof input requires only a typed statement")
                record = verify_affine_lean(
                    payload["statement"], project_root=args.project_root,
                    timeout_seconds=args.timeout)
                audit_affine_lean_record(record)
                if args.output:
                    save_affine_lean_record(record, args.output)
                if args.source:
                    target = Path(args.source)
                    if target.exists():
                        raise ValueError("Lean source output is immutable")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("x", encoding="utf-8") as stream:
                        stream.write(record["source"])
                shown = {
                    "status": record["status"], "accepted": record["accepted"],
                    "scope": record["claim_scope"],
                    "all_orders_verified": False,
                    "axioms": record["axioms"],
                    "lean_version": record["lean_version"],
                }
            else:
                record = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
                audit_affine_lean_record(record)
                shown = {
                    "audit": "SOURCE_REPLAY_ACCEPTED",
                    "kernel_reexecution_performed": False,
                    "status": record["status"], "accepted": record["accepted"],
                    "scope": record["claim_scope"],
                    "all_orders_verified": False,
                }
        except (LeanBackendError, ValueError, KeyError, TypeError,
                OSError, json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        if args.command == "graph-affine-lean-verify" and not record["accepted"]:
            p.exit(1)
        return

    if args.command in {"graph-synthesize", "graph-synthesize-audit"}:
        from .graph_synthesis import save_synthesis, audit_synthesis
        import sqlite3
        try:
            if args.command == "graph-synthesize":
                record = save_synthesis(
                    args.db, args.output, seed=args.seed,
                    n6_training=args.n6_training, n7_training=args.n7_training,
                    holdout_budget=args.holdout_budget,
                    max_candidates=args.max_candidates)
                shown = {
                    "schema": record["schema"],
                    "output": args.output,
                    "source_fingerprint": record["source_fingerprint"],
                    "candidate_count": record["synthesis"]["canonical_candidates_generated"],
                    "selected_count": len(record["synthesis"]["selected"]),
                    "holdout_graphs": record["holdout"]["distinct_graphs_checked"],
                    "holdout_refutations": record["holdout"]["refutations"],
                    "holdout_survivals": record["holdout"]["survivals"],
                    "lean_obligations_pending": len(record["lean_handoff"]),
                    "formally_verified": 0,
                }
            else:
                result = audit_synthesis(args.db, args.report_file)
                shown = {k: v for k, v in result.items() if k != "report"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return

    if args.command in {"graph-research-discover", "graph-research-discover-audit"}:
        from .graph_adaptive import save_discovery, audit_discovery
        import sqlite3
        try:
            if args.command == "graph-research-discover":
                result = save_discovery(
                    args.db, args.output, seed=args.seed,
                    source_probe=args.source_probe,
                    experiment_budget=args.experiment_budget,
                    task_limit=args.task_limit)
                shown = {
                    "schema": result["schema"],
                    "source_fingerprint": result["source_fingerprint"],
                    "candidate_count": result["candidate_bank"]["candidate_count"],
                    "eligible_count": result["candidate_bank"]["eligible_count"],
                    "new_graphs": result["new_distinct_masks_checked"],
                    "new_refutations": result["new_refutations"],
                    "experimental_survivals": result["experimental_survivals"],
                    "formal_kernel_executed": False,
                    "output": args.output,
                }
            else:
                result = audit_discovery(args.db, args.report_file)
                shown = {k: v for k, v in result.items() if k != "report"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return

    if args.command in {"graph-research-advance", "graph-research-advance-audit"}:
        from .graph_nonduplicate import run_iteration, audit_iteration
        import sqlite3
        try:
            if args.command == "graph-research-advance":
                report = run_iteration(
                    args.db, args.output_dir, iteration=args.iteration,
                    seed=args.seed, search_budget=args.search_budget,
                    task_limit=args.task_limit)
                shown = {
                    "schema": report["schema"],
                    "source_fingerprint": report["source_fingerprint"],
                    "configuration": report["configuration"],
                    "attempted": report["attempted"],
                    "refutations": report["refutations"],
                    "bounded_survivals": report["bounded_survivals"],
                    "new_masks_checked": report["new_masks_checked"],
                    "historical_source_modified": False,
                    "formal_lean_verification": "NOT_PERFORMED",
                }
            else:
                report = audit_iteration(args.db, args.report_file)
                shown = {k: v for k, v in report.items() if k != "report"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return

    if args.command in {"graph-research-cycle", "graph-research-cycle-audit"}:
        from .graph_research_cycle import execute_cycle, audit_cycle
        import sqlite3
        try:
            if args.command == "graph-research-cycle":
                result = execute_cycle(
                    args.db, args.output_dir, project_root=args.project_root,
                    proof_quota=args.proof_quota,
                    experiment_quota=args.experiment_quota,
                    search_budget=args.search_budget, seed=args.seed,
                    timeout_seconds=args.timeout)
                shown = {
                    "run_id": result["run_id"],
                    "source_fingerprint": result["source_fingerprint"],
                    "formal": result["formal"],
                    "bounded": result["bounded"],
                    "offline_replay_is_kernel_attestation": False,
                }
            else:
                result = audit_cycle(args.db, args.run_dir)
                shown = {k: v for k, v in result.items() if k != "report"}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(shown, sort_keys=True, indent=2))
        return

    if args.command in {"graph-n6-lean-verify", "graph-lean-autopilot",
                        "graph-lean-autopilot-audit"}:
        from pathlib import Path
        import sqlite3
        from .graph_lean import (
            verify_graph_with_lean, save_record, LeanBackendError)
        from .graph_research_executor import (
            execute_graph_research, audit_executor_report)
        try:
            if args.command == "graph-n6-lean-verify":
                data = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
                if type(data) is not dict or set(data) != {"statement", "certificate"}:
                    raise ValueError("expected exact graph proof artifact")
                report = verify_graph_with_lean(
                    data["statement"], data["certificate"],
                    project_root=args.project_root, timeout_seconds=args.timeout)
                if args.output:
                    save_record(report, args.output)
                if args.source:
                    dest = Path(args.source)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(report["source"], encoding="utf-8")
                success = report["accepted"]
            elif args.command == "graph-lean-autopilot":
                report = execute_graph_research(
                    args.db, args.output_dir,
                    project_root=args.project_root, max_proofs=args.max_proofs,
                    timeout_seconds=args.timeout)
                success = report["formally_verified"] == report["attempted"]
            else:
                report = audit_executor_report(args.db, args.output_dir)
                success = True
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError, LeanBackendError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        if args.command == "graph-n6-lean-verify":
            shown = {k: report[k] for k in (
                "status", "accepted", "theorem", "lean_version", "axioms")}
        elif args.command == "graph-lean-autopilot":
            shown = {k: report[k] for k in (
                "source_fingerprint", "candidate_count", "attempted",
                "formally_verified", "pending")}
        else:
            shown = report
        print(json.dumps(shown, indent=2, sort_keys=True))
        if not success:
            p.exit(1)
        return

    if args.command in {"knowledge-graph-plan", "knowledge-graph-plan-audit"}:
        from .knowledge_graph_plan import (
            graph_research_plan, write_graph_plan, audit_graph_plan)
        import sqlite3
        try:
            if args.command == "knowledge-graph-plan-audit":
                result = audit_graph_plan(args.db, args.report_file)
            elif args.output:
                result = write_graph_plan(
                    args.db, args.output, order=args.order,
                    limit=args.limit, offset=args.offset)
            else:
                result = graph_research_plan(
                    args.db, order=args.order, limit=args.limit, offset=args.offset)
        except (ValueError, KeyError, TypeError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"knowledge-exact-n6-import", "knowledge-exact-n6-audit",
                        "knowledge-exact-n6-query"}:
        from .knowledge_exact_n6 import import_exact_n6, exact_n6_summary, query_exact_n6
        import sqlite3
        try:
            if args.command == "knowledge-exact-n6-import":
                result = import_exact_n6(args.db, args.reports)
            elif args.command == "knowledge-exact-n6-audit":
                result = exact_n6_summary(args.db)
            else:
                result = {"statements": query_exact_n6(
                    args.db, status=args.status, offset=args.offset, limit=args.limit)}
        except (ValueError, KeyError, TypeError, OSError,
                sqlite3.DatabaseError, json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"graph-n6-run", "graph-n6-audit",
                        "graph-n6-check-certificate"}:
        from .graph_n6_exact import (
            research_n6, audit_n6, save_n6, check_n6_certificate,
            DEFAULT_TEMPLATES)
        try:
            if args.command == "graph-n6-run":
                report = research_n6(
                    args.templates if args.templates is not None else
                    list(DEFAULT_TEMPLATES))
                save_n6(report, args.output)
                result = {"schema": report["schema"],
                          "output": args.output,
                          "campaign_id": report["campaign_id"],
                          "counts": report["counts"],
                          "labelled_graphs_per_statement": 32768,
                          "formal_lean_verification": "NOT_PERFORMED"}
            elif args.command == "graph-n6-audit":
                with open(args.report_file, "r", encoding="utf-8") as stream:
                    result = audit_n6(json.load(stream))
            else:
                with open(args.artifact, "r", encoding="utf-8") as stream:
                    artifact = json.load(stream)
                if type(artifact) is not dict or set(artifact) != {
                        "statement", "certificate"}:
                    raise ValueError("n6 proof artifact must contain statement and certificate")
                check_n6_certificate(artifact["statement"], artifact["certificate"])
                result = {"audit": "ACCEPTED", "exact_graph_order": 6,
                          "labelled_graphs_exhaustively_checked": 32768,
                          "formal_lean_verification": "NOT_PERFORMED",
                          "all_order_generalization": "NOT_PROVED"}
        except (ValueError, TypeError, KeyError, OSError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"knowledge-frontier-import", "knowledge-frontier-audit",
                        "knowledge-frontier-query"}:
        from .frontier_lineage import (
            import_frontier_lineage, frontier_lineage_summary, query_frontier_lineage)
        import sqlite3
        try:
            if args.command == "knowledge-frontier-import":
                result = import_frontier_lineage(args.db, args.reports)
            elif args.command == "knowledge-frontier-audit":
                result = frontier_lineage_summary(args.db)
            else:
                result = {"statements": query_frontier_lineage(
                    args.db, order=args.order, status=args.status,
                    offset=args.offset, limit=args.limit)}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"knowledge-plan", "knowledge-plan-audit"}:
        from .knowledge_agenda import research_agenda, write_agenda, audit_agenda
        import sqlite3
        try:
            if args.command == "knowledge-plan-audit":
                result = audit_agenda(args.db, args.report_file)
            elif args.output:
                result = write_agenda(args.db, args.output,
                                      domain=args.domain, limit=args.limit,
                                      offset=args.offset)
            else:
                result = research_agenda(args.db, domain=args.domain,
                                         limit=args.limit, offset=args.offset)
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"graph-frontier-run", "graph-frontier-audit"}:
        from .graph_frontier import (
            run_frontier, audit_frontier, load_graph_sources)
        import sqlite3
        try:
            if args.command == "graph-frontier-run":
                result = run_frontier(args.reports, output=args.output,
                                      seed=args.seed, target_order=args.target_order,
                                      search_budget=args.search_budget,
                                      max_candidates=args.max_candidates)
                result = {"schema": result["schema"],
                          "campaign_id": result["campaign_id"],
                          "output": args.output, "counts": result["counts"],
                          "candidates": result["candidate_count"],
                          "proofs_at_target_order": 0}
            else:
                with open(args.report, "r", encoding="utf-8") as source_file:
                    report = json.load(source_file)
                result = audit_frontier(
                    report, load_graph_sources(args.reports))
        except (ValueError, KeyError, OSError, TypeError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"knowledge-formal-import", "knowledge-formal-audit",
                        "knowledge-formal-query", "knowledge-formal-replay"}:
        from .formal_provenance import import_formal, formal_summary, formal_query
        import sqlite3
        try:
            if args.command == "knowledge-formal-import":
                result = import_formal(args.db, algebra_ndjson=args.algebra_ndjson,
                                       number_index=args.number_index,
                                       number_records_dir=args.number_records_dir)
            elif args.command == "knowledge-formal-audit":
                result = formal_summary(args.db)
            elif args.command == "knowledge-formal-replay":
                from .formal_replay import replay_formal
                result = replay_formal(args.db, project_root=args.project_root,
                                       timeout_seconds=args.timeout)
            else:
                result = {"records": formal_query(
                    args.db, domain=args.domain, limit=args.limit)}
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command in {"knowledge-federate", "knowledge-federation-audit", "knowledge-cross-query"}:
        from .knowledge_federation import federate, federation_summary, query_federation
        import sqlite3
        try:
            if args.command == "knowledge-federate":
                result = federate(args.db, args.reports)
            elif args.command == "knowledge-federation-audit":
                result = federation_summary(args.db)
            else:
                result = {"statements": query_federation(
                    args.db, domain=args.domain, status=args.status,
                    limit=args.limit)}
                if args.replay_lean:
                    from .formal_replay import add_replayed_evidence
                    result = add_replayed_evidence(args.db, result["statements"],
                                                   project_root=args.project_root,
                                                   timeout_seconds=args.timeout)
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if args.command in {"knowledge-build", "knowledge-audit", "knowledge-query", "knowledge-neighbors"}:
        import sqlite3
        from .knowledge_graph import (build_knowledge_graph, knowledge_summary,
                                      query_knowledge, knowledge_neighbors)
        try:
            if args.command == "knowledge-build":
                result = build_knowledge_graph(args.db, args.reports)
            elif args.command == "knowledge-audit":
                result = knowledge_summary(args.db)
            elif args.command == "knowledge-query":
                result = {"statements": query_knowledge(
                    args.db, template=args.template, order=args.order,
                    status=args.status, limit=args.limit)}
            else:
                result = knowledge_neighbors(args.db, args.node_id, limit=args.limit)
        except (ValueError, TypeError, KeyError, OSError, sqlite3.DatabaseError,
                json.JSONDecodeError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, sort_keys=True, indent=2))
        return

    if args.command == "graph-count":
        from .graph_combinatorics import edge_count_histogram, check_edge_count_histogram
        if not 0<=args.max_order<=5:
            p.exit(2, "REJECTED: finite graph count capped at n=5\n")
        histograms = []
        for n in range(args.max_order+1):
            record=edge_count_histogram(n)
            check_edge_count_histogram(record)
            histograms.append(record)
        print(json.dumps({"histograms":histograms,"proof_scope":"exact fixed finite n<=5",
                          "lean_formal_verification":"NOT_PERFORMED"},indent=2))
        return
    if args.command == "graph-run":
        from .graph_campaign import run_graph_campaign
        try:
            report = run_graph_campaign(args.db,seed=args.seed,candidates=args.candidates,
                max_order=args.max_order,search_budget=args.search_budget,
                step_limit=args.step_limit,report_path=args.report)
        except (ValueError, TypeError, KeyError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps({"campaign_id":report["campaign_id"],"progress":report["progress"],
                          "counts":report["counts"],"measurement":report["measurement"],
                          "report":args.report},indent=2))
        return
    if args.command == "graph-audit":
        from pathlib import Path
        from .graph_campaign import audit_graph_report
        try:
            report = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
            counts = audit_graph_report(report)
        except (ValueError, TypeError, KeyError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps({"outcome":"ACCEPTED","counts":counts,
                          "lean_formal_verification":"NOT_PERFORMED"},indent=2))
        return
    if args.command == "graph-check-certificate":
        from pathlib import Path
        from .graph_checker import check_finite_certificate
        try:
            artifact = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
            if type(artifact) is not dict or set(artifact)!={"statement","certificate"}:
                raise ValueError("artifact must contain statement and certificate")
            check_finite_certificate(artifact['statement'],artifact['certificate'])
        except (ValueError, TypeError, KeyError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print("ACCEPTED: exhaustive fixed-order finite graph proof; NOT Lean formally verified")
        return
    if args.command == "graph-enumerate":
        from .graph_model import isomorphism_representatives
        if not 0<=args.max_order<=5:
            p.exit(2, "REJECTED: exact isomorphism enumeration capped at n=5\n")
        print(json.dumps({"unlabeled_simple_graphs":
            {n:len(isomorphism_representatives(n)) for n in range(args.max_order+1)}},indent=2))
        return
    if args.command == "nt-audit-lean-results":
        from pathlib import Path
        from .number_theory_lean import audit_nt_lean_report
        try:
            source=json.loads(Path(args.report_file).read_text(encoding='utf-8'))
            result=audit_nt_lean_report(source,args.result_dir,
                expected_attempts=args.expected_attempts,require_verified=args.require_verified)
        except (ValueError,TypeError,KeyError,RecursionError,OSError) as exc:
            p.exit(2,f"REJECTED: {exc}\n")
        print(json.dumps(result,indent=2,sort_keys=True))
        return
    if args.command == "nt-sequence-run":
        from pathlib import Path
        from .recurrences import sequence_campaign, audit_sequence_campaign
        report=sequence_campaign(args.seed,args.budget)
        audit_sequence_campaign(report)
        target=Path(args.report);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"budget":args.budget,"independently_checked_periodicity_certificates":len(report['findings']),
                          "formal_verification":"NOT_EXECUTED","report":str(target)},indent=2))
        return
    if args.command == "nt-sequence-audit":
        from pathlib import Path
        from .recurrences import audit_sequence_campaign
        try:
            report=json.loads(Path(args.report_file).read_text(encoding='utf-8'))
            audit_sequence_campaign(report)
        except (ValueError,TypeError,KeyError,RecursionError,OSError) as exc:
            p.exit(2,f"REJECTED: {exc}\n")
        print(json.dumps({"outcome":"ACCEPTED","certificates":len(report['findings']),
                          "formal_verification":"NOT_EXECUTED"},indent=2))
        return
    if args.command == "nt-run":
        from .number_theory_campaign import run_nt_campaign
        result = run_nt_campaign(args.db,seed=args.seed,candidates=args.candidates,
                                 lower=args.lower,upper=args.upper,max_evals=args.max_evals,
                                 step_limit=args.step_limit,report_path=args.report)
        print(json.dumps({"campaign_id":result["campaign_id"],"progress":result["progress"],
                          "counts":result["counts"],"measurement":result["measurement"],
                          "report":args.report},indent=2))
        return
    if args.command == "nt-audit":
        from pathlib import Path
        from .number_theory_campaign import audit_nt_report
        try:
            report=json.loads(Path(args.report_file).read_text(encoding="utf-8"))
            counts=audit_nt_report(report)
        except (ValueError,TypeError,KeyError,RecursionError,OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps({"outcome":"ACCEPTED","counts":counts,
                          "formal_verification":"NOT_PERFORMED"},indent=2))
        return
    if args.command == "nt-check-certificate":
        from pathlib import Path
        from .number_theory_checker import check_nt_certificate
        try:
            artifact=json.loads(Path(args.artifact).read_text(encoding="utf-8"))
            if not isinstance(artifact,dict) or set(artifact)!={"statement","certificate"}:
                raise ValueError("artifact must contain statement and certificate")
            check_nt_certificate(artifact['statement'],artifact['certificate'])
        except (ValueError,TypeError,KeyError,RecursionError,OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print("ACCEPTED: independently checked Z-polynomial factor certificate (not Lean)")
        return
    if args.command == "nt-lean-verify":
        from pathlib import Path
        from .number_theory_lean import verify_nt_with_lean
        from .lean_backend import LeanBackendError
        try:
            artifact=json.loads(Path(args.artifact).read_text(encoding="utf-8"))
            if not isinstance(artifact,dict) or set(artifact)!={"statement","certificate"}:
                raise ValueError("artifact must contain statement and certificate")
            result=verify_nt_with_lean(artifact['statement'],artifact['certificate'],
                                       project_root=args.project_root,timeout_seconds=args.timeout)
        except (ValueError,TypeError,KeyError,RecursionError,OSError,LeanBackendError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        if args.output:
            path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        if args.source:
            path=Path(args.source);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(result['source'],encoding="utf-8")
        print(json.dumps({k:result[k] for k in ("status","accepted","theorem","lean_version","axioms")},indent=2))
        if not result['accepted']:
            p.exit(1)
        return
    if args.command == "nt-lean-verify-report":
        from pathlib import Path
        from .number_theory_lean import verify_nt_report
        try:
            report=json.loads(Path(args.report_file).read_text(encoding="utf-8"))
            summary=verify_nt_report(report,project_root=args.project_root,
                                     output_dir=args.output_dir,limit=args.limit,
                                     timeout_seconds=args.timeout)
        except (ValueError,TypeError,KeyError,RecursionError,OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps({k:summary[k] for k in ("campaign_id","attempted","formally_verified")},indent=2))
        if summary['attempted']!=summary['formally_verified']:
            p.exit(1)
        return
    if args.command == "audit-lean-results":
        from .formal_campaign import audit_formal_report
        from .lean_backend import LeanBackendError
        try:
            result = audit_formal_report(args.report_file, result_dir=args.result_dir,
                                          require_complete=args.require_complete)
        except (LeanBackendError, ValueError, KeyError, TypeError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if args.command == "lean-verify-report":
        from .formal_campaign import verify_report_proofs
        from .lean_backend import LeanBackendError
        try:
            summary = verify_report_proofs(args.report_file, project_root=args.project_root,
                                           output_dir=args.output_dir, limit=args.limit,
                                           timeout_seconds=args.timeout)
        except (LeanBackendError, ValueError, KeyError, TypeError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        print(json.dumps({k: summary[k] for k in ("origin_campaign_id", "attempted", "formally_verified", "duration_seconds")}, indent=2))
        if summary['formally_verified'] != summary['attempted']:
            p.exit(1)
        return
    if args.command == "lean-verify":
        from pathlib import Path
        from .lean_backend import verify_saved_artifact, LeanBackendError
        try:
            result = verify_saved_artifact(args.artifact, project_root=args.project_root,
                                           timeout_seconds=args.timeout)
        except (LeanBackendError, ValueError, KeyError, TypeError, RecursionError, OSError) as exc:
            p.exit(2, f"REJECTED: {exc}\n")
        if args.output:
            dest = Path(args.output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.source:
            dest = Path(args.source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(result["source"], encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("status", "accepted", "theorem", "lean_version", "axioms", "duration_seconds")}, indent=2))
        if not result["accepted"]:
            p.exit(1)
        return
    if args.command == "audit-report":
        from pathlib import Path
        from .evidence import audit_report
        try:
            record = json.loads(Path(args.report_file).read_text(encoding="utf-8"))
            counts = audit_report(record)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            p.exit(1, f"REJECTED: {exc}\n")
        print(json.dumps({"outcome": "ACCEPTED", "audited_findings": len(record["findings"]),
                          "counts": counts, "formal_verification": "NOT_PERFORMED"}, indent=2))
        return
    if args.command == "check-certificate":
        from pathlib import Path
        from .certificate_checker import check_certificate, CertificateError
        try:
            record = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
            if not isinstance(record, dict) or set(record) != {"statement", "certificate"}:
                raise CertificateError("expected statement and certificate")
            check_certificate(record["statement"], record["certificate"])
        except (CertificateError, ValueError, TypeError, RecursionError) as exc:
            p.exit(1, f"REJECTED: {exc}\n")
        print("ACCEPTED: locally checked algebraic proof certificate; not Lean formal verification")
        return
    report = run_campaign(args.db, args.seed, args.candidates, args.domain, args.lower,
                          args.upper, args.max_evals, args.step_limit, args.report)
    print(json.dumps({"campaign_id": report["campaign_id"], "progress": report["progress"],
                      "counts": {k: v for k, v in report["counts"].items() if v},
                      "measurement": report["measurement"], "report": args.report}, indent=2))


if __name__ == "__main__":
    main()
