from __future__ import annotations
import argparse
import json
from .research import run_campaign


def main() -> None:
    p = argparse.ArgumentParser(prog="axiom", description="AXIOM v0.6 mathematical research")
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
    args = p.parse_args()
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
