#!/usr/bin/env python3
"""Record the existing real desktop; optional explicit motion uses the ROS probe.

Does not start a world or GUI. DISPLAY and dimensions come from this session's
receipt. The capture is wall-clock 1x playback, including slow simulation.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(12)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(5)
            raise RuntimeError('recorder required SIGTERM')


def wait_for_first_frame(process, progress_path, timeout=15.):
    """Require FFmpeg's completed progress block to report a captured frame."""
    started = time.monotonic()
    deadline = started + timeout
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise RuntimeError(f'capture exited before first-frame readiness: {code}; see ffmpeg.log')
        try:
            progress = progress_path.read_text()
        except FileNotFoundError:
            progress = ''
        block = {}
        for line in progress.splitlines():
            key, separator, value = line.partition('=')
            if not separator:
                continue
            block[key] = value
            if key == 'progress' and value in ('continue', 'end'):
                frames = block.get('frame', '').strip()
                if frames.isdigit() and int(frames) > 0:
                    return {'frames': int(frames), 'wall_seconds': time.monotonic()-started}
                block = {}
        time.sleep(min(.05, max(0., deadline-time.monotonic())))
    raise TimeoutError(f'capture produced no first frame before the {timeout:g}-second readiness deadline; no motion was started')


def capture_luma_quality(video, output, timeout=20.):
    """Reject an entirely near-black capture; never prove model visibility."""
    command = ['ffmpeg', '-v', 'error', '-nostdin', '-threads', '1',
        '-filter_threads', '1', '-i', str(video), '-vf',
        'scale=320:-2:flags=area:out_range=full,format=yuv420p,signalstats,'
        'metadata=mode=print:key=lavfi.signalstats.YAVG:file=-',
        '-an', '-f', 'null', '-']
    result = subprocess.run(command, capture_output=True, text=True,
                            check=True, timeout=timeout)
    output.with_suffix('.txt').write_text(result.stdout, encoding='utf-8')
    values = [float(line.partition('=')[2]) for line in result.stdout.splitlines()
              if line.startswith('lavfi.signalstats.YAVG=')]
    if not values or any(not math.isfinite(value) or not 0 <= value <= 255
                         for value in values):
        raise RuntimeError('missing or invalid decoded frame luma statistics')
    black = max(values) <= 2.0
    quality = {'result': 'FAIL' if black else 'PASS',
        'criterion': 'reject only when every decoded frame mean full-range 8-bit luma <= 2',
        'decoded_frames': len(values), 'minimum_yavg': min(values),
        'maximum_yavg': max(values), 'all_frames_near_black': black,
        'visual_model_and_motion_observation': 'NOT TESTED; manual GUI inspection still required',
        'command': command}
    output.write_text(json.dumps(quality, indent=2), encoding='utf-8')
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, default=Path('/evidence/visual-session.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--motion', action='store_true', help='Explicitly verify one motion through existing /g2/say_hello')
    parser.add_argument('--duration', type=float, default=40.)
    args = parser.parse_args()
    if not 1 <= args.duration <= 180:
        parser.error('duration must be between 1 and 180 seconds')
    session = json.loads(args.session.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    size = f"{session['width']}x{session['height']}"
    display = session['display']
    env = dict(os.environ, DISPLAY=display)
    processes = []
    streams = []
    error = None
    succeeded = False
    first_frame = None
    capture_quality = None
    started = time.monotonic()

    def start(command, filename):
        stream = (args.output/filename).open('w')
        streams.append(stream)
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True)
        processes.append(process)
        return process

    try:
        capture = start(['ffmpeg', '-y', '-nostdin', '-f', 'x11grab', '-video_size', size,
            '-framerate', '10', '-i', display, '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '23', '-pix_fmt', 'yuv420p', '-stats_period', '0.2',
            '-progress', str(args.output/'ffmpeg-progress.txt'),
            str(args.output/'gazebo-rviz-state.mp4')], 'ffmpeg.log')
        first_frame = wait_for_first_frame(capture, args.output/'ffmpeg-progress.txt')
        # FFmpeg startup and TF subscriptions must be live before the motion
        # probe gathers its own baseline. Neither starts a second simulator.
        tf = start(['python3', '/opt/demo/scripts/verify_visual.py', '--duration', str(args.duration),
            '--timeout', '220', '--output', str(args.output/'tf-correlation.json')] +
            (['--require-motion', '--motion-result', str(args.output/'motion/result.json')]
             if args.motion else []), 'tf-check.log')
        if args.motion:
            motion = start(['python3', '/opt/demo/scripts/verify_sim.py', '--mode', 'motion',
                '--evidence-dir', str(args.output/'motion')], 'motion-check.log')
            if motion.wait(max(.1, 225-(time.monotonic()-started))):
                raise RuntimeError('motion verification failed; see motion-check.log')
        if tf.wait(max(.1, 230-(time.monotonic()-started))):
            raise RuntimeError('TF correlation failed; see tf-check.log')
        if args.motion:
            motion_result = json.loads((args.output/'motion/result.json').read_text())
            tf_result = json.loads((args.output/'tf-correlation.json').read_text())
            run_id = motion_result['run_ids'][0]
            matching = [row for row in tf_result['samples'] if row['run_id'] == run_id]
            assert len(matching) >= 10, 'insufficient TF evidence for this motion run_id'
            values = [row['position_rad'] for row in matching]
            assert max(values)-min(values) > .04, 'TF did not follow this run_id movement'
            assert any(row['state'] == 'RUNNING' for row in matching), 'missing RUNNING TF sample'
            assert any(row['state'] == 'SUCCEEDED' for row in matching), 'missing completed TF sample'
        if capture.poll() is not None:
            raise RuntimeError('capture exited prematurely')
        subprocess.run(['ffmpeg', '-y', '-f', 'x11grab', '-video_size', size, '-i', display,
            '-frames:v', '1', str(args.output/'gazebo-rviz-state.png')], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=20)
        stop(capture)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
            '-of', 'json', str(args.output/'gazebo-rviz-state.mp4')], capture_output=True,
            text=True, check=True, timeout=20)
        media = json.loads(probe.stdout)
        (args.output/'media.json').write_text(json.dumps(media, indent=2))
        assert float(media['format']['duration']) > 5, 'empty or truncated capture'
        capture_quality = capture_luma_quality(
            args.output/'gazebo-rviz-state.mp4', args.output/'capture-quality.json')
        if capture_quality['all_frames_near_black']:
            raise RuntimeError('recorded desktop is entirely near black; restore the visible desktop and record again')
        succeeded = True
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
        raise
    finally:
        cleanup_errors = []
        for process in reversed(processes):
            try:
                stop(process)
            except Exception as exc:
                cleanup_errors.append(str(exc))
        for stream in streams:
            stream.close()
        (args.output/'recording.json').write_text(json.dumps({'result': 'PASS' if succeeded and not cleanup_errors else 'FAIL',
            'error': error, 'cleanup_errors': cleanup_errors, 'session': session,
            'playback': '1x wall-clock; no speed adjustment', 'wall_seconds': time.monotonic()-started,
            'first_frame': first_frame, 'capture_quality': capture_quality,
            'result_scope': 'automated capture/data checks only; actual GUI model and motion require manual observation',
            'motion_explicitly_requested': args.motion}, indent=2))
        if cleanup_errors:
            raise RuntimeError('record cleanup failed: '+str(cleanup_errors))


if __name__ == '__main__':
    def interrupted(*_):
        raise InterruptedError('recording interrupted; cleanup requested')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    main()
