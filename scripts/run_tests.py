#!/usr/bin/env python3
"""Run colcon tests, reject empty suites and retain evidence even on failure."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import xml.etree.ElementTree as ET


def run(command, logfile, timeout):
    with logfile.open('w') as output:
        process = subprocess.Popen(command, cwd='/opt/demo', stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mock-only', action='store_true',
                        help='Match the mock image build: exclude the GUI-only CMake package.')
    args = parser.parse_args()
    root = Path('/opt/demo')
    out = Path(os.environ.get('EVIDENCE_DIR', '/evidence'))
    out.mkdir(parents=True, exist_ok=True)
    junit = root / 'build/agibot_g2_demo/pytest.xml'
    commands = [
        ['colcon', 'test', '--event-handlers', 'console_direct+',
         '--return-code-on-test-failure'],
        ['colcon', 'test-result', '--verbose'],
    ]
    if args.mock_only:
        commands[0] += ['--packages-skip', 'agibot_g2_visual_tools']
    codes = []
    summary = {'commands': commands, 'exit_codes': codes, 'groups': {}}
    try:
        for index, command in enumerate(commands):
            log = out / f'colcon-{index}.log'
            codes.append(run(command, log, 540 if index == 0 else 30))
            print(log.read_text(), flush=True)
        if not junit.is_file():
            raise RuntimeError('No pytest JUnit file produced')
        shutil.copy2(junit, out / 'pytest.xml')
        for case in ET.parse(junit).getroot().iter('testcase'):
            group = 'ros_integration' if 'integration_test' in case.get('classname', '') else 'unit'
            entry = summary['groups'].setdefault(group, {'tests': 0, 'failed': 0, 'skipped': 0})
            entry['tests'] += 1
            entry['failed'] += int(case.find('failure') is not None or case.find('error') is not None)
            entry['skipped'] += int(case.find('skipped') is not None)
        for group in ('unit', 'ros_integration'):
            entry = summary['groups'].get(group, {})
            if entry.get('tests', 0) - entry.get('skipped', 0) < 1 or entry.get('failed', 0):
                codes.append(1)
    except BaseException as error:
        summary['error'] = type(error).__name__ + ': ' + str(error)
        codes.append(124 if isinstance(error, subprocess.TimeoutExpired) else 1)
    finally:
        if (root / 'log').exists():
            shutil.copytree(root / 'log', out / 'colcon-log', dirs_exist_ok=True)
        (out / 'test-summary.json').write_text(json.dumps(summary, indent=2))
    return next((code for code in codes if code), 0)


if __name__ == '__main__':
    sys.exit(main())
