#!/usr/bin/env python3
"""Persistent authenticated Gazebo/RViz desktop, stopped explicitly by its owner.

Host orchestration must publish port 6080 only on the VM loopback interface.
The VNC password file is a read-only, mode-0600 secret; no credential is logged.
No motion is submitted by startup or display reconnection. The separate
record-visual command explicitly requests its recorded action.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
import yaml

from ament_index_python.packages import get_package_prefix, get_package_share_directory
import run_sim as supervisor

OUT = supervisor.OUT
ENV = dict(os.environ, DISPLAY=':99', LIBGL_ALWAYS_SOFTWARE='1', QT_XCB_NO_MITSHM='1')
STOPPING = False
LIVE_PROCESSES = []


def start(argv, label, env=None):
    """Start and register one process owned by this visual supervisor."""
    process = supervisor.start(argv, label, env)
    LIVE_PROCESSES.append((label, process))
    return process


def stop_requested(*_):
    global STOPPING
    STOPPING = True


def wait_for(condition, description, timeout=90.):
    """Wait on wall time while failing if any owned prerequisite exits."""
    end = time.monotonic()+timeout
    while not STOPPING and time.monotonic() < end:
        for label, process in LIVE_PROCESSES:
            if process.poll() is not None:
                raise RuntimeError(f'{label} exited prematurely: {process.returncode}')
        value = condition()
        if value:
            return value
        time.sleep(.2)
    raise RuntimeError('Stopped or deadline exceeded: '+description)


def windows(pattern, visible=True):
    """Return X11 windows matching a role pattern and visibility requirement."""
    result = subprocess.run(['xdotool', 'search'] + (['--onlyvisible'] if visible else []) + ['--name', pattern],
                            env=ENV, capture_output=True, text=True, timeout=5)
    if result.returncode not in (0, 1) or (result.returncode == 1 and result.stderr.strip()):
        raise RuntimeError('X11 window query failed: '+result.stderr)
    return result.stdout.splitlines() if result.returncode == 0 else []


def owned_window(pattern, existing, process):
    """Require a new XID and a live PID in this component's process tree."""
    rows = supervisor.process_tree()
    owned = {process.pid}
    while True:
        children = {pid for pid, row in rows.items() if row[0] in owned}
        if children <= owned:
            break
        owned |= children
    matches = []
    for window in windows(pattern):
        if window in existing:
            continue
        result = subprocess.run(['xdotool', 'getwindowpid', window], env=ENV,
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip().isdigit():
            pid = int(result.stdout.strip())
            if pid in owned and pid in rows and rows[pid][1] != 'Z':
                matches.append((window, pid))
    # A transient splash and the main window may briefly coexist. Wait rather
    # than choose a random window or touch another user's existing window.
    return matches[0] if len(matches) == 1 else None


def place(window, name, x, y, width, height, resize=True):
    commands = [['xdotool', 'set_window', '--name', name, window]]
    if resize:
        commands.append(['wmctrl', '-i', '-r', hex(int(window)), '-b',
                         'remove,maximized_vert,maximized_horz'])
    commands.append(['wmctrl', '-i', '-r', hex(int(window)), '-e',
                     f'0,{x},{y},{width if resize else -1},{height if resize else -1}'])
    for argv in commands:
        subprocess.run(argv, env=ENV, check=True, timeout=5)


def session_rviz_config(source, x, y, width, height):
    """Set geometry before Qt/Ogre initialize; preserve the installed config."""
    data = yaml.safe_load(Path(source).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('Window Geometry'), dict):
        raise RuntimeError('RViz config lacks Window Geometry mapping')
    data['Window Geometry'].update(Width=width, Height=height, X=x, Y=y)
    config = OUT / 'g2_demo.rviz'
    config.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return str(config)


def rviz_environment():
    # Scope the verified native-Xorg shutdown workaround to RViz. Gazebo keeps
    # its existing renderer; actual capabilities are captured with this same env.
    environment = dict(ENV, GALLIUM_DRIVER='softpipe')
    environment.pop('LP_NUM_THREADS', None)
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop', action='store_true', help='Use an existing authorized DISPLAY/XAUTHORITY; no VNC or display server.')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=900)
    args = parser.parse_args()
    if not 1000 <= args.width <= 2560 or not 650 <= args.height <= 1600:
        parser.error('desktop dimensions outside supported range')
    secret = Path(os.environ.get('VNC_PASSWORD_FILE', '/run/secrets/vnc_password'))
    if args.desktop:
        if not os.environ.get('DISPLAY') or not os.environ.get('XAUTHORITY'):
            raise RuntimeError('Desktop mode requires existing DISPLAY and a narrowly mounted XAUTHORITY file')
        ENV['DISPLAY'] = os.environ['DISPLAY']
        if not Path(os.environ['XAUTHORITY']).is_file():
            raise RuntimeError('XAUTHORITY file is unavailable')
    else:
        info = secret.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size != 8:
            raise RuntimeError('VNC password must be an 8-byte x11vnc password file with mode 0600')
    supervisor.command(['python3', '/opt/demo/scripts/check_install.py', '--visual'], 'python-identity', 30)
    if not args.desktop:
        start(['Xvfb', ':99', '-screen', '0', f'{args.width}x{args.height}x24', '-nolisten', 'tcp'], 'xvfb', ENV)

    def opengl_ready():
        result = subprocess.run(['glxinfo', '-B'], env=ENV, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            (OUT/'opengl.txt').write_text(result.stdout)
            return True
        return False

    wait_for(opengl_ready, 'Mesa GL context', 30)
    if not args.desktop:
        start(['openbox', '--sm-disable'], 'window-manager', ENV)
    existing_windows = set(windows('.*', visible=False))
    start(['ros2', 'launch', 'agibot_g2_demo', 'sim.launch.py', 'enable_motion:=true'], 'simulation', ENV)
    gazebo_process = start(['ign', 'gazebo', '-g', '-v', '3', '--render-engine', 'ogre'], 'gazebo-gui', ENV)
    half = args.width // 2
    view_height = args.height - 240
    config = session_rviz_config(
        Path(get_package_share_directory('agibot_g2_demo'))/'config/g2_demo.rviz',
        half, 0, half, view_height)
    rviz_env = rviz_environment()
    rviz_gl = subprocess.run(['glxinfo', '-B'], env=rviz_env, capture_output=True,
                             text=True, check=True, timeout=10)
    (OUT/'rviz-opengl.txt').write_text(rviz_gl.stdout, encoding='utf-8')
    rviz_executable = str(Path(get_package_prefix('agibot_g2_visual_tools')) /
                          'lib/agibot_g2_visual_tools/rviz2_close_order')
    rviz_process = start([rviz_executable, '-d', config, '--ros-args', '-r', '__node:=rviz2',
                      '-r', '__ns:=/g2/tools', '-p', 'use_sim_time:=true'], 'rviz2', rviz_env)
    observer_process = start(['python3', '/opt/demo/scripts/visual_observer.py', '--output',
                      str(OUT/'observer.json')], 'observer', ENV)
    gazebo, gazebo_pid = wait_for(lambda: owned_window('Gazebo|Ignition', existing_windows, gazebo_process), 'owned Gazebo window')
    rviz, rviz_pid = wait_for(lambda: owned_window('RViz|rviz', existing_windows, rviz_process), 'owned RViz window')
    observer, observer_pid = wait_for(lambda: owned_window('G2 Live State', existing_windows, observer_process), 'owned state observer window')
    place(gazebo, 'G2 Gazebo - physics source', 0, 0, half, view_height)
    # Native Xorg/Mesa can crash in XPutImage on exit after an external resize.
    # The session config establishes the requested size before rendering starts.
    place(rviz, 'G2 RViz2 - same Gazebo TF', half, 0, half, view_height, resize=False)
    place(observer, 'G2 Live State - explicit motion only', 0, view_height+25, args.width, 190)
    if not args.desktop:
        start(['x11vnc', '-display', ':99', '-rfbauth', str(secret), '-localhost',
                          '-rfbport', '5900', '-forever', '-shared', '-noxdamage', '-quiet'], 'vnc', ENV)
        start(['websockify', '--web=/usr/share/novnc', '0.0.0.0:6080',
                          '127.0.0.1:5900'], 'websockify', ENV)

    def observer_ready():
        try:
            return json.loads((OUT/'observer.json').read_text()).get('ready', False)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    wait_for(observer_ready, 'clock, source feedback and existing Trigger service', 180)
    # This receipt proves process/service readiness only. Browser visibility,
    # interaction and TF checks are separate acceptance evidence.
    receipt = {'state': 'READY', 'motion_started_automatically': False,
               'world': 'g2_demo', 'backend': 'gazebo', 'display': ENV['DISPLAY'],
               'desktop_mode': args.desktop, 'width': args.width, 'height': args.height,
               'description_topic': '/g2/sim/robot_description', 'fixed_frame': 'world',
               'rviz_session_config': config,
               'rviz_executable': rviz_executable,
               'renderer_selection': {'gazebo': ENV.get('GALLIUM_DRIVER', 'Mesa software default'),
                                      'rviz2_requested_driver': 'softpipe'},
               'renderer_evidence': {'gazebo': 'opengl.txt', 'rviz2': 'rviz-opengl.txt'},
               'web_port': None if args.desktop else 6080,
               'authentication': 'existing Xauthority' if args.desktop else 'VNC password-file',
               'windows': {'gazebo': gazebo, 'rviz2': rviz, 'observer': observer},
               'window_owner_pids': {'gazebo': gazebo_pid, 'rviz2': rviz_pid, 'observer': observer_pid},
               'window_selection': 'new XID and live component descendant PID; existing windows excluded',
               'processes': [{'label': label, 'pid': process.pid} for label, process in supervisor.PROCESSES]}
    (OUT/'visual-session.json').write_text(json.dumps(receipt, indent=2))
    print('READY: real Gazebo + RViz2 + live state desktop. No action has been sent.', flush=True)
    while not STOPPING:
        for label, process in LIVE_PROCESSES:
            if process.poll() is not None:
                raise RuntimeError(f'{label} exited during interactive session: {process.returncode}')
        time.sleep(.25)


def cleanup():
    """Stop GUI dependents in reverse order, then simulation and display services."""
    errors = []
    for label, process in reversed(supervisor.PROCESSES):
        try:
            supervisor.stop(process)
        except Exception as error:
            errors.append({'label': label, 'error': str(error)})
    supervisor.TRACKING = False
    signalled = []
    for sig, budget in [(signal.SIGINT, 8.), (signal.SIGTERM, 5.)]:
        for pid in supervisor.remaining_owned():
            try:
                os.kill(pid, sig)
                signalled.append({'pid': pid, 'signal': sig.name})
            except ProcessLookupError:
                pass
        end = time.monotonic()+budget
        while supervisor.remaining_owned() and time.monotonic() < end:
            time.sleep(.1)
    remaining = supervisor.remaining_owned()
    if remaining:
        errors.append({'remaining_pids': remaining})
        for pid in remaining:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    for stream in supervisor.FILES:
        stream.close()
    exits = [{'label': label, 'pid': process.pid, 'exit_code': process.poll()}
             for label, process in supervisor.PROCESSES]
    for entry in exits:
        # These display infrastructure programs may use the default signal
        # handler. ROS/Qt applications must finish their shutdown normally.
        expected = {0}
        if entry['label'] in {'xvfb', 'window-manager', 'vnc', 'websockify'}:
            expected |= {-signal.SIGINT, -signal.SIGTERM}
        if entry['exit_code'] not in expected:
            errors.append(dict(entry, error='unexpected component exit'))
    (OUT/'cleanup.json').write_text(json.dumps({'errors': errors,
        'descendant_cleanup': signalled, 'remaining_owned_pids': supervisor.remaining_owned(),
        'processes': exits}, indent=2))
    if errors:
        raise RuntimeError('visual session cleanup failed: '+str(errors))


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    try:
        main()
    finally:
        cleanup()
