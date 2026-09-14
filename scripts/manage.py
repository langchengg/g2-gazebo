#!/usr/bin/env python3
"""Bounded commands, per-run evidence and cleanup of only our own containers."""
import datetime
import json
import os
import platform
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from source_manifest import manifest

ROOT = Path(__file__).resolve().parents[1]
ACTION = sys.argv[1] if len(sys.argv) > 1 else 'doctor'
RUN = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
OUT = ROOT / '.artifacts' / ACTION / RUN
OUT.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, EVIDENCE_DIR=str(OUT))
RECORDS = []

def terminate(_signum, _frame):
    # Raising unwinds command/main finally blocks so their own resources close.
    raise SystemExit(143)

signal.signal(signal.SIGTERM, terminate)

def command(args, timeout=1200):
    started = time.monotonic()
    print('+', ' '.join(args), flush=True)
    logfile = OUT / f'{len(RECORDS):02d}-command.log'
    with logfile.open('w') as log:
        proc = subprocess.Popen(args, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except BaseException as exc:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            RECORDS.append({'command': args, 'exit_code': proc.returncode,
                            'failure': type(exc).__name__, 'duration_s': time.monotonic()-started,
                            'log': str(logfile.relative_to(ROOT))})
            (OUT / 'commands.json').write_text(json.dumps(RECORDS, indent=2))
            print(logfile.read_text()[-14000:], flush=True)
            raise
    RECORDS.append({'command': args, 'exit_code': code, 'duration_s': time.monotonic()-started, 'log': str(logfile.relative_to(ROOT))})
    print(logfile.read_text()[-14000:], flush=True)
    (OUT / 'commands.json').write_text(json.dumps(RECORDS, indent=2))
    if code:
        raise subprocess.CalledProcessError(code, args)

def check_image(environment):
    """Refuse to test an old image while reporting a newer working tree hash."""
    result = subprocess.run(['docker', 'image', 'inspect', 'agibot-g2-demo:humble',
                             '--format', '{{.Id}}'], capture_output=True, text=True,
                            check=True, timeout=15)
    image_id = result.stdout.strip()
    data = subprocess.run(['docker', 'run', '--rm', '--network', 'none',
                           '--entrypoint', 'cat', image_id,
                           '/opt/demo/source-manifest.json'], capture_output=True,
                          text=True, check=True, timeout=30)
    image_source = json.loads(data.stdout)
    environment['tested_image_id'] = image_id
    environment['image_source'] = image_source
    environment['source_match'] = image_source == manifest(ROOT, 'runtime')
    (OUT/'environment.json').write_text(json.dumps(environment, indent=2))
    if not environment['source_match']:
        raise ValueError('SOURCE MISMATCH: rebuild the image before running current sources')

def main():
    common = ['docker', 'compose', '-f', str(ROOT / 'compose.yaml')]
    environment={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'host_os':platform.platform(),'host_machine':platform.machine(),
                 'sdk':'NOT SUPPLIED; no hardware tests',
                 'source':manifest(ROOT, 'runtime'),
                 'docker_overrides':{key:os.environ.get(key) for key in ('DOCKER_HOST','DOCKER_CONTEXT')}}
    for key,args in [('docker_context',['docker','context','show']),
                     ('docker_endpoints',['docker','context','inspect','--format','{{json .Endpoints.docker}}']),
                     ('builder',['docker','buildx','inspect']),
                     ('daemon',['docker','info','--format','{{.Name}} {{.OSType}} {{.Architecture}} {{.OperatingSystem}}']),
                     ('image',['docker','image','inspect','agibot-g2-demo:humble','--format','{{.Id}} {{.Architecture}}'])]:
        try:
            item=subprocess.run(args,capture_output=True,text=True,timeout=15)
            environment[key]={'exit_code':item.returncode,'output':item.stdout.strip()}
        except (OSError,subprocess.TimeoutExpired) as error:
            environment[key]={'error':str(error)}
    (OUT/'environment.json').write_text(json.dumps(environment,indent=2))
    if ACTION in ('up', 'test', 'verify', 'demo-mock'):
        check_image(environment)
    if ACTION in ('build', 'clean-build'):
        args = common + ['--progress', 'plain', 'build']
        if ACTION == 'clean-build':
            args += ['--no-cache']
        command(args, 1800)
        check_image(environment)
    elif ACTION == 'up':
        command(common + ['up', '-d', '--no-build'], 90)
        command(common + ['exec', '-T', 'demo', '/opt/demo/docker/entrypoint.sh',
                         'python3', '/opt/demo/scripts/hello.py', '--ready-only'], 40)
    elif ACTION == 'hello':
        command(common + ['exec', '-T', 'demo', '/opt/demo/docker/entrypoint.sh',
                         'python3', '/opt/demo/scripts/hello.py'], 40)
    elif ACTION == 'logs':
        command(common + ['logs', '--no-color', '--tail', '200'], 30)
    elif ACTION == 'down':
        command(common + ['down', '--timeout', '10'], 45)
    elif ACTION in ('test', 'verify', 'demo-mock'):
        project = 'g2-' + ACTION + '-' + uuid.uuid4().hex[:8]
        name = project + '-runner'
        isolated = common + ['-p', project]
        try:
            if ACTION == 'test':
                inner = ['python3', '/opt/demo/scripts/run_tests.py', '--mock-only']
            else:
                inner = ['python3', '/opt/demo/src/agibot_g2_demo/test/integration_test.py', '--verify', '--output', '/evidence']
            command(isolated + ['run', '--rm', '--no-deps', '--name', name, 'demo'] + inner, 650 if ACTION == 'test' else 120)
        finally:
            command(isolated + ['down', '--timeout', '10', '--remove-orphans'], 45)
    else:
        raise ValueError('Unknown action: ' + ACTION)
    print('Evidence:', OUT)

if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1)
