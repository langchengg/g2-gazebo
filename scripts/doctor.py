#!/usr/bin/env python3
"""Inspect and classify the supported Linux host and local Docker daemon."""
import datetime
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys


def normalize_arch(value):
    """Return canonical architecture used across host/daemon checks."""
    if value is None:
        return None
    value = value.lower()
    if value in ('aarch64', 'arm64'):
        return 'arm64'
    if value in ('x86_64', 'amd64'):
        return 'amd64'
    return value


def validate_environment(checks, system, machine, environ):
    errors = []
    warnings = []

    host_arch = normalize_arch(machine)
    if system != 'Linux':
        errors.append('The tested simulation path requires Linux.')
    if host_arch not in ('arm64', 'amd64'):
        errors.append('The tested host architecture is unsupported for this project flow.')

    for item in checks:
        command = item['command']
        # Bare metal returns 1 for systemd-detect-virt; Git is optional in archives.
        if item['exit_code'] and command[0] not in ('git', 'systemd-detect-virt'):
            errors.append('Required host/tool check failed: ' + ' '.join(command))

    def output(prefix):
        return next((item.get('stdout', '') for item in checks
                     if item['command'][:len(prefix)] == prefix and not item['exit_code']), '')

    try:
        endpoint = json.loads(output(['docker', 'context', 'inspect']))['Host']
        if endpoint != 'unix:///var/run/docker.sock':
            errors.append('Docker context must use the local unix:///var/run/docker.sock daemon.')
    except (ValueError, KeyError, TypeError):
        errors.append('Cannot verify the Docker context endpoint.')

    if environ.get('DOCKER_HOST') not in (None, '', 'unix:///var/run/docker.sock'):
        errors.append('DOCKER_HOST must not select an external daemon.')
    if environ.get('DOCKER_CONTEXT') not in (None, '', 'default'):
        errors.append('Unset DOCKER_CONTEXT or use default for this local-daemon workflow.')
    if environ.get('BUILDX_BUILDER') not in (None, '', 'default') or environ.get('BUILDKIT_HOST'):
        errors.append('Unset external Buildx/BuildKit overrides; use the local default builder.')

    try:
        daemon = json.loads(output(['docker', 'info']))
        if daemon.get('OSType') != 'linux':
            errors.append('Docker server must run on Linux.')
        daemon_arch = normalize_arch(daemon.get('Architecture'))
        if daemon_arch not in ('arm64', 'amd64'):
            errors.append('Docker server architecture is unsupported by this project flow.')
        elif host_arch and daemon_arch != host_arch:
            errors.append('Host architecture and Docker daemon architecture must match.')
    except (ValueError, TypeError):
        errors.append('Cannot verify Docker server architecture.')
        daemon_arch = None
    else:
        if host_arch == 'amd64' and daemon_arch == 'amd64':
            warnings.append('x86_64/amd64 reached preflight without native validation evidence.')

    builder = output(['docker', 'buildx', 'inspect'])
    fields = {}
    for line in builder.splitlines():
        if ':' in line:
            key, value = line.strip().split(':', 1)
            fields.setdefault(key, []).append(value.strip())
    if fields.get('Driver') != ['docker'] or fields.get('Endpoint') != ['default']:
        errors.append('Buildx must use the default local Docker driver, not a remote worker.')
    if fields.get('Status') != ['running']:
        errors.append('The local Buildx worker must be running.')

    os_release = output(['cat', '/etc/os-release'])
    if 'ID=ubuntu' not in os_release or 'VERSION_ID="22.04"' not in os_release:
        errors.append('The tested host prerequisite is Ubuntu 22.04.')

    service = output(['systemctl', 'show', 'docker'])
    if 'ActiveState=active' not in service:
        errors.append('The local Docker system service must be active.')

    preflight = 'PASS' if not errors else 'FAIL'
    # This command checks prerequisites only.  A successful preflight is not
    # evidence that this source revision completed the runtime acceptance suite.
    validation = 'NOT_TESTED'
    return errors, warnings, preflight, validation


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    out = root / '.artifacts' / 'doctor'
    out.mkdir(parents=True, exist_ok=True)
    commands = [['hostname'], ['uname', '-a'], ['python3', '--version'], ['make', '--version'],
                ['df', '-h', str(root)], ['docker', 'version'], ['docker', 'context', 'show'],
                ['docker', 'context', 'inspect', '--format', '{{json .Endpoints.docker}}'],
                ['docker', 'info', '--format',
                 '{"Name":{{json .Name}},"OSType":{{json .OSType}},"Architecture":{{json .Architecture}},"OperatingSystem":{{json .OperatingSystem}},"NCPU":{{json .NCPU}},"MemTotal":{{json .MemTotal}}}'],
                ['docker', 'compose', 'version'], ['docker', 'buildx', 'version'],
                ['docker', 'buildx', 'inspect']]
    if platform.system() == 'Linux':
        commands += [['cat', '/etc/os-release'], ['dpkg', '--print-architecture'], ['free', '-h'],
                     ['systemd-detect-virt'], ['systemctl', 'show', 'docker', '-p', 'ActiveState', '-p', 'MainPID'],
                     ['stat', '-c', '%F %U:%G %a %n', '/var/run/docker.sock'], ['pgrep', '-x', 'dockerd']]
    if (root / '.git').exists():
        commands += [['git', 'status', '--short', '--branch']]

    results = []
    for command in commands:
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=20)
            item = {'command': command, 'exit_code': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr}
        except (OSError, subprocess.TimeoutExpired) as exc:
            item = {'command': command, 'exit_code': 124, 'error': str(exc)}
        results.append(item)
        print(json.dumps(item, ensure_ascii=False))

    errors, warnings, preflight, validation = validate_environment(results, platform.system(), platform.machine(), os.environ)
    report = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'execution_host': platform.platform(), 'machine': platform.machine(),
              'docker_overrides': {key: os.environ.get(key) for key in ['DOCKER_HOST', 'DOCKER_CONTEXT']},
              'tools': {name: shutil.which(name) for name in ['docker', 'make', 'python3']},
              'checks': results, 'errors': errors, 'warnings': warnings,
              'preflight_result': preflight,
              'validation_status': validation,
              'result': 'FAIL' if errors else 'PASS'}
    (out / 'report.json').write_text(json.dumps(report, indent=2))
    for error in errors:
        print('FAIL: ' + error, file=sys.stderr)
    for warn in warnings:
        print('WARN: ' + warn, file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
