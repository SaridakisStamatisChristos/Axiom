from __future__ import annotations
import argparse
import json
from .research import run_campaign


def main() -> None:
    p = argparse.ArgumentParser(prog="axiom", description="AXIOM v0.12 mathematical research")
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
    args = p.parse_args()
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

    if args.command in {"knowledge-formal-import", "knowledge-formal-audit", "knowledge-formal-query"}:
        from .formal_provenance import import_formal, formal_summary, formal_query
        import sqlite3
        try:
            if args.command == "knowledge-formal-import":
                result = import_formal(args.db, algebra_ndjson=args.algebra_ndjson,
                                       number_index=args.number_index,
                                       number_records_dir=args.number_records_dir)
            elif args.command == "knowledge-formal-audit":
                result = formal_summary(args.db)
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
