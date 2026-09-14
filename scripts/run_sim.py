#!/usr/bin/env python3
"""Bounded real simulator runs, optional actual GUI capture, and process cleanup."""
import argparse
import ctypes
import threading
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

OUT = Path(os.environ.get('EVIDENCE_DIR', '/evidence'))
OUT.mkdir(parents=True, exist_ok=True)
PROCESSES = []
FILES = []
RECORDS = []
OWNED = {}
TRACKING = True
# Keep orphaned descendants attributable to this dedicated container runner.
if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0:
    raise RuntimeError('could not establish child subreaper')


def process_tree():
    rows = {}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            fields = (directory/'stat').read_text().split(') ', 1)[1].split()
            rows[int(directory.name)] = (int(fields[1]), fields[0], fields[19])
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return rows


def track():
    while TRACKING:
        rows = process_tree()
        selected = {os.getpid()}
        while True:
            more = {pid for pid, row in rows.items() if row[0] in selected}
            if more <= selected:
                break
            selected |= more
        for pid in selected - {os.getpid()}:
            if pid in rows:
                OWNED[pid] = rows[pid][2]
        time.sleep(0.1)


threading.Thread(target=track, daemon=True).start()


def remaining_owned():
    rows = process_tree()
    return [pid for pid, start in list(OWNED.items()) if pid in rows and
            rows[pid][2] == start and rows[pid][1] != 'Z']



def start(argv, label, env=None):
    stream = (OUT / (label + '.log')).open('w')
    FILES.append(stream)
    process = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                               start_new_session=True, env=env)
    PROCESSES.append((label, process))
    return process


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(5)
                raise RuntimeError('process required SIGKILL during cleanup')


def command(argv, label, timeout=180, env=None):
    t = time.monotonic()
    process = start(argv, label, env)
    code = 1
    try:
        code = process.wait(timeout)
    except subprocess.TimeoutExpired:
        code = 124
        stop(process)
    finally:
        RECORDS.append({'argv': argv, 'label': label, 'exit_code': code,
                        'wall_seconds': time.monotonic()-t})
        (OUT / 'run-commands.json').write_text(json.dumps(RECORDS, indent=2))
    print((OUT / (label + '.log')).read_text()[-12000:], flush=True)
    if code:
        raise subprocess.CalledProcessError(code, argv)


def graphics():
    env = dict(os.environ, DISPLAY=':99', LIBGL_ALWAYS_SOFTWARE='1', QT_X11_NO_MITSHM='1')
    start(['Xvfb', ':99', '-screen', '0', '1280x720x24', '-nolisten', 'tcp'], 'xvfb', env)
    deadline = time.monotonic()+20
    while True:
        result = subprocess.run(['glxinfo', '-B'], env=env, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            (OUT/'opengl.txt').write_text(result.stdout)
            break
        if time.monotonic() > deadline:
            raise RuntimeError('Xvfb/Mesa GL context unavailable: ' + result.stderr)
        time.sleep(0.2)
    start(['openbox', '--sm-disable'], 'window-manager', env)
    gui = start(['ign', 'gazebo', '-g', '-v', '3', '--render-engine', 'ogre'], 'gazebo-gui', env)
    deadline = time.monotonic()+60
    while time.monotonic() < deadline:
        if gui.poll() is not None:
            raise RuntimeError('Gazebo GUI exited')
        result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', 'Gazebo|G2 Gazebo|Ignition'],
                                env=env, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            (OUT/'gui-windows.txt').write_text(result.stdout)
            window = result.stdout.splitlines()[0]
            for argv in [['xdotool', 'windowmove', window, '0', '0'],
                         ['xdotool', 'windowsize', window, '1280', '720']]:
                subprocess.run(argv, env=env, check=True, timeout=5)
            return env
        time.sleep(0.25)
    raise RuntimeError('Gazebo visible GUI window deadline exceeded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['verify', 'test', 'demo', 'record'], default='verify')
    args = parser.parse_args()
    command(['python3', '/opt/demo/scripts/check_install.py'], 'python-identity', 20)
    command(['/opt/demo/check_mesh', '/opt/g2-model/meshes'], 'actual-mesh-loader', 60)
    if args.mode == 'test':
        command(['python3', '/opt/demo/scripts/run_tests.py'], 'software-regression', 650)
        disabled = start(['ros2', 'launch', 'agibot_g2_demo', 'sim.launch.py'], 'disabled-simulation')
        command(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'disabled', '--evidence-dir', str(OUT/'disabled')], 'disabled-check', 180)
        stop(disabled)
    simulation = start(['ros2', 'launch', 'agibot_g2_demo', 'sim.launch.py', 'enable_motion:=true'], 'simulation')
    env = graphics() if args.mode in ['demo', 'record'] else None
    recorder = None
    if env:
        recorder = start(['ffmpeg', '-y', '-nostdin', '-f', 'x11grab', '-video_size', '1280x720',
                          '-framerate', '10', '-i', ':99', '-c:v', 'libx264', '-preset', 'ultrafast',
                          '-crf', '23', '-pix_fmt', 'yuv420p', str(OUT/'g2-gazebo.mp4')], 'recording', env)
    command(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'motion', '--evidence-dir', str(OUT/'motion')], 'motion-check', 240)
    if simulation.poll() is not None:
        raise RuntimeError('simulation died during acceptance')
    if recorder:
        command(['ffmpeg', '-y', '-f', 'x11grab', '-video_size', '1280x720', '-i', ':99',
                 '-frames:v', '1', str(OUT/'g2-gazebo.png')], 'screenshot', 20, env)
        stop(recorder)
        command(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
                 str(OUT/'g2-gazebo.mp4')], 'media-probe', 20)
    if args.mode == 'test':
        command(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'action-faults', '--evidence-dir', str(OUT/'action-faults')], 'action-faults-check', 180)
        command(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'pause-reset', '--evidence-dir', str(OUT/'faults')], 'pause-reset-check', 180)
    if env:
        for label, proc in PROCESSES:
            if label == 'gazebo-gui' and proc.poll() is not None:
                raise RuntimeError('Gazebo GUI died during recording')
        media = json.loads((OUT/'media-probe.log').read_text())
        duration = float(media['format']['duration'])
        motion_wall = next(r['wall_seconds'] for r in RECORDS if r['label']=='motion-check')
        if duration < motion_wall - 1.0:
            raise RuntimeError('recording does not span the motion observation interval')
    stop(simulation)
    if args.mode == 'test':
        interrupted = start(['ros2', 'launch', 'agibot_g2_demo', 'sim.launch.py', 'enable_motion:=true'], 'interrupt-simulation')
        command(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'interrupt', '--evidence-dir', str(OUT/'interrupt')], 'interrupt-check', 180)
        try:
            interrupted.wait(20)
        except subprocess.TimeoutExpired:
            raise RuntimeError('launch did not stop after application SIGTERM')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    try:
        main()
    finally:
        errors = []
        for label, process in reversed(PROCESSES):
            try:
                stop(process)
            except Exception as error:
                errors.append({'label': label, 'error': str(error)})
        TRACKING = False
        # Fortress's Ruby launcher can exit before its server child after a
        # launch-triggered shutdown. As container subreaper, finish the owned
        # descendants as well; a dead group leader is not proof of cleanup.
        descendant_cleanup = []
        for sig, budget in [(signal.SIGINT, 8.), (signal.SIGTERM, 5.)]:
            leftovers = remaining_owned()
            if not leftovers:
                break
            for pid in leftovers:
                try:
                    argv = Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
                    descendant_cleanup.append({'pid': pid, 'signal': sig.name,
                        'argv': [v.decode(errors='replace') for v in argv if v]})
                    os.kill(pid, sig)
                except (ProcessLookupError, FileNotFoundError):
                    pass
            deadline = time.monotonic()+budget
            while remaining_owned() and time.monotonic()<deadline:
                time.sleep(0.1)
        leftovers = remaining_owned()
        if leftovers:
            errors.append({'remaining_owned_pids_after_bounded_shutdown': leftovers})
            for pid in leftovers:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        for stream in FILES:
            stream.close()
        (OUT/'cleanup.json').write_text(json.dumps({'processes': [
            {'label': label, 'pid': p.pid, 'exit_code': p.poll()} for label, p in PROCESSES], 'descendant_cleanup': descendant_cleanup, 'remaining_owned_pids': remaining_owned(),
            'errors': errors}, indent=2))
        if errors:
            raise RuntimeError('cleanup errors: '+str(errors))
