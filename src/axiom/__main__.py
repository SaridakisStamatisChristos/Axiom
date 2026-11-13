from __future__ import annotations
import argparse
import json
from .research import run_campaign


def main() -> None:
    p = argparse.ArgumentParser(prog="axiom", description="AXIOM v0.3 local mathematical research")
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
    args = p.parse_args()
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
