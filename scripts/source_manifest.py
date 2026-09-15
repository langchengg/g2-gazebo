#!/usr/bin/env python3
"""Hash allowlisted project sources, including uncommitted and untracked files.

The runtime scope is identical on Mac, VM and image. Documentation and legacy
sources are included only in the delivery scope. No Git checkout is required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

RUNTIME_ROOTS = ('src', 'docker', 'scripts', 'model_sources')
ROOT_FILES = ('Dockerfile', 'Dockerfile.sim', 'Dockerfile.model-tools', 'compose.yaml', 'compose.sim.yaml', 'Makefile', '.dockerignore')
EXCLUDED = {'__pycache__', '.pytest_cache', 'build', 'install', 'log',
            'sdk', '.cache', '.artifacts', '.git'}


def manifest(root, scope):
    """Hash canonical allowlisted source without depending on Git metadata.

    ``runtime`` binds source to the built image; ``delivery`` additionally covers
    documentation and legacy sources. Symlinks and known binary/secret-bearing
    file types are rejected so a package cannot escape or hide outside the tree.
    """
    directories = RUNTIME_ROOTS + (('docs', 'legacy') if scope == 'delivery' else ())
    names = list(ROOT_FILES) + (['README.md', 'README.zh-CN.md', '.gitignore'] if scope == 'delivery' else [])
    candidates = [root / name for name in names]
    for name in directories:
        candidates.extend((root / name).rglob('*'))
    entries = {}
    for path in sorted(candidates):
        relative = path.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.name in ('.DS_Store', '.env', 'hardware.yaml') or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('Symlink not allowed in source delivery: ' + str(relative))
        if not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            raise ValueError('Unexpected large source: ' + str(relative))
        if path.suffix.lower() in ('.so', '.deb', '.dylib', '.key', '.pem', '.whl',
                                  '.obj', '.mtl', '.usd', '.usda', '.usdc', '.fbx',
                                  '.stl', '.dae', '.png', '.jpg', '.mp4', '.tar', '.gz'):
            raise ValueError('Binary or credential cannot be delivered: ' + str(relative))
        if path.name.startswith('.env.') and path.name != '.env.example':
            raise ValueError('Private environment cannot be delivered: ' + str(relative))
        entries[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    canonical = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
    return {'scope': scope, 'algorithm': 'sha256', 'files': entries,
            'source_hash': hashlib.sha256(canonical).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--scope', choices=('runtime', 'delivery'), default='runtime')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', type=Path)
    parser.add_argument('--bundle', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = manifest(root, args.scope)
    if args.check:
        expected = json.loads(args.check.read_text())
        if result != expected:
            raise SystemExit('SOURCE MISMATCH: hashes, paths or scope differ')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.bundle:
        args.bundle.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting a previous snapshot.
        with args.bundle.open('xb') as destination:
            with tarfile.open(fileobj=destination, mode='w:gz') as archive:
                for name in result['files']:
                    archive.add(root / name, arcname=name, recursive=False)
    print(json.dumps({'scope': result['scope'], 'files': len(result['files']),
                      'source_hash': result['source_hash']}))


if __name__ == '__main__':
    main()
