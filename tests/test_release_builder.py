import hashlib
import importlib.util
from pathlib import Path
from zipfile import ZipFile
import pytest

MODULE=Path(__file__).resolve().parents[1]/'scripts'/'build_release.py'
spec=importlib.util.spec_from_file_location('release_builder',MODULE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_release_builder_deterministic_and_manifests_files(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'pyproject.toml').write_text('[project]\nname="axiom"\n')
    (root/'CHECKPOINT.md').write_text('checkpoint\n')
    (root/'file.txt').write_text('proof evidence\n')
    (root/'RELEASE_MANIFEST.sha256').write_text('stale previous manifest\n')
    (root/'__pycache__').mkdir();(root/'__pycache__'/'ignored.pyc').write_bytes(b'junk')
    a=tmp_path/'a.zip';b=tmp_path/'b.zip'
    ra=module.build(a,root);rb=module.build(b,root)
    assert a.read_bytes()==b.read_bytes()
    assert ra['file_count']==3 and rb['file_count']==3
    assert ra['archive_sha256']==hashlib.sha256(a.read_bytes()).hexdigest()
    with ZipFile(a) as z:
        assert 'AXIOM/file.txt' in z.namelist()
        assert z.namelist().count('AXIOM/RELEASE_MANIFEST.sha256')==1
        assert 'AXIOM/__pycache__/ignored.pyc' not in z.namelist()
        manifest=z.read('AXIOM/RELEASE_MANIFEST.sha256').decode()
        assert hashlib.sha256(b'proof evidence\n').hexdigest() in manifest


def test_release_builder_rejects_in_root_output(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    (root/'pyproject.toml').write_text('x')
    (root/'CHECKPOINT.md').write_text('x')
    with pytest.raises(ValueError):module.build(root/'bad.zip',root)
