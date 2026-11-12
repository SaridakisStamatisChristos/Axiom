import json
import sqlite3
from axiom.research import run_campaign


def signatures(report):
    return [(f["candidate_id"], f["status"], f["search"], f["proof"]) for f in report["findings"]]


def test_resume_and_replay(tmp_path):
    one = tmp_path / "first.db"
    two = tmp_path / "second.db"
    a = run_campaign(str(one), seed=31, candidates=30, step_limit=9)
    assert a["progress"]["cursor"] == 9 and not a["progress"]["complete"]
    b = run_campaign(str(one), seed=31, candidates=30)
    c = run_campaign(str(two), seed=31, candidates=30)
    assert b["progress"]["complete"] and c["progress"]["complete"]
    assert b["progress"] == c["progress"]
    assert signatures(b) == signatures(c)
    assert any(f["status"] == "REFUTED" for f in b["findings"])
    assert any(f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT" for f in b["findings"])
    assert all(f["originality"] == "NOT_ASSESSED" for f in b["findings"])
    assert not any(f["status"] == "FORMALLY_VERIFIED" for f in b["findings"])


def test_persistent_report_and_no_double_count(tmp_path):
    db = tmp_path / "data.db"
    file = tmp_path / "report.json"
    a = run_campaign(str(db), seed=44, candidates=32, domain="mixed", report_path=str(file))
    b = run_campaign(str(db), seed=44, candidates=32, domain="mixed", report_path=str(file))
    assert a["progress"] == b["progress"]
    assert json.loads(file.read_text())["progress"] == b["progress"]
    assert a["counts"].get("EXPERIMENTALLY_SUPPORTED", 0) > 0
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == a["progress"]["unique_candidates"]


def test_bounded_search_not_promoted(tmp_path):
    result = run_campaign(str(tmp_path / "test.db"), seed=42, candidates=50, domain="mixed", max_evals=1)
    for item in result["findings"]:
        if item["statement"]["relation"] == ">=" and item["search"]["counterexample"] is None:
            assert item["status"] == "EXPERIMENTALLY_SUPPORTED"
            assert item["proof"] is None


def test_status_history_and_complexity_rank(tmp_path):
    data = run_campaign(str(tmp_path / "state.db"), seed=4, candidates=60, domain="mixed")
    for f in data["findings"]:
        assert f["history"][0:2] == ["GENERATED", "UNDER_TEST"]
        assert f["history"][-1] == f["status"]
        assert f["ranking_score"] > 0
        if f["status"] == "PROVED_IN_SUPPORTED_FRAGMENT":
            assert "PROOF_CANDIDATE" in f["history"]
            assert "pure_python_sparse_polynomial" in f["proof"]["checks"]
