from __future__ import annotations
import argparse
import json
from .research import run_campaign


def main() -> None:
    p = argparse.ArgumentParser(prog="axiom", description="AXIOM v0.2 local mathematical research")
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
    args = p.parse_args()
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
