"""Real subprocess fixtures for capture readiness; no ROS/GUI PASS is implied."""
import importlib.util
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('record_visual_test', ROOT/'scripts/record_visual.py')
record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record)


@pytest.fixture
def child():
    processes = []

    def start(code, *args):
        process = subprocess.Popen([sys.executable, '-c', code, *map(str, args)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        processes.append(process)
        return process

    yield start
    for process in processes:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=5)


def test_capture_exit_before_first_frame_is_rejected(child, tmp_path):
    process = child('raise SystemExit(7)')
    with pytest.raises(RuntimeError, match='before first-frame readiness: 7'):
        record.wait_for_first_frame(process, tmp_path/'progress', timeout=2)


@pytest.mark.parametrize('progress', ['', 'frame=0\nprogress=continue\n', 'frame=1\n'])
def test_running_process_without_complete_frame_progress_times_out(child, tmp_path, progress):
    path = tmp_path/'progress'
    path.write_text(progress)
    process = child('import time; time.sleep(10)')
    with pytest.raises(TimeoutError, match='no motion was started'):
        record.wait_for_first_frame(process, path, timeout=.15)
    assert process.poll() is None  # A live PID alone was not accepted.


def test_first_complete_positive_frame_progress_is_accepted(child, tmp_path):
    path = tmp_path/'progress'
    process = child('from pathlib import Path; import sys,time; '
                    'Path(sys.argv[1]).write_text("frame=1\\nprogress=continue\\n"); '
                    'time.sleep(10)', path)
    observed = record.wait_for_first_frame(process, path, timeout=2)
    assert observed['frames'] == 1
    assert observed['wall_seconds'] < 2


def test_interrupted_tf_check_writes_failure_receipt(monkeypatch, tmp_path):
    # Execute the production entry function with a failing executor fixture,
    # without importing ROS or opening the fixed runtime model path on the host.
    source = ROOT/'scripts/verify_visual.py'
    main = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'main')
    model = tmp_path/'model.urdf'
    model.write_text('<robot/>')
    output = tmp_path/'tf.json'

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt('fixture interrupt')

    node = SimpleNamespace(urdf='<robot/>', results=[], infrastructure={},
                           destroy_node=lambda: None)
    scope = {'argparse': argparse, 'hashlib': hashlib, 'json': json, 'time': time,
             'Path': lambda value: model if str(value) == '/opt/g2-model/g2.urdf' else Path(value),
             'VisualProbe': lambda _: node,
             'rclpy': SimpleNamespace(init=lambda: None, spin_once=interrupted, shutdown=lambda: None)}
    exec(compile(ast.Module(body=[main], type_ignores=[]), str(source), 'exec'), scope)
    monkeypatch.setattr(sys, 'argv', ['verify_visual.py', '--output', str(output)])
    with pytest.raises(KeyboardInterrupt):
        scope['main']()
    receipt = json.loads(output.read_text())
    assert receipt['result'] == 'FAIL'
    assert 'KeyboardInterrupt' in receipt['error']


def test_interrupted_recording_writes_failure_receipt(monkeypatch, tmp_path):
    session = tmp_path/'session.json'
    session.write_text(json.dumps({'width': 1000, 'height': 700, 'display': ':99'}))
    output = tmp_path/'capture'
    monkeypatch.setattr(sys, 'argv', ['record_visual.py', '--session', str(session),
                                     '--output', str(output), '--motion'])

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt('fixture interrupt')

    monkeypatch.setattr(record.subprocess, 'Popen', interrupted)
    with pytest.raises(KeyboardInterrupt):
        record.main()
    receipt = json.loads((output/'recording.json').read_text())
    assert receipt['result'] == 'FAIL'
    assert 'KeyboardInterrupt' in receipt['error']
    assert receipt['first_frame'] is None


@pytest.fixture
def luma_video(tmp_path):
    """Real encoded frames; no robot data or display server needed."""
    import shutil
    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg is required for decoded capture-quality tests')

    def make(black):
        video = tmp_path / ('black cursor.mp4' if black else 'bright empty scene.mp4')
        scene = 'color=c=black:s=320x180:r=10:d=0.6,drawbox=x=100:y=100:w=2:h=2:color=white:t=fill' if black else 'color=c=gray:s=320x180:r=10:d=0.6'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'lavfi',
                        '-i', scene, '-threads', '1', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', str(video)], check=True, timeout=10)
        return video
    return make


@pytest.mark.parametrize('black', [True, False])
def test_real_decoded_video_rejects_black_even_with_bright_cursor(luma_video, tmp_path, black):
    quality = record.capture_luma_quality(luma_video(black), tmp_path/'quality.json')
    assert quality['decoded_frames'] == 6
    assert quality['all_frames_near_black'] is black
    assert quality['result'] == ('FAIL' if black else 'PASS')
    # A bright empty scene is accepted only as nonblack, never as model evidence.
    assert quality['visual_model_and_motion_observation'].startswith('NOT TESTED')
    assert (tmp_path/'quality.txt').is_file()


def test_luma_decoder_failure_propagates(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        record.capture_luma_quality(tmp_path/'missing.mp4', tmp_path/'quality.json')


@pytest.mark.parametrize('text', ['', 'lavfi.signalstats.YAVG=nan\n',
                                  'lavfi.signalstats.YAVG=256\n'])
def test_missing_or_invalid_luma_metadata_is_rejected(monkeypatch, tmp_path, text):
    monkeypatch.setattr(record, 'subprocess', SimpleNamespace(
        run=lambda *a, **kw: SimpleNamespace(stdout=text)))
    with pytest.raises(RuntimeError, match='missing or invalid'):
        record.capture_luma_quality(tmp_path/'fixture.mp4', tmp_path/'quality.json')


def test_black_capture_causes_main_failure_receipt(monkeypatch, tmp_path, luma_video):
    import shutil
    black_video = luma_video(True)
    session = tmp_path/'session.json'
    session.write_text(json.dumps({'width': 1000, 'height': 700, 'display': ':99'}))
    output = tmp_path/'capture'
    real_run = subprocess.run

    def fake_popen(argv, **kwargs):
        if str(argv[-1]).endswith('.mp4'):
            shutil.copyfile(black_video, argv[-1])
        return SimpleNamespace(wait=lambda *a: 0, poll=lambda: None)

    def run(argv, **kwargs):
        if argv[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': '6'}}))
        if 'x11grab' in argv:
            return SimpleNamespace(returncode=0)
        return real_run(argv, **kwargs)  # Real FFmpeg decodes the actual black fixture.

    monkeypatch.setattr(record, 'subprocess', SimpleNamespace(
        Popen=fake_popen, run=run, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE,
        STDOUT=subprocess.STDOUT))
    monkeypatch.setattr(record, 'stop', lambda process: None)
    monkeypatch.setattr(record, 'wait_for_first_frame', lambda *a: {'frames': 1})
    monkeypatch.setattr(sys, 'argv', ['record_visual.py', '--session', str(session),
                                    '--output', str(output), '--duration', '1'])
    with pytest.raises(RuntimeError, match='entirely near black'):
        record.main()
    receipt = json.loads((output/'recording.json').read_text())
    assert receipt['result'] == 'FAIL'
    assert receipt['capture_quality']['all_frames_near_black'] is True
    assert 'manual observation' in receipt['result_scope']
