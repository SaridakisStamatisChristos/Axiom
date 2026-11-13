"""Deterministic, self-hashing AXIOM source + research ZIP release builder.

Usage: python scripts/build_release.py --output /mnt/data/AXIOM_v0.4.zip

Includes experimental SQLite evidence and formal JSON proof source. Does not
fabricate test results, and no assertion of kernel correctness follows solely
from a ZIP being built. The archive carries a SHA-256 manifest.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SKIP_DIRECTORIES = {'.git','.venv','venv','__pycache__','.pytest_cache',
                    '.mypy_cache','.ruff_cache','node_modules','.lake','.tox'}
SKIP_FILE_SUFFIXES = {'.pyc','.pyo','.tmp','.swp','.log','.sqlite3-wal','.sqlite3-shm'}
SKIP_NAMES = {'coverage.xml','.coverage','lake-manifest.json'}


def enumerated_files(root: Path, output: Path) -> list[Path]:
    paths=[]
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink() or path.resolve()==output:
            continue
        relative=path.relative_to(root)
        if (any(part in SKIP_DIRECTORIES or part.endswith('.egg-info') for part in relative.parts) or
                relative.name in SKIP_NAMES or any(relative.name.endswith(s) for s in SKIP_FILE_SUFFIXES)):
            continue
        paths.append(path)
    return sorted(paths,key=lambda p:p.relative_to(root).as_posix())


def build(output: Path, root: Path) -> dict:
    root=root.resolve();output=output.expanduser().resolve()
    if output.is_relative_to(root):
        raise ValueError('output archive must be outside project root to avoid recursion')
    if not (root/'pyproject.toml').is_file() or not (root/'CHECKPOINT.md').is_file():
        raise ValueError('project root missing essential checkpoint/manifest')
    output.parent.mkdir(parents=True,exist_ok=True)
    files=enumerated_files(root,output)
    if not files:
        raise ValueError('release would be empty')
    lines=[]
    with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            rel='AXIOM/'+path.relative_to(root).as_posix()
            content=path.read_bytes()
            lines.append(f'{sha256(content).hexdigest()}  {len(content)}  {rel}')
            info=ZipInfo(rel,date_time=(1980,1,1,0,0,0))
            info.compress_type=ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,content,compress_type=ZIP_DEFLATED,compresslevel=9)
        manifest='\n'.join(lines)+'\n'
        info=ZipInfo('AXIOM/RELEASE_MANIFEST.sha256',date_time=(1980,1,1,0,0,0))
        info.external_attr=0o644<<16;info.compress_type=ZIP_DEFLATED
        archive.writestr(info,manifest.encode(),compress_type=ZIP_DEFLATED,compresslevel=9)
    digest=sha256(output.read_bytes()).hexdigest()
    (output.with_suffix(output.suffix+'.sha256')).write_text(digest+'  '+output.name+'\n',encoding='utf-8')
    return {'file_count':len(files),'archive_bytes':output.stat().st_size,
            'archive_sha256':digest,'manifest_entries':len(lines)}


def main() -> None:
    p=argparse.ArgumentParser(description='Deterministic SHA-256 manifested AXIOM release ZIP')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=p.parse_args()
    import json
    print(json.dumps(build(args.output,args.root),sort_keys=True,indent=2))


if __name__=='__main__':
    main()
