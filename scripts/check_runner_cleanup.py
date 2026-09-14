#!/usr/bin/env python3
"""Exercise only uniquely named demo resources; no robot or VM access.

Default: interrupt manage.py verify with SIGTERM during a confirmed mock run.
Use --also-launch-checks to check unavailable-GDK launch and normal Compose stop.
All commands and outcomes are retained under .artifacts/runner-cleanup/.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
READY_PROBE = r'''
import json, math, sys, time
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
rclpy.init()
node = rclpy.create_node('cleanup_readiness_probe')
samples, states = [], []
stream = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                    durability=DurabilityPolicy.VOLATILE)
latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
sub = node.create_subscription(JointState, '/g2/joint_states', samples.append, stream)
status = node.create_subscription(String, '/g2/hello_status',
                                  lambda m: states.append(json.loads(m.data)), latched)
client = node.create_client(Trigger, '/g2/say_hello')
deadline = time.monotonic() + 12
try:
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        nodes = {(name, ns) for name, ns in node.get_node_names_and_namespaces()}
        expected = {('sayHello', '/g2'), ('telemetry', '/g2')}
        valid = [m for m in samples if len(m.name) == len(m.position) == 6 and
                 len(set(m.name)) == 6 and all(math.isfinite(p) for p in m.position)]
        running = bool(states and states[-1]['state'] == 'RUNNING' and states[-1]['run_id'])
        if expected <= nodes and client.service_is_ready() and len(valid) >= 2 and (
                sys.argv[1] != 'running' or running):
            print(json.dumps({'result': 'READY', 'nodes': sorted(expected),
                              'valid_samples': len(valid),
                              'last_status': states[-1] if states else None}), flush=True)
            break
    else:
        raise RuntimeError('readiness deadline expired before the requested mock state')
finally:
    node.destroy_node()
    rclpy.shutdown()
'''


class Check:
    def __init__(self):
        run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self.out = ROOT / '.artifacts' / 'runner-cleanup' / (run_id + '-' + uuid.uuid4().hex[:8])
        self.out.mkdir(parents=True)
        self.env = dict(os.environ, EVIDENCE_DIR=str(self.out))
        self.records = []
        self.owned = set()
        self.result = {
            'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'host_os': platform.platform(), 'host_machine': platform.machine(),
            'scope': ('Mac Docker supplemental; not Ubuntu VM validation'
                      if platform.system() == 'Darwin' else
                      'Linux Docker cleanup; combine with daemon/VM identity evidence'),
            'sdk': 'NOT SUPPLIED; only unavailable-adapter rejection is exercised',
            'checks': {}, 'result': 'RUNNING',
        }
        self.save()

    def save(self):
        (self.out / 'commands.json').write_text(json.dumps(self.records, indent=2))
        (self.out / 'result.json').write_text(json.dumps(self.result, indent=2))

    def run(self, args, timeout=30, expected=(0,)):
        log = self.out / f'{len(self.records):02d}-command.log'
        started = time.monotonic()
        record = {'command': args, 'log': str(log.relative_to(ROOT))}
        try:
            item = subprocess.run(args, cwd=ROOT, env=self.env, capture_output=True,
                                  text=True, timeout=timeout)
            log.write_text(item.stdout + item.stderr)
            record['exit_code'] = item.returncode
            record['duration_s'] = time.monotonic() - started
            self.records.append(record)
            self.save()
            if expected is not None and item.returncode not in expected:
                raise RuntimeError(f'Unexpected exit {item.returncode}: {args}; see {log}')
            return item
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or b'') + (exc.stderr or b'')
            if isinstance(output, bytes):
                output = output.decode(errors='replace')
            log.write_text(output)
            record.update(exit_code=None, failure='TimeoutExpired', duration_s=time.monotonic()-started)
            self.records.append(record)
            self.save()
            raise

    def compose(self, project):
        if project not in self.owned:
            raise RuntimeError('Refusing to control a project not created by this check')
        return ['docker', 'compose', '-f', str(ROOT / 'compose.yaml'), '-p', project]

    def own(self, prefix):
        project = prefix + '-' + uuid.uuid4().hex[:8]
        self.owned.add(project)
        return project

    def leftovers(self, project):
        if project not in self.owned:
            raise RuntimeError('Refusing to inspect an unowned project')
        label = 'label=com.docker.compose.project=' + project
        containers = self.run(['docker', 'ps', '-aq', '--filter', label]).stdout.split()
        networks = self.run(['docker', 'network', 'ls', '-q', '--filter', label]).stdout.split()
        return {'containers': containers, 'networks': networks}

    def down(self, project):
        self.run(self.compose(project) + ['down', '--timeout', '10', '--remove-orphans'], timeout=45)

    def ready(self, container, running=False):
        return self.run(['docker', 'exec', container, '/opt/demo/docker/entrypoint.sh',
                         'python3', '-c', READY_PROBE, 'running' if running else 'ready'], timeout=16)

    def manager_sigterm(self):
        log = self.out / 'manager.log'
        manager = None
        project = None
        entry = {'result': 'RUNNING', 'manager_log': str(log.relative_to(ROOT))}
        self.result['checks']['manager_sigterm'] = entry
        started = time.monotonic()
        try:
            with log.open('w') as output:
                manager = subprocess.Popen([sys.executable, '-u', str(ROOT / 'scripts/manage.py'), 'verify'],
                                           cwd=ROOT, env=self.env, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    match = re.search(r' -p (g2-verify-[0-9a-f]{8}) run .*? --name (g2-verify-[0-9a-f]{8}-runner) ',
                                      log.read_text())
                    if match:
                        project, container = match.groups()
                        if container != project + '-runner':
                            raise RuntimeError('Manager emitted inconsistent owned resource names')
                        self.owned.add(project)
                        break
                    if manager.poll() is not None:
                        raise RuntimeError(f'Manager exited before creating its project: {manager.returncode}')
                    time.sleep(0.1)
                else:
                    raise RuntimeError('Manager project discovery deadline expired')
                entry.update(project=project, container=container, manager_pid=manager.pid)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    state = self.run(['docker', 'container', 'inspect', '--format',
                                      '{{json .State}}', container], timeout=5, expected=None)
                    if state.returncode == 0 and json.loads(state.stdout)['Running']:
                        entry['container_running_before_signal'] = True
                        break
                    if manager.poll() is not None:
                        raise RuntimeError('Manager exited before its container was running')
                    time.sleep(0.1)
                else:
                    raise RuntimeError('Manager container readiness deadline expired')
                self.ready(container, running=True)
                if manager.poll() is not None:
                    raise RuntimeError('Verify completed before the external SIGTERM could be tested')
                entry['signal'] = 'SIGTERM'
                entry['signal_time_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                manager.send_signal(signal.SIGTERM)
                entry['manager_exit_code'] = manager.wait(timeout=60)
                entry['remaining_after_manager_finally'] = self.leftovers(project)
                entry['elapsed_s'] = time.monotonic() - started
                if entry['manager_exit_code'] != 143:
                    raise RuntimeError(f'Expected intentional SIGTERM exit 143, got {entry["manager_exit_code"]}')
                if any(entry['remaining_after_manager_finally'].values()):
                    raise RuntimeError('Manager finally left its own resources behind')
                entry['result'] = 'PASS'
        finally:
            if manager is not None and manager.poll() is None:
                manager.send_signal(signal.SIGTERM)
                try:
                    manager.wait(timeout=55)
                except subprocess.TimeoutExpired:
                    manager.kill()
                    manager.wait(timeout=5)
            if project is not None:
                remaining = self.leftovers(project)
                if any(remaining.values()):
                    entry['emergency_cleanup_required'] = remaining
                    self.down(project)
                entry['remaining_after_check_cleanup'] = self.leftovers(project)
            self.save()

    def gdk_launch(self):
        project = self.own('g2-cleanup-gdk')
        entry = {'project': project, 'result': 'RUNNING'}
        self.result['checks']['unavailable_gdk_launch'] = entry
        try:
            item = self.run(self.compose(project) + [
                'run', '--rm', '--no-deps', 'demo', 'ros2', 'launch',
                'agibot_g2_demo', 'demo.launch.py', 'backend:=gdk'], timeout=25, expected=None)
            entry['exit_code'] = item.returncode
            if item.returncode == 0 or 'GDK_UNAVAILABLE' not in item.stdout + item.stderr:
                raise RuntimeError('Unavailable GDK launch did not produce explicit nonzero failure')
            entry['result'] = 'PASS'
        finally:
            self.down(project)
            entry['remaining'] = self.leftovers(project)
            if any(entry['remaining'].values()):
                raise RuntimeError('GDK check resources were not removed')
            self.save()

    def normal_stop(self):
        project = self.own('g2-cleanup-stop')
        entry = {'project': project, 'result': 'RUNNING'}
        self.result['checks']['normal_compose_stop'] = entry
        try:
            self.run(self.compose(project) + ['up', '-d', '--no-build', 'demo'], timeout=45)
            container = self.run(self.compose(project) + ['ps', '-q', 'demo']).stdout.strip()
            if not container or '\n' in container:
                raise RuntimeError('Expected exactly one owned Compose demo container')
            entry['container'] = container
            self.ready(container)
            self.run(self.compose(project) + ['stop', '--timeout', '10', 'demo'], timeout=20)
            state = json.loads(self.run(['docker', 'container', 'inspect', '--format',
                                         '{{json .State}}', container]).stdout)
            entry['stopped_state'] = state
            self.run(self.compose(project) + ['logs', '--no-color', 'demo'])
            if state['Running'] or state['ExitCode'] != 0 or state['OOMKilled']:
                raise RuntimeError('Normal Compose stop was not a clean zero exit')
            entry['result'] = 'PASS'
        finally:
            self.down(project)
            entry['remaining'] = self.leftovers(project)
            if any(entry['remaining'].values()):
                raise RuntimeError('Stop check resources were not removed')
            self.save()


def main():
    def terminate(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--also-launch-checks', action='store_true')
    args = parser.parse_args()
    check = Check()
    print('Evidence:', check.out, flush=True)
    try:
        for key, command in (
            ('docker_context', ['docker', 'context', 'show']),
            ('daemon', ['docker', 'info', '--format', '{{.OSType}}/{{.Architecture}} {{.ServerVersion}}']),
            ('image', ['docker', 'image', 'inspect', 'agibot-g2-demo:humble', '--format', '{{.Id}} {{.Architecture}}']),
        ):
            check.result[key] = check.run(command).stdout.strip()
        check.manager_sigterm()
        if args.also_launch_checks:
            check.gdk_launch()
            check.normal_stop()
        check.result['result'] = 'PASS'
        check.save()
        print(json.dumps(check.result, indent=2), flush=True)
        return 0
    except BaseException as error:
        check.result.update(result='FAIL', error=f'{type(error).__name__}: {error}')
        check.save()
        print(json.dumps(check.result, indent=2), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
