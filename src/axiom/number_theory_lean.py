"""Lean 4 kernel adapter for certified integer divisibility/congruence fragment.

A congruence a ≡ b (mod m), m>0, is formalized as m ∣ (a-b) in Int.
Every accepted quotient certificate yields a witness of the integer div relation.
Only an actual Lean compiler invocation with audited transitive axioms may mark
an artifact FORMALLY_VERIFIED; generated text itself remains unverified.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any
from .certificate_checker import CertificateError
from .number_theory_checker import check_nt_certificate, digest
from .number_theory_model import NTStatement
from .lean_backend import (_expr, _poly, _num, _axiom_report, _toolchain_matches,
                           _dependency_manifest, ALLOWED_AXIOMS, LEAN_VERSION,
                           MATHLIB_REV, TOOLCHAIN, VERSION_RE, MAX_LOG_BYTES,
                           MAX_SOURCE_BYTES, LeanBackendError)

SOURCE_SCHEMA = 'axiom.lean4.number_theory.source.v1'
RESULT_SCHEMA = 'axiom.lean4.number_theory.verification.v1'


def build_nt_lean_source(statement: dict, certificate: dict) -> dict[str, Any]:
    try:
        check_nt_certificate(statement,certificate)
        stmt=NTStatement.from_dict(statement)
    except (CertificateError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise LeanBackendError('untrusted or invalid number theory certificate') from exc
    theorem='axiom_nt_'+digest(statement)[:24]
    names=stmt.variables
    variables=' '.join(f'({name} : Int)' for name in names)
    bounded=' '.join(f'(h{idx} : {_num(lo)} ≤ {n} ∧ {n} ≤ {_num(hi)})'
                     for idx,(n,lo,hi) in enumerate(stmt.bounds))
    if stmt.relation=='divides':
        proposition=f'{_expr(stmt.lhs)} ∣ {_expr(stmt.rhs)}'
    else:
        proposition=f'{_num(stmt.modulus)} ∣ ({_expr(stmt.lhs)} - {_expr(stmt.rhs)})'
    quotient=_poly(certificate['quotient'],names)
    source=(f'-- Generated from separately checked AXIOM integer-polynomial factor certificate.\n'
            f'-- Statement SHA-256: {digest(statement)}\n'
            f'import Mathlib.Tactic.Ring\n\n'
            f'theorem {theorem} {variables}'+(f' {bounded}' if bounded else '')+
            f' : {proposition} := by\n'
            f'  refine ⟨{quotient}, ?_⟩\n'
            f'  ring\n\n#print axioms {theorem}\n')
    if len(source.encode('utf-8'))>MAX_SOURCE_BYTES:
        raise LeanBackendError('generated Lean source exceeds size limit')
    return {'schema':SOURCE_SCHEMA,'statement':statement,'statement_sha256':digest(statement),
            'certificate':certificate,'theorem':theorem,'method':'integer_polynomial_multiple',
            'assumptions':list(stmt.bounds),'imports':['Mathlib.Tactic.Ring'],
            'source':source,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'toolchain':TOOLCHAIN,'mathlib_rev':MATHLIB_REV,
            'formalization':('Int divisibility' if stmt.relation=='divides'
                             else 'Int congruence via (m ∣ a-b), m>0')}


def verify_nt_with_lean(statement: dict, certificate: dict, *,
                        project_root: str | Path, timeout_seconds: int = 120) -> dict[str,Any]:
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=1200:
        raise LeanBackendError('invalid Lean timeout')
    src=build_nt_lean_source(statement,certificate)
    root=Path(project_root).expanduser().resolve()
    record={'schema':RESULT_SCHEMA,'status':'VERIFICATION_PENDING','accepted':False,
            'theorem':src['theorem'],'statement':statement,'certificate':certificate,
            'statement_sha256':src['statement_sha256'], 'source':src['source'],
            'source_sha256':src['source_sha256'],'assumptions':src['assumptions'],
            'formalization':src['formalization'],'imports':src['imports'],
            'expected_toolchain':TOOLCHAIN,'mathlib_rev':MATHLIB_REV,
            'toolchain_file_matches':_toolchain_matches(root),
            'dependency_manifest_sha256':None,'mathlib_revision':None,
            'lean_version':None,'axioms':None,'checker_exit_code':None,
            'stdout_sha256':None,'stderr_excerpt':'','duration_seconds':None,
            'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'command':['lake','env','lean']}
    if not record['toolchain_file_matches']:
        record['status']='CONFIGURATION_MISSING';return record
    if shutil.which('lake') is None:
        record['status']='LEAN_UNAVAILABLE';return record
    begin=time.perf_counter()
    try:
        deps=_dependency_manifest(root)
        record['dependency_manifest_sha256']=deps['manifest_sha256']
        record['mathlib_revision']=deps['mathlib_revision']
        if not deps['mathlib_revision']:
            record['status']='DEPENDENCY_MANIFEST_MISSING';return record
        version=subprocess.run(['lake','env','lean','--version'],cwd=root,
                               capture_output=True,text=True,timeout=min(30,timeout_seconds),check=False)
        match=VERSION_RE.search(version.stdout)
        if version.returncode!=0 or not match:
            record['status']='VERSION_CHECK_FAILED';record['stderr_excerpt']=(version.stderr or version.stdout)[:1024];return record
        record['lean_version']=match.group(1)
        if match.group(1)!=LEAN_VERSION:
            record['status']='VERSION_MISMATCH';return record
        with tempfile.TemporaryDirectory(prefix='axiom-nt-lean-') as temp:
            source=Path(temp)/(src['theorem']+'.lean')
            source.write_text(src['source'],encoding='utf-8')
            check=subprocess.run(['lake','env','lean',str(source)],cwd=root,
                                 capture_output=True,text=True,timeout=timeout_seconds,check=False)
        record['checker_exit_code']=check.returncode
        record['stdout_sha256']=hashlib.sha256(check.stdout.encode()).hexdigest()
        record['stderr_excerpt']=check.stderr[-2048:]
        if (len(check.stdout.encode())>MAX_LOG_BYTES or
                len(check.stderr.encode())>MAX_LOG_BYTES):
            record['status']='OUTPUT_LIMIT_EXCEEDED'
        elif check.returncode!=0 or check.stderr.strip():
            record['status']='CHECKER_FAILED'
        else:
            record['axioms']=_axiom_report(check.stdout,src['theorem'])
            if record['axioms'] is None:
                record['status']='AXIOM_AUDIT_MISSING'
            elif not set(record['axioms']).issubset(ALLOWED_AXIOMS):
                record['status']='UNTRUSTED_AXIOMS'
            else:
                record['status']='FORMALLY_VERIFIED';record['accepted']=True
    except (LeanBackendError, ValueError, KeyError, TypeError) as exc:
        record['status']='DEPENDENCY_MANIFEST_INVALID';record['stderr_excerpt']=str(exc)[:512]
    except subprocess.TimeoutExpired:
        record['status']='CHECKER_TIMEOUT'
    except OSError as exc:
        record['status']='CHECKER_IO_ERROR';record['stderr_excerpt']=str(exc)[:512]
    finally:
        record['duration_seconds']=round(time.perf_counter()-begin,6)
    return record


def verify_nt_record_integrity(record: dict) -> bool:
    """Offline record binding audit, NOT cryptographic proof of historical CI execution."""
    if not isinstance(record,dict) or record.get('schema')!=RESULT_SCHEMA:
        raise LeanBackendError('invalid formal number theory record schema')
    expected=build_nt_lean_source(record['statement'],record['certificate'])
    for k,v in (('statement_sha256',expected['statement_sha256']),
                ('source',expected['source']),('source_sha256',expected['source_sha256']),
                ('imports',expected['imports']),('theorem',expected['theorem']),
                ('assumptions',expected['assumptions']),('formalization',expected['formalization']),
                ('expected_toolchain',TOOLCHAIN),('mathlib_rev',MATHLIB_REV)):
        if record.get(k)!=v:
            raise LeanBackendError('source-bound Lean evidence mismatch: '+k)
    if record.get('status')=='FORMALLY_VERIFIED':
        if (record.get('accepted') is not True or record.get('checker_exit_code')!=0 or
                record.get('lean_version')!=LEAN_VERSION or
                record.get('toolchain_file_matches') is not True or
                not isinstance(record.get('dependency_manifest_sha256'),str) or
                not isinstance(record.get('mathlib_revision'),str) or len(record['mathlib_revision'])!=40 or
                not isinstance(record.get('stdout_sha256'),str) or
                not isinstance(record.get('axioms'),list) or
                not set(record['axioms']).issubset(ALLOWED_AXIOMS)):
            raise LeanBackendError('inconsistent kernel verification declaration')
    elif record.get('accepted') is not False:
        raise LeanBackendError('invalid pending/rejected acceptance pair')
    return True


def verify_nt_report(report: dict,*,project_root: str | Path,
                     output_dir: str | Path,limit: int=20,timeout_seconds: int=120) -> dict:
    from .number_theory_campaign import audit_nt_report
    counts=audit_nt_report(report)
    if type(limit) is not int or not 1<=limit<=1000:
        raise LeanBackendError('invalid batch limit')
    path=Path(output_dir);path.mkdir(parents=True,exist_ok=True)
    findings=[f for f in report['findings'] if f['status']=='PROVED_IN_SUPPORTED_FRAGMENT'][:limit]
    records=[]
    for finding in findings:
        candidate_id=finding['candidate_id']
        record=verify_nt_with_lean(finding['statement'],finding['proof']['certificate'],
                                   project_root=project_root,timeout_seconds=timeout_seconds)
        verify_nt_record_integrity(record)
        (path/(candidate_id[:24]+'.json')).write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        records.append({'candidate_id':candidate_id,'theorem':record['theorem'],
                        'status':record['status'],'accepted':record['accepted']})
    summary={'schema':'axiom.number_theory.lean_batch.v1','campaign_id':report['campaign_id'],
             'candidates_tested':len(report['findings']),'locally_proved':counts['PROVED_IN_SUPPORTED_FRAGMENT'],
             'attempted':len(records),'formally_verified':sum(r['accepted'] for r in records),
             'results':records}
    (path/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return summary
