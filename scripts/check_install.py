#!/usr/bin/env python3
"""Check actual installed Python modules, console entry points and resources."""
import importlib.metadata
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from ament_index_python.packages import get_package_prefix, get_package_share_directory
import agibot_g2_demo

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--visual', action='store_true', help='Also require the installed RViz infrastructure entry point.')
args = parser.parse_args()
prefix = Path(get_package_prefix('agibot_g2_demo')).resolve()
share = Path(get_package_share_directory('agibot_g2_demo')).resolve()
module = Path(agibot_g2_demo.__file__).resolve()
assert prefix in module.parents, (prefix, module)
distribution = importlib.metadata.distribution('agibot-g2-demo')
entries = {item.name: item.value for item in distribution.entry_points
           if item.group == 'console_scripts'}
assert entries['sayHello'] == 'agibot_g2_demo.say_hello_node:main'
assert entries['telemetry'] == 'agibot_g2_demo.telemetry_node:main'
scripts = {}
for name in ('sayHello', 'telemetry'):
    path = prefix / 'lib/agibot_g2_demo' / name
    content = path.read_bytes()
    assert content.startswith(b'#!') and b'python' in content.splitlines()[0]
    scripts[name] = {'path': str(path), 'shebang': content.splitlines()[0].decode()}
for name in ('launch/demo.launch.py', 'config/mock.yaml', 'config/hardware.example.yaml',
             'launch/sim.launch.py', 'config/sim.yaml', 'config/g2_demo.rviz'):
    assert (share / name).is_file(), name
if args.visual:
    visual_prefix = Path(get_package_prefix('agibot_g2_visual_tools')).resolve()
    executable = visual_prefix / 'lib/agibot_g2_visual_tools/rviz2_close_order'
    assert executable.is_file() and os.access(executable, os.X_OK), executable
    assert executable.read_bytes()[:4] == b'\x7fELF', executable
    linkage = subprocess.run(['ldd', '-r', str(executable)], capture_output=True,
                             text=True, check=True, timeout=15)
    assert 'not found' not in linkage.stdout and 'undefined symbol:' not in linkage.stdout, linkage.stdout
    scripts['rviz2_close_order'] = {'path': str(executable), 'linkage': linkage.stdout}
print(json.dumps({'python': sys.version, 'interpreter': sys.executable,
                  'module': str(module), 'prefix': str(prefix),
                  'entries': entries, 'scripts': scripts}, indent=2))
