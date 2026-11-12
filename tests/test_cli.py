import json
import os
import subprocess
import sys


def test_cli_subprocess(tmp_path):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
    output = tmp_path / "output.json"
    result = subprocess.run([sys.executable, "-m", "axiom", "run", "--seed", "1",
                             "--candidates", "12", "--domain", "polynomial", "--db", str(tmp_path / "temp.db"),
                             "--report", str(output)], capture_output=True, text=True, env=env, check=True)
    stdout = json.loads(result.stdout)
    assert stdout["progress"]["complete"]
    assert json.loads(output.read_text())["campaign_id"] == stdout["campaign_id"]


def test_cli_audit_and_certificate_subcommands(tmp_path):
    from axiom.research import run_campaign
    from axiom.certificate_checker import check_certificate
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
    report_file = tmp_path / "v02.json"
    report = run_campaign(str(tmp_path / "db.sqlite3"), seed=101, candidates=28,
                          domain="mixed", report_path=str(report_file))
    cmd = [sys.executable, "-m", "axiom"]
    audit = subprocess.run(cmd + ["audit-report", str(report_file)],
                           capture_output=True, text=True, env=env, check=True)
    assert json.loads(audit.stdout)["outcome"] == "ACCEPTED"
    f = next(item for item in report["findings"] if item["proof"])
    certificate_file = tmp_path / "proof.json"
    certificate_file.write_text(json.dumps({"statement": f["statement"],
                                            "certificate": f["proof"]["certificate"]}))
    assert check_certificate(f["statement"], f["proof"]["certificate"])
    checked = subprocess.run(cmd + ["check-certificate", str(certificate_file)],
                             capture_output=True, text=True, env=env, check=True)
    assert "ACCEPTED" in checked.stdout
