"""The prerequisite check must reject unsupported host and remote Docker execution."""
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / 'scripts'
if not SCRIPTS.exists():
    SCRIPTS = Path('/opt/demo/scripts')
sys.path.insert(0, str(SCRIPTS))
from doctor import validate_environment


def checks():
    outputs = [
        (['docker', 'context', 'inspect'], json.dumps({'Host': 'unix:///var/run/docker.sock'})),
        (['docker', 'info'], json.dumps({'OSType': 'linux', 'Architecture': 'aarch64'})),
        (['docker', 'buildx', 'inspect'], 'Driver: docker\nEndpoint: default\nStatus: running\n'),
        (['cat', '/etc/os-release'], 'ID=ubuntu\nVERSION_ID="22.04"\n'),
        (['systemctl', 'show', 'docker'], 'ActiveState=active\nMainPID=123\n'),
    ]
    return [{'command': command, 'stdout': output, 'exit_code': 0} for command, output in outputs]


def test_native_local_daemon_and_bare_metal_are_supported():
    data = checks() + [{'command': ['systemd-detect-virt'], 'exit_code': 1, 'stdout': 'none'}]
    errors, warnings, preflight, validation = validate_environment(data, 'Linux', 'aarch64', {})
    assert errors == []
    assert warnings == []
    assert preflight == 'PASS'
    assert validation == 'PASS'


def test_amd64_support_is_preflight_only_when_matching_daemon_is_amd64():
    data = checks()
    data[1]['stdout'] = json.dumps({'OSType': 'linux', 'Architecture': 'amd64'})
    errors, warnings, preflight, validation = validate_environment(data, 'Linux', 'x86_64', {})
    assert errors == []
    assert warnings
    assert any('x86_64/amd64' in item for item in warnings)
    assert preflight == 'PASS'
    assert validation == 'NOT_TESTED'


@pytest.mark.parametrize('system,machine', [('Darwin', 'arm64'), ('Linux', 'riscv64')])
def test_unsupported_host_fails(system, machine):
    assert validate_environment(checks(), system, machine, {})[0]


@pytest.mark.parametrize('key,value', [('DOCKER_HOST', 'tcp://remote:2375'),
                                      ('DOCKER_CONTEXT', 'remote'),
                                      ('BUILDX_BUILDER', 'remote'),
                                      ('BUILDKIT_HOST', 'tcp://remote:1234')])
def test_remote_overrides_fail(key, value):
    assert validate_environment(checks(), 'Linux', 'aarch64', {key: value})[0]


@pytest.mark.parametrize('command,output', [
    (['docker', 'context', 'inspect'], '{"Host":"ssh://other-host"}'),
    (['docker', 'info'], '{"OSType":"linux","Architecture":"x86_64"}'),
    (['docker', 'buildx', 'inspect'], 'Driver: remote\nEndpoint: remote\nStatus: running\n'),
    (['systemctl', 'show', 'docker'], 'ActiveState=inactive\n'),
    (['cat', '/etc/os-release'], 'ID=ubuntu\nVERSION_ID="24.04"\n'),
])
def test_wrong_execution_identity_fails(command, output):
    data = checks()
    next(item for item in data if item['command'] == command)['stdout'] = output
    assert validate_environment(data, 'Linux', 'aarch64', {})[0]


@pytest.mark.parametrize('command', [['docker', 'compose', 'version'], ['docker', 'buildx', 'version'],
                                      ['make', '--version'], ['python3', '--version']])
def test_required_tool_failure_fails(command):
    data = checks() + [{'command': command, 'exit_code': 127, 'stdout': ''}]
    assert validate_environment(data, 'Linux', 'aarch64', {})[0]
