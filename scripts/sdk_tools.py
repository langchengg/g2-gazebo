#!/usr/bin/env python3
"""Bounded official-installer acquisition and honest SDK stage gates."""
import argparse
import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/agibot_g2_demo'))
from agibot_g2_demo.sdk_acquisition import AcquisitionError, RESOURCES, fetch_installer, inspect_artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fetch', 'inspect', 'build', 'smoke'))
    parser.add_argument('--file', type=Path, help='static inspection only; never execute')
    parser.add_argument('--sha256', help='independently supplied expected hash')
    args = parser.parse_args()
    cache = ROOT / '.artifacts/gdk/2.6.3'
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    code = 0
    if args.action == 'fetch':
        for name in RESOURCES:
            try:
                item = fetch_installer(name, cache / 'installers')
                records.append(dict(resource=name, result='INSTALLER_FETCHED_REVIEW_REQUIRED', **item))
            except AcquisitionError as error:
                code = 2
                records.append(dict(resource=name, result='BLOCKED', reason=str(error)))
    elif args.action == 'inspect' and args.file:
        try:
            records.append(inspect_artifact(args.file, args.sha256))
        except AcquisitionError as error:
            code = 2
            records.append(dict(result='BLOCKED', reason=str(error)))
    else:
        # No actual payload/layout/license/version has been obtained. Do not
        # invent COPY paths, distribution names, installer flags or a fake import.
        code = 2
        records.append(dict(result='BLOCKED', stage={'inspect': 'S0', 'build': 'S1',
                              'smoke': 'S1/S2'}[args.action],
                            reason='No verified GDK 2.6.3 payload/distribution available. '
                            'The documented robot-hosted installer could not be obtained; '
                            'installation and native import have NOT RUN.',
                            native_import_executed=False, robot_connection_attempted=False))
    result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  action=args.action, exit_code=code, records=records)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = cache / (args.action + '-' + stamp + '.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
