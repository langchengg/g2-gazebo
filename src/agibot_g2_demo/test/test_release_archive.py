"""Release extraction validates bytes and path boundaries without a Git checkout."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import os
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / 'scripts'
if not SCRIPTS.exists():
    SCRIPTS = Path('/opt/demo/scripts')
sys.path.insert(0, str(SCRIPTS))
import release
from release import extract, isolated_environment, run_recorded, collect_simulation_evidence


def archive(tmp_path, name='g2-gazebo/README.md', content=b'hello', kind=tarfile.REGTYPE):
    file=tmp_path/'candidate.tar.gz'
    with tarfile.open(file,'w:gz') as stream:
        member=tarfile.TarInfo(name);member.type=kind;member.size=len(content) if kind==tarfile.REGTYPE else 0
        if kind==tarfile.SYMTYPE:member.linkname='/outside'
        stream.addfile(member,io.BytesIO(content) if kind==tarfile.REGTYPE else None)
    file.with_suffix('.gz.sha256').write_text(hashlib.sha256(file.read_bytes()).hexdigest()+'  candidate.tar.gz\n')
    files={'README.md':hashlib.sha256(content).hexdigest()}
    canonical=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
    file.with_suffix('.gz.manifest.json').write_text(json.dumps({'scope':'delivery','algorithm':'sha256','files':files,'source_hash':hashlib.sha256(canonical).hexdigest()}))
    return file


def test_safe_extract_into_new_path_with_spaces(tmp_path):
    root,data=extract(archive(tmp_path),tmp_path)
    assert ' ' in str(root)
    assert (root/'README.md').read_bytes()==b'hello'
    assert not (root/'.git').exists()


@pytest.mark.parametrize('name,kind', [('/outside',tarfile.REGTYPE),('g2-gazebo/../../outside',tarfile.REGTYPE),('g2-gazebo/link',tarfile.SYMTYPE)])
def test_unsafe_archive_entries_rejected(tmp_path,name,kind):
    with pytest.raises(ValueError,match='Unsafe'):
        extract(archive(tmp_path,name=name,kind=kind),tmp_path)


def test_archive_checksum_is_required(tmp_path):
    file=archive(tmp_path);file.write_bytes(file.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        extract(file,tmp_path)


def test_package_refuses_incomplete_source_before_creating_archive(tmp_path, monkeypatch):
    source = tmp_path / 'incomplete-source'
    source.mkdir()
    (source / 'README.md').write_text('Incomplete fixture')
    monkeypatch.setattr(release, 'ROOT', source)
    with pytest.raises(ValueError, match='Required release files missing'):
        release.package(tmp_path / 'delivery')
    assert not (tmp_path / 'delivery').exists()


def test_release_environment_does_not_inherit_author_secrets(tmp_path, monkeypatch):
    for key in ['HOME', 'HF_TOKEN', 'DOCKER_HOST', 'DOCKER_CONFIG', 'BUILDKIT_HOST',
                'SIM_IMAGE', 'G2_MODEL_DIR', 'PYTHONPATH', 'PIP_INDEX_URL', 'SSH_AUTH_SOCK']:
        monkeypatch.setenv(key, 'private-author-value')
    env = isolated_environment(tmp_path)
    assert 'private-author-value' not in env.values()
    assert env['DOCKER_HOST'] == 'unix:///var/run/docker.sock'
    assert env['DOCKER_CONTEXT'] == 'default'
    for key in ['HOME', 'HF_HOME', 'DOCKER_CONFIG', 'XDG_CONFIG_HOME', 'PIP_CACHE_DIR']:
        directory = Path(env[key])
        assert directory.is_relative_to(tmp_path)
        assert list(directory.iterdir()) == []
        assert directory.stat().st_mode & 0o077 == 0


def test_timeout_records_deadline_and_terminated_process(tmp_path):
    report = {'commands': []}
    receipt = tmp_path / 'receipt.json'
    with pytest.raises(subprocess.TimeoutExpired):
        run_recorded([sys.executable, '-c', 'import time; time.sleep(30)'],
                     0.05, tmp_path, dict(os.environ), tmp_path, report, receipt)
    record = json.loads(receipt.read_text())['commands'][0]
    assert record['exit_code'] == 124
    assert record['process_exit_code'] is not None
    assert 0.04 <= record['wall_seconds'] < 5
    assert 'TimeoutExpired' in record['error']
    assert Path(record['log']).exists()


def test_command_nonzero_and_spawn_error_are_recorded(tmp_path):
    report = {'commands': []}
    receipt = tmp_path / 'receipt.json'
    with pytest.raises(RuntimeError, match='Failed'):
        run_recorded([sys.executable, '-c', 'raise SystemExit(7)'],
                     5, tmp_path, dict(os.environ), tmp_path, report, receipt)
    with pytest.raises(FileNotFoundError):
        run_recorded([str(tmp_path / 'missing-executable')],
                     5, tmp_path, dict(os.environ), tmp_path, report, receipt)
    records = json.loads(receipt.read_text())['commands']
    assert records[0]['exit_code'] == 7
    assert records[1]['exit_code'] != 0 and records[1]['process_exit_code'] is None
    assert 'FileNotFoundError' in records[1]['error']


def test_receipt_binds_actual_nested_image_evidence(tmp_path):
    evidence = tmp_path / '.artifacts/gazebo/test-run/environment.json'
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps({'image': 'sha256:actual-image arm64',
                                   'source': {'source_hash': 'actual-source'},
                                   'image_source_matches': True}))
    report = {}
    collect_simulation_evidence(tmp_path, report)
    assert report['image_ids'] == ['sha256:actual-image']
    assert report['simulation_evidence'][0]['sha256'] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert report['simulation_evidence'][0]['path'] == str(evidence)
