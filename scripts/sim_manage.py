#!/usr/bin/env python3
"""Run project-scoped Fortress commands and retain failures and source identity."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid
from source_manifest import manifest

ROOT = Path(__file__).resolve().parents[1]
KEY = hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]
IMAGE = os.environ.get('SIM_IMAGE', 'agibot-g2-sim:fortress-' + KEY)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'doctor', 'up', 'hello', 'down', 'logs', 'verify', 'test', 'demo', 'record'])
    parser.add_argument('--no-cache', action='store_true')
    args = parser.parse_args()
    run = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    out = ROOT / '.artifacts/gazebo' / run
    out.mkdir(parents=True)
    records = []
    env = dict(os.environ, EVIDENCE_DIR=str(out), SIM_IMAGE=IMAGE)
    model = Path(env.get('G2_MODEL_DIR', str(ROOT / '.artifacts/gazebo-model/generated'))).resolve()
    env['G2_MODEL_DIR'] = str(model)
    project = 'g2-sim-' + run.lower()
    name = project + '-runner'

    def command(argv, timeout=120, allow_failure=False):
        log = out / (str(len(records)).zfill(2) + '-command.log')
        print('+', ' '.join(argv), flush=True)
        start = time.monotonic()
        failure = None
        with log.open('w') as stream:
            proc = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout)
            except BaseException as error:
                failure = type(error).__name__
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(5)
                code = (124 if isinstance(error, subprocess.TimeoutExpired) else
                        int(error.code) if isinstance(error, SystemExit) and isinstance(error.code, int) else
                        130 if isinstance(error, KeyboardInterrupt) else 1)
            records.append({'argv': argv, 'exit_code': code, 'error': failure,
                            'wall_seconds': time.monotonic()-start, 'log': str(log)})
            (out / 'commands.json').write_text(json.dumps(records, indent=2))
        print(log.read_text()[-14000:], flush=True)
        if code and not allow_failure:
            raise subprocess.CalledProcessError(code, argv)
        return log.read_text(), code

    def check_model():
        data = json.loads((model / 'generated_manifest.json').read_text())
        for relative, digest in data['files'].items():
            path = model / relative
            if not path.resolve().is_relative_to(model) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('model cache checksum mismatch: ' + relative)
        (out / 'model-manifest.json').write_text(json.dumps(data, indent=2))

    compose = ['docker', 'compose', '-p', 'agibot-g2-sim-' + KEY, '-f', str(ROOT / 'compose.sim.yaml')]
    environment = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'source': manifest(ROOT, 'runtime'), 'model_dir': str(model),
                   'overrides': {k: env.get(k) for k in ['DOCKER_HOST', 'DOCKER_CONTEXT']}}
    for key, argv in [('host', ['uname', '-a']), ('daemon', ['docker', 'info', '--format', '{{.Name}} {{.OperatingSystem}} {{.Architecture}}']),
                      ('context', ['docker', 'context', 'inspect', '--format', '{{json .Endpoints.docker}}']),
                      ('builder', ['docker', 'buildx', 'inspect'])]:
        text, code = command(argv, 30)
        environment[key] = text.strip()
    if args.action == 'build':
        argv = ['docker', 'build', '--progress=plain', '-f', 'Dockerfile.sim', '--target', 'simulation', '-t', IMAGE]
        if args.no_cache:
            argv.append('--no-cache')
        command(argv + ['.'], 3600)
    if args.action not in ['down', 'logs']:
        image, _ = command(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}} {{.Architecture}}'], 20)
        environment['image'] = image.strip()
        text, _ = command(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'cat', IMAGE,
                           '/opt/demo/source-manifest.json'], 30)
        actual = json.loads(text)
        if actual != environment['source'] or actual != manifest(ROOT, 'runtime'):
            raise ValueError('image/source mismatch; rebuild before testing current changes')
        environment['image_source_matches'] = True
    (out / 'environment.json').write_text(json.dumps(environment, indent=2))
    if args.action in ['doctor', 'up', 'verify', 'test', 'demo', 'record']:
        check_model()
    if args.action == 'up':
        command(compose + ['up', '-d', '--no-build'], 90)
    elif args.action == 'hello':
        command(compose + ['exec', '-T', 'sim', '/opt/demo/docker/sim-entrypoint.sh',
                          'python3', '/opt/demo/scripts/sim_hello.py'], 30)
    elif args.action == 'down':
        command(compose + ['down', '--timeout', '20'], 45)
    elif args.action == 'logs':
        command(compose + ['logs', '--no-color', '--tail', '200'], 30)
    elif args.action == 'doctor':
        command(['docker', 'run', '--rm', '--network', 'none',
                 '--mount', 'type=bind,src='+str(model)+',dst=/opt/g2-model,readonly', IMAGE, 'bash', '-c',
                 'python3 /opt/demo/scripts/check_install.py && /opt/demo/check_mesh /opt/g2-model/meshes && '
                 'xvfb-run -a glxinfo -B && ign gazebo --versions && '
                 'ros2 pkg prefix gz_ros2_control && ros2 pkg prefix ros_gz_bridge && '
                 'dpkg-query -W ignition-fortress libignition-gazebo6 ros-humble-ros-gz-bridge'], 60)
    elif args.action in ['verify', 'test', 'demo', 'record']:
        env['SIM_PARTITION'] = project
        argv = ['docker', 'run', '--name', name, '--init', '--network', 'none',
                '-e', 'IGN_PARTITION='+project, '-e', 'GZ_PARTITION='+project,
                '-e', 'ROS_DOMAIN_ID=43', '-e', 'EVIDENCE_DIR=/evidence',
                '--mount', 'type=bind,src='+str(model)+',dst=/opt/g2-model,readonly',
                '--mount', 'type=bind,src='+str(out)+',dst=/evidence', IMAGE,
                'python3', '/opt/demo/scripts/run_sim.py', '--mode', args.action]
        try:
            command(argv, 1000 if args.action == 'test' else 600)
        finally:
            # Only this uniquely named run is touched, even on timeouts.
            text, code = command(['docker', 'inspect', '--format', '{{.State.Status}}', name], 15, allow_failure=True)
            if code == 0:
                command(['docker', 'stop', '--time', '20', name], 35)
                command(['docker', 'rm', name], 15)
            elif 'No such object' not in text:
                raise RuntimeError('cannot verify cleanup for ' + name)
    print('Evidence:', out)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    main()
