"""Offline Lean provenance lineage: authenticated source matching, not execution attestation."""
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import pytest

from axiom.knowledge_graph import build_knowledge_graph, knowledge_summary
from axiom.knowledge_federation import federate, federation_summary
from axiom.formal_provenance import import_formal, formal_summary, formal_query

ROOT = Path(__file__).parents[1]
ALGEBRA = ROOT / "research/v03_formal_results.ndjson"
NT_INDEX = ROOT / "research/number_theory/v04_formal_results.ndjson"
NT_DIR = ROOT / "research/lean_verified/number_theory"


@pytest.fixture(scope="module")
def prepared_db(tmp_path_factory):
    root = tmp_path_factory.mktemp("formal-source")
    db = str(root / "knowledge.sqlite3")
    build_knowledge_graph(db, [
        str(ROOT / "research/graphs/v05_baseline_report.json"),
        str(ROOT / "research/graphs/v05_scale_report.json")])
    federate(db, [
        str(ROOT / "research/v03_campaign_report.json"),
        str(ROOT / "research/number_theory/v04_report.json"),
        str(ROOT / "research/number_theory/v04_sequences.json")])
    return db


@pytest.fixture
def cloned_db(tmp_path, prepared_db):
    db = str(tmp_path / "clone.sqlite3")
    src = sqlite3.connect(prepared_db)
    dst = sqlite3.connect(db)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    return db


@pytest.fixture
def small_records(tmp_path):
    algebra_lines = ALGEBRA.read_text().splitlines()[:2]
    nt_lines = NT_INDEX.read_text().splitlines()[:2]
    ap = tmp_path / "algebra.ndjson"
    np = tmp_path / "nt.ndjson"
    ap.write_text("\n".join(algebra_lines) + "\n")
    np.write_text("\n".join(nt_lines) + "\n")
    return ap, np


def test_lineage_idempotence_and_no_formal_promotion(cloned_db, small_records):
    ap, np = small_records
    a = import_formal(cloned_db, algebra_ndjson=str(ap),
                      number_index=str(np), number_records_dir=str(NT_DIR))
    b = import_formal(cloned_db, algebra_ndjson=str(ap),
                      number_index=str(np), number_records_dir=str(NT_DIR))
    assert a == b
    assert a["audit"] == "ACCEPTED"
    assert a["historical_full_records_source_bound"] == 4
    assert a["records_by_domain"] == {"algebra": 2, "number_theory": 2}
    assert a["external_lean_execution_attestation"] == "NOT_ESTABLISHED_BY_OFFLINE_AUDIT"
    assert a["knowledge_graph_status_upgrades"] == 0
    results = formal_query(cloned_db, domain="number_theory")
    assert len(results) == 2
    assert all(row["status"] == "SOURCE_BOUND_OFFLINE_ONLY" for row in results)
    assert all(row["declared_kernel_status"] == "FORMALLY_VERIFIED" for row in results)
    assert all(row["external_execution_attestation"] ==
               "NOT_ESTABLISHED_BY_OFFLINE_AUDIT" for row in results)
    assert knowledge_summary(cloned_db)["audit"] == "ACCEPTED"
    assert federation_summary(cloned_db)["audit"] == "ACCEPTED"


def test_invalid_import_inputs_do_not_modify_db(cloned_db, small_records, tmp_path):
    ap, np = small_records
    with pytest.raises(ValueError):
        import_formal(cloned_db, number_index=str(np))
    bogus = tmp_path / "not_here"
    with pytest.raises(ValueError):
        import_formal(cloned_db, number_index=str(np),
                      number_records_dir=str(bogus))
    assert formal_summary(cloned_db)["historical_full_records_source_bound"] == 0


def test_tampered_historical_lean_source_rejected(cloned_db, small_records, tmp_path):
    ap, _ = small_records
    record = json.loads(ap.read_text().splitlines()[0])
    record["source"] += "\n-- forged change\n"
    fake = tmp_path / "forged.ndjson"
    fake.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError):
        import_formal(cloned_db, algebra_ndjson=str(fake))
    assert formal_summary(cloned_db)["historical_full_records_source_bound"] == 0


def test_downgraded_or_mismatched_origin_rejected(cloned_db, small_records, tmp_path):
    ap, _ = small_records
    record = json.loads(ap.read_text().splitlines()[0])
    record["origin_candidate_id"] = "f" * 64
    fake = tmp_path / "unknown.ndjson"
    fake.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError):
        import_formal(cloned_db, algebra_ndjson=str(fake))
    record = json.loads(ap.read_text().splitlines()[0])
    record["status"] = "VERIFICATION_PENDING"
    fake.write_text(json.dumps(record) + "\n")
    with pytest.raises(ValueError):
        import_formal(cloned_db, algebra_ndjson=str(fake))


def test_missing_number_record_and_tampered_index(cloned_db, small_records, tmp_path):
    _, np = small_records
    empty = tmp_path / "full_records"
    empty.mkdir()
    with pytest.raises(ValueError, match="missing or unsafe"):
        import_formal(cloned_db, number_index=str(np), number_records_dir=str(empty))
    meta = json.loads(np.read_text().splitlines()[0])
    meta["source_sha256"] = "0" * 64
    fake = tmp_path / "corrupt.nt"
    fake.write_text(json.dumps(meta) + "\n")
    with pytest.raises(ValueError, match="disagree"):
        import_formal(cloned_db, number_index=str(fake), number_records_dir=str(NT_DIR))
    meta = json.loads(np.read_text().splitlines()[0])
    meta["evidence_path"] = "forged_folder/" + meta["candidate_id"][:24] + ".json"
    fake.write_text(json.dumps(meta) + "\n")
    with pytest.raises(ValueError, match="campaign/path mismatch"):
        import_formal(cloned_db, number_index=str(fake), number_records_dir=str(NT_DIR))


def test_changed_source_snapshot_is_rejected(cloned_db, small_records, tmp_path):
    ap, _ = small_records
    import_formal(cloned_db, algebra_ndjson=str(ap))
    doc = json.loads(ap.read_text().splitlines()[0])
    changed = tmp_path / "different.ndjson"
    changed.write_text(json.dumps(doc) + "\n")
    with pytest.raises(ValueError, match="immutable"):
        import_formal(cloned_db, algebra_ndjson=str(changed))


def test_integrity_checks_tampered_links_and_batches(cloned_db, small_records):
    ap, np = small_records
    import_formal(cloned_db, algebra_ndjson=str(ap),
                  number_index=str(np), number_records_dir=str(NT_DIR))
    with sqlite3.connect(cloned_db) as db:
        db.execute("UPDATE formal_links SET evidence_json='{}' WHERE "
                   "record_id=(SELECT record_id FROM formal_links LIMIT 1)")
    with pytest.raises(ValueError, match="differs"):
        formal_summary(cloned_db)
    with pytest.raises(ValueError):
        import_formal(cloned_db, algebra_ndjson=str(ap))


def test_deleting_derived_links_does_not_repair(cloned_db, small_records):
    ap, _ = small_records
    import_formal(cloned_db, algebra_ndjson=str(ap))
    with sqlite3.connect(cloned_db) as db:
        db.execute("DELETE FROM formal_links")
    with pytest.raises(ValueError):
        formal_summary(cloned_db)
    with pytest.raises(ValueError):
        import_formal(cloned_db, algebra_ndjson=str(ap))


def test_cli_formal_evidence_import_audit_and_query(cloned_db, small_records):
    ap, np = small_records
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    base = [sys.executable, "-m", "axiom"]

    def cli(*args):
        return subprocess.run(base + list(args), capture_output=True, text=True, env=env)

    written = cli("knowledge-formal-import", "--db", cloned_db,
                  "--algebra-ndjson", str(ap), "--number-index", str(np),
                  "--number-records-dir", str(NT_DIR))
    assert written.returncode == 0, written.stderr
    assert json.loads(written.stdout)["historical_full_records_source_bound"] == 4
    inspected = cli("knowledge-formal-query", "--db", cloned_db,
                    "--domain", "algebra", "--limit", "2")
    assert inspected.returncode == 0, inspected.stderr
    assert len(json.loads(inspected.stdout)["records"]) == 2
    audited = cli("knowledge-formal-audit", "--db", cloned_db)
    assert audited.returncode == 0, audited.stderr
    rejected = cli("knowledge-formal-query", "--db", cloned_db,
                   "--domain", "graph")
    assert rejected.returncode != 0
