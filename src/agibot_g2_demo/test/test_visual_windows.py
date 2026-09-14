"""Window selection fixtures; these are not real desktop acceptance evidence."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def visual(monkeypatch, tmp_path):
    # Avoid starting the Linux process supervisor or requiring ROS on the host.
    monkeypatch.setitem(sys.modules, 'run_sim', SimpleNamespace(OUT=tmp_path))
    monkeypatch.setitem(sys.modules, 'ament_index_python.packages', SimpleNamespace(
        get_package_prefix=lambda _: '/unused',
        get_package_share_directory=lambda _: '/unused'))
    path = Path(__file__).resolve().parents[3] / 'scripts/visual_session.py'
    spec = importlib.util.spec_from_file_location('visual_window_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.supervisor.process_tree = lambda: {
        10: (1, 'S', '100'), 11: (10, 'S', '101'), 12: (11, 'S', '102'),
        20: (1, 'S', '200'), 13: (10, 'Z', '103')}
    return module


def candidates(module, monkeypatch, mapping):
    monkeypatch.setattr(module, 'windows', lambda _: list(mapping))
    monkeypatch.setattr(module.subprocess, 'run', lambda argv, **kw: SimpleNamespace(
        returncode=0, stdout=str(mapping[argv[-1]])))


def test_old_window_is_excluded_even_with_colliding_container_pid(visual, monkeypatch):
    candidates(visual, monkeypatch, {'old': 12, 'new': 11})
    assert visual.owned_window('Gazebo', {'old'}, SimpleNamespace(pid=10)) == ('new', 11)


def test_new_window_must_belong_to_component_descendants(visual, monkeypatch):
    candidates(visual, monkeypatch, {'unrelated': 20, 'new-child': 12})
    assert visual.owned_window('Gazebo', set(), SimpleNamespace(pid=10)) == ('new-child', 12)


def test_multiple_owned_windows_wait_instead_of_selecting_splash(visual, monkeypatch):
    candidates(visual, monkeypatch, {'splash': 11, 'main': 12})
    assert visual.owned_window('RViz', set(), SimpleNamespace(pid=10)) is None


def test_dead_window_owner_is_not_ready(visual, monkeypatch):
    candidates(visual, monkeypatch, {'zombie': 13})
    assert visual.owned_window('RViz', set(), SimpleNamespace(pid=10)) is None


def test_successful_bootstrap_does_not_fail_live_readiness(visual):
    visual.supervisor.PROCESSES = [('python-identity', SimpleNamespace(poll=lambda: 0, returncode=0))]
    assert visual.wait_for(lambda: True, 'display', timeout=1) is True


def test_exited_persistent_component_fails_readiness(visual):
    visual.LIVE_PROCESSES = [('rviz2', SimpleNamespace(poll=lambda: 0, returncode=0))]
    with pytest.raises(RuntimeError, match='rviz2 exited prematurely'):
        visual.wait_for(lambda: True, 'display', timeout=1)


def test_rviz_geometry_is_set_in_session_copy_only(visual, tmp_path):
    import yaml
    source = Path(__file__).resolve().parents[1] / 'config/g2_demo.rviz'
    original = source.read_bytes()
    config = Path(visual.session_rviz_config(source, 756, 0, 756, 594))
    assert config.parent == tmp_path
    assert source.read_bytes() == original
    before = yaml.safe_load(original)
    after = yaml.safe_load(config.read_text())
    before['Window Geometry'].update(X=756, Y=0, Width=756, Height=594)
    assert after == before


def test_rviz_move_does_not_resize_or_unmaximize(visual, monkeypatch):
    calls = []
    monkeypatch.setattr(visual.subprocess, 'run', lambda argv, **kw: calls.append(argv))
    visual.place('42', 'G2 RViz2', 756, 0, 756, 594, resize=False)
    assert calls == [
        ['xdotool', 'set_window', '--name', 'G2 RViz2', '42'],
        ['wmctrl', '-i', '-r', '0x2a', '-e', '0,756,0,-1,-1']]


def test_invalid_rviz_geometry_fails_before_launch(visual, tmp_path):
    source = tmp_path / 'invalid.rviz'
    source.write_text('Window Geometry: []\n')
    with pytest.raises(RuntimeError, match='Window Geometry'):
        visual.session_rviz_config(source, 756, 0, 756, 594)


def test_softpipe_is_scoped_to_rviz_without_gl_version_override(visual, monkeypatch):
    monkeypatch.setitem(visual.ENV, 'LP_NUM_THREADS', '8')
    monkeypatch.setitem(visual.ENV, 'GALLIUM_DRIVER', 'llvmpipe')
    original = dict(visual.ENV)
    environment = visual.rviz_environment()
    assert environment['GALLIUM_DRIVER'] == 'softpipe'
    assert 'LP_NUM_THREADS' not in environment
    assert visual.ENV == original
    assert {key for key in environment if environment[key] != original.get(key)} == {'GALLIUM_DRIVER'}
    assert environment.get('MESA_GL_VERSION_OVERRIDE') == original.get('MESA_GL_VERSION_OVERRIDE')


@pytest.mark.parametrize('exit_code', [-11, -9, -6, 1, None])
def test_cleanup_rejects_abnormal_exit_even_without_remaining_pids(visual, exit_code):
    import json
    visual.supervisor.PROCESSES = [('rviz2', SimpleNamespace(pid=10, poll=lambda: exit_code))]
    visual.supervisor.FILES = []
    visual.supervisor.stop = lambda _: None
    visual.supervisor.remaining_owned = lambda: []
    with pytest.raises(RuntimeError, match='unexpected component exit'):
        visual.cleanup()
    receipt = json.loads((visual.OUT / 'cleanup.json').read_text())
    assert receipt['remaining_owned_pids'] == []
    assert receipt['errors'][0]['exit_code'] == exit_code


def test_cleanup_accepts_normal_ros_exit(visual):
    import json
    visual.supervisor.PROCESSES = [('rviz2', SimpleNamespace(pid=10, poll=lambda: 0))]
    visual.supervisor.FILES = []
    visual.supervisor.stop = lambda _: None
    visual.supervisor.remaining_owned = lambda: []
    visual.cleanup()
    assert json.loads((visual.OUT / 'cleanup.json').read_text())['errors'] == []
