"""Bounded, auditable Lean proof-checking over an existing mathematical campaign.

This does not mutate the original v0.2 findings: Lean status lives in distinct
records and never overwrites local proof statuses without verified output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from .evidence import audit_report
from .lean_backend import verify_with_lean, verify_record_integrity


def verify_report_proofs(report_file: str | Path, *, project_root: str | Path,
                         output_dir: str | Path, limit: int = 10, timeout_seconds: int = 120) -> dict:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("formal verification batch limit must be 1..100")
    raw = Path(report_file).read_bytes()
    report = json.loads(raw)
    audit_report(report)  # Independently replay all mathematical evidence before dispatch.
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    selected = [f for f in report['findings'] if f['status'] == 'PROVED_IN_SUPPORTED_FRAGMENT'][:limit]
    results = []
    for finding in selected:
        record = verify_with_lean(finding['statement'], finding['proof']['certificate'],
                                  project_root=project_root, timeout_seconds=timeout_seconds)
        verify_record_integrity(record)
        record['origin_campaign_id'] = report['campaign_id']
        record['origin_candidate_id'] = finding['candidate_id']
        record['origin_candidate_status'] = finding['status']
        path = out / (finding['candidate_id'][:24] + '.json')
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        results.append({'candidate_id': finding['candidate_id'], 'status': record['status'],
                        'accepted': record['accepted'], 'record': str(path)})
    summary = {'schema': 'axiom.lean4.batch_report.v1', 'origin_campaign_id': report['campaign_id'],
               'origin_report_sha256': hashlib.sha256(raw).hexdigest(), 'budget': limit,
               'attempted': len(results), 'formally_verified': sum(x['accepted'] for x in results),
               'duration_seconds': round(time.perf_counter()-started, 6), 'results': results,
               'notes': 'Independent Lean verdicts only. Original campaign is unchanged.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return summary
