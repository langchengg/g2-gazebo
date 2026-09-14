"""Project downloader fixtures; no fixture is presented as a vendor asset."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.error
import time
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetcher = load('fetch_g2_model')
preparer = load('prepare_model')


class Response(io.BytesIO):
    status = 200


def fixture_lock(tmp_path, body=b'project fixture model'):
    path = tmp_path / 'lock.json'
    item = {'path': 'model.usda', 'size': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    path.write_text(json.dumps({'repository': 'project/fixture', 'repo_id': 'project/fixture',
        'repo_type': 'dataset', 'revision': 'a' * 40, 'license': 'CC-BY-NC-SA-4.0',
        'files': [item]}))
    return path


def test_download_requires_recipient_license_acknowledgment(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('unexpected network'))
    with pytest.raises(ValueError, match='author cannot accept'):
        fetcher.fetch(fixture_lock(tmp_path), tmp_path / 'cache')


def test_fetch_and_hash_verified_cache_reuse(tmp_path, monkeypatch):
    body = b'project fixture model'
    calls = []
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda url, **kw: (calls.append(url), Response(body))[1])
    lock, cache = fixture_lock(tmp_path, body), tmp_path / 'cache'
    fetcher.fetch(lock, cache, True)
    fetcher.fetch(lock, cache)
    assert len(calls) == 1 and '/resolve/' + 'a' * 40 + '/' in calls[0]
    assert (cache / 'raw/model.usda').read_bytes() == body


def test_corrupt_cache_is_quarantined_and_replaced(tmp_path, monkeypatch):
    body = b'project fixture model'
    cache = tmp_path / 'cache'
    (cache / 'raw').mkdir(parents=True)
    (cache / 'raw/model.usda').write_bytes(b'damaged')
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda *a, **k: Response(body))
    fetcher.fetch(fixture_lock(tmp_path, body), cache, True)
    assert (cache / 'raw/model.usda').read_bytes() == body
    assert [p.read_bytes() for p in (cache / 'quarantine').rglob('model.usda')] == [b'damaged']


@pytest.mark.parametrize('body', [b'<html>denied', b'{"error":"denied"}', b'version https://git-lfs.github.com/spec/v1'])
def test_http_200_error_documents_rejected(tmp_path, monkeypatch, body):
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda *a, **k: Response(body))
    with pytest.raises(ValueError, match='Error page'):
        fetcher.fetch(fixture_lock(tmp_path, body), tmp_path / 'cache', True)
    assert not (tmp_path / 'cache/raw/model.usda').exists()


def test_checksum_mismatch_rejected_without_partial_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda *a, **k: Response(b'x' * 21))
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        fetcher.fetch(fixture_lock(tmp_path), tmp_path / 'cache', True)
    assert not (tmp_path / 'cache/raw/model.usda').exists()


@pytest.mark.parametrize('revision', ['main', 'latest', 'a' * 39])
def test_mutable_or_incomplete_revision_rejected(tmp_path, revision):
    path = fixture_lock(tmp_path)
    data = json.loads(path.read_text()); data['revision'] = revision
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='immutable commit'):
        fetcher.fetch(path, tmp_path / 'cache', True)


def test_authorization_error_is_not_retried(tmp_path, monkeypatch):
    calls = []
    def denied(url, **kwargs):
        calls.append(url)
        raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', denied)
    with pytest.raises(urllib.error.HTTPError):
        fetcher.fetch(fixture_lock(tmp_path), tmp_path / 'cache', True)
    assert len(calls) == 1


def test_download_deadline_interrupts_stalled_read_and_removes_partial(tmp_path, monkeypatch):
    class Stalled(Response):
        def read(self, size=-1):
            time.sleep(2)
            return super().read(size)
    calls = []
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen',
                        lambda *a, **k: (calls.append(a), Stalled(b'fixture'))[1])
    started = time.monotonic()
    with pytest.raises(fetcher.DownloadDeadlineExceeded):
        fetcher.fetch(fixture_lock(tmp_path), tmp_path / 'cache', True, file_timeout=.05)
    assert time.monotonic() - started < 1
    assert len(calls) == 1
    assert list((tmp_path / 'cache/raw').iterdir()) == []


def test_download_deadline_spans_retry_backoff(tmp_path, monkeypatch):
    calls = []
    def unavailable(url, **kwargs):
        calls.append(url)
        raise urllib.error.HTTPError(url, 503, 'Unavailable', {}, None)
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', unavailable)
    with pytest.raises(fetcher.DownloadDeadlineExceeded):
        fetcher.fetch(fixture_lock(tmp_path), tmp_path / 'cache', True, file_timeout=.05)
    assert len(calls) == 1


def test_symlink_cache_escape_rejected(tmp_path, monkeypatch):
    cache = tmp_path / 'cache'; (cache / 'raw').mkdir(parents=True)
    (cache / 'raw/model.usda').symlink_to(tmp_path / 'outside')
    with pytest.raises(ValueError, match='Unsafe model cache'):
        fetcher.fetch(fixture_lock(tmp_path), cache, True)


def test_native_tool_dockerfile_pins_source_and_has_real_import():
    text = (ROOT / 'Dockerfile.model-tools').read_text()
    assert 'ee47c679abde5b467a7b6a41f3b2285564a4222e' in text
    assert 'Usd.Stage.CreateInMemory()' in text
    assert 'PXR_BUILD_IMAGING=OFF' in text
    assert 'TBB_COMMIT=9afd759b72c0c233cd5ea3c3c06b0894c9da9c54' in text
    assert '-DTBB_DIR=/opt/tbb/lib/cmake/TBB' in text
    assert 'COPY --from=usd-build /opt/tbb /opt/tbb' in text
    assert 'libtbb-dev' not in text


def generated_fixture(tmp_path):
    root = tmp_path / 'project source'
    (root / 'scripts').mkdir(parents=True)
    (root / 'model_sources').mkdir()
    (root / 'scripts/convert_g2_model.py').write_text('# project fixture')
    (root / 'model_sources/g2.lock.json').write_text(json.dumps({'revision': 'a' * 40}))
    generated = tmp_path / 'fresh output'; generated.mkdir()
    inventory = generated / 'joint_inventory.json'
    inventory.write_text(json.dumps({'controlled_joints': [{'name': name} for name in preparer.ARM]}))
    robot = ET.Element('robot', name='project_fixture')
    for name in ['world', 'base_link'] + ['arm_' + str(i) for i in range(7)]:
        ET.SubElement(robot, 'link', name=name)
    for index, name in enumerate(['world_to_base'] + preparer.ARM):
        joint = ET.SubElement(robot, 'joint', name=name, type='fixed' if index == 0 else 'revolute')
        ET.SubElement(joint, 'parent', link='world' if index == 0 else 'base_link' if index == 1 else 'arm_' + str(index-2))
        ET.SubElement(joint, 'child', link='base_link' if index == 0 else 'arm_' + str(index-1))
    visual = ET.SubElement(robot.find("link[@name='base_link']"), 'visual')
    ET.SubElement(ET.SubElement(visual, 'geometry'), 'mesh', filename='file:///opt/g2-model/meshes/fixture.obj')
    ET.ElementTree(robot).write(generated / 'g2.urdf')
    (generated / 'meshes').mkdir()
    (generated / 'meshes/fixture.obj').write_text('mtllib fixture.mtl\nusemtl fixture\nv 0 0 0\n')
    (generated / 'meshes/fixture.mtl').write_text('newmtl fixture\nKd 0.5 0.5 0.5\n')
    manifest = {'converter_sha256': preparer.digest(root / 'scripts/convert_g2_model.py'),
        'source_lock_sha256': preparer.digest(root / 'model_sources/g2.lock.json'),
        'revision': 'a' * 40, 'runtime_arguments': preparer.RUNTIME_ARGUMENTS,
        'files': {str(path.relative_to(generated)): preparer.digest(path)
                  for path in generated.rglob('*') if path.is_file()}}
    (generated / 'generated_manifest.json').write_text(json.dumps(manifest))
    return root, generated


def refresh_fixture_manifest(generated):
    path = generated / 'generated_manifest.json'
    manifest = json.loads(path.read_text())
    manifest['files'] = {str(p.relative_to(generated)): preparer.digest(p)
                         for p in generated.rglob('*') if p.is_file() and p != path}
    path.write_text(json.dumps(manifest))


@pytest.mark.parametrize('fault', ['wrong_joint_name', 'wrong_mobile_joint', 'multiple_parents', 'cycle', 'missing_mesh', 'author_uri', 'bare_path', 'encoded_escape',
                                  'escaping_mtl', 'undefined_material', 'external_texture'])
def test_independent_generated_validation_rejects_self_consistent_bad_model(tmp_path, fault):
    root, generated = generated_fixture(tmp_path)
    if fault == 'wrong_joint_name':
        path = generated / 'joint_inventory.json'
        data = json.loads(path.read_text()); data['controlled_joints'][0]['name'] = 'wrong_joint'
        path.write_text(json.dumps(data))
    elif fault in ('cycle', 'wrong_mobile_joint', 'multiple_parents', 'author_uri', 'missing_mesh', 'bare_path', 'encoded_escape'):
        path = generated / 'g2.urdf'; tree = ET.parse(path)
        if fault == 'cycle':
            tree.find("joint[@name='" + preparer.ARM[0] + "']/parent").set('link', 'arm_6')
        elif fault == 'wrong_mobile_joint':
            tree.find("joint[@name='" + preparer.ARM[0] + "']").set('name', 'unexpected_joint')
        elif fault == 'multiple_parents':
            tree.find("joint[@name='" + preparer.ARM[0] + "']/child").set('link', 'base_link')
        else:
            tree.find('.//mesh').set('filename', {
                'author_uri': 'file:///Users/author/fixture.obj',
                'bare_path': '/opt/g2-model/meshes/fixture.obj',
                'encoded_escape': 'file:///opt/g2-model/%2e%2e/outside.obj',
                'missing_mesh': 'file:///opt/g2-model/meshes/missing.obj',
            }[fault])
        tree.write(path)
    elif fault == 'escaping_mtl':
        (generated / 'meshes/fixture.obj').write_text('mtllib ../../outside.mtl\nusemtl fixture\n')
    elif fault == 'undefined_material':
        (generated / 'meshes/fixture.mtl').write_text('newmtl different\n')
    else:
        (generated / 'meshes/fixture.mtl').write_text('newmtl fixture\nmap_Kd https://example.invalid/texture.png\n')
    refresh_fixture_manifest(generated)
    with pytest.raises(ValueError):
        preparer.validate_generated(generated, root)


def test_generated_cache_verifies_and_rejects_extra_stale_file(tmp_path):
    root, generated = generated_fixture(tmp_path)
    preparer.validate_generated(generated, root)
    (generated / 'old_mesh.obj').write_text('project stale fixture')
    with pytest.raises(ValueError, match='file set differs'):
        preparer.validate_generated(generated, root)


def test_generated_cache_rejects_content_and_source_changes(tmp_path):
    root, generated = generated_fixture(tmp_path)
    (generated / 'joint_inventory.json').write_text('damaged')
    with pytest.raises(ValueError, match='Invalid generated'):
        preparer.validate_generated(generated, root)
    (root / 'scripts/convert_g2_model.py').write_text('# changed converter')
    with pytest.raises(ValueError, match='converter_sha256'):
        preparer.validate_generated(generated, root)
