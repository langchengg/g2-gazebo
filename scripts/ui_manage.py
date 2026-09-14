#!/usr/bin/env python3
"""Project-scoped persistent GUI on an existing authorized Linux desktop."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
from source_manifest import manifest
from prepare_model import validate_generated

ROOT = Path(__file__).resolve().parents[1]
KEY = hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]
IMAGE = os.environ.get('SIM_IMAGE', 'agibot-g2-sim:fortress-' + KEY)
STATE = ROOT / '.artifacts/visual-session.json'


def call(argv, timeout=30, **kwargs):
    return subprocess.run(argv, check=True, timeout=timeout, **kwargs)


def session():
    if not STATE.exists():
        raise RuntimeError('No visual session. Run make demo-visual in the Ubuntu desktop terminal.')
    data = json.loads(STATE.read_text())
    result = call(['docker', 'inspect', data['container']], capture_output=True, text=True)
    info = json.loads(result.stdout)[0]
    if info['Config']['Labels'].get('org.agibot-g2.source-root') != str(ROOT):
        raise RuntimeError('Session ownership mismatch')
    return data, info


def exec_ros(data, args, timeout=60):
    return call(['docker', 'exec', data['container'], '/opt/demo/docker/sim-entrypoint.sh']+args, timeout)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['up', 'info', 'hello', 'telemetry', 'down', 'record', 'check'])
    args = p.parse_args()
    if args.action == 'up':
        if STATE.exists():
            data, info = session()
            if info['State']['Running']:
                print('Existing session retained; no new world/action started.')
                print(json.dumps(data, indent=2));return
            raise RuntimeError('Stopped session exists. Run make ui-down before restarting.')
        display = os.environ.get('DISPLAY', '')
        authority = Path(os.environ.get('XAUTHORITY', '/nonexistent'))
        if os.environ.get('XDG_SESSION_TYPE') != 'x11':
            raise RuntimeError('Use an Ubuntu on Xorg login session and preserve XDG_SESSION_TYPE. Wayland/XWayland cannot supply this desktop recording path.')
        if not display or not authority.is_file():
            raise RuntimeError('Run in the Ubuntu graphical terminal. Preserve DISPLAY, XAUTHORITY and XDG_SESSION_TYPE when using sudo.')
        model = Path(os.environ.get('G2_MODEL_DIR', str(ROOT/'.artifacts/gazebo-model/generated'))).resolve()
        validate_generated(model)
        current = manifest(ROOT, 'runtime')
        r = call(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'cat', IMAGE,
                  '/opt/demo/source-manifest.json'], capture_output=True, text=True)
        if json.loads(r.stdout) != current:
            raise RuntimeError('Image/source mismatch; run make build-sim')
        tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
        out = ROOT/'.artifacts/visual'/tag;out.mkdir(parents=True)
        secret = out/'xauthority';secret.touch(mode=0o600)
        # Copy only this display's cookie, with family-wild matching for the
        # container hostname. The cookie is never printed or embedded in argv.
        cookie = call(['xauth','-f',str(authority),'nlist',display], capture_output=True).stdout
        if not cookie.strip():
            raise RuntimeError('No Xauthority cookie for the selected DISPLAY')
        cookie = b'\n'.join(b'ffff'+line[4:] for line in cookie.splitlines())+b'\n'
        call(['xauth','-f',str(secret),'nmerge','-'], input=cookie, capture_output=True)
        screen = call(['xrandr','--current'], capture_output=True, text=True).stdout
        match = re.search(r'current (\d+) x (\d+)', screen)
        if not match:raise RuntimeError('Could not determine current desktop dimensions')
        width,height = map(int,match.groups())
        if width<1280 or height<800:raise RuntimeError('Set desktop resolution to at least 1280x800 (recommended1600x900)')
        name='g2-visual-'+KEY+'-'+tag.lower()
        run = ['docker','run','-d','--name',name,'--init','--network','none',
               '--label','org.agibot-g2.source-root='+str(ROOT),
               '-e','IGN_PARTITION='+name,'-e','GZ_PARTITION='+name,
               '-e','DISPLAY='+display,'-e','XAUTHORITY=/run/secrets/xauthority',
               '-e','EVIDENCE_DIR=/evidence','-e','QT_X11_NO_MITSHM=1',
               '--mount','type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix,readonly',
               '--mount','type=bind,src='+str(secret)+',dst=/run/secrets/xauthority,readonly',
               '--mount','type=bind,src='+str(model)+',dst=/opt/g2-model,readonly',
               '--mount','type=bind,src='+str(out)+',dst=/evidence',IMAGE,
               'python3','/opt/demo/scripts/visual_session.py','--desktop','--width',str(width),'--height',str(height)]
        call(run,90,capture_output=True)
        data={'container':name,'source_root':str(ROOT),'runtime_hash':current['source_hash'],
              'image':IMAGE,'evidence_dir':str(out),'desktop':'Ubuntu existing desktop; open the VM display from Mac',
              'network':'none; no published ports','automatic_motion':False}
        STATE.write_text(json.dumps(data,indent=2))
        end=time.monotonic()+200
        while time.monotonic()<end:
            if (out/'visual-session.json').exists():
                print('READY: Gazebo + RViz2 + G2 Live State on the Ubuntu desktop.');print(json.dumps(data,indent=2));return
            running=call(['docker','inspect','--format','{{.State.Running}}',name],capture_output=True,text=True).stdout.strip()
            if running!='true':break
            time.sleep(.5)
        call(['docker','logs','--tail','80',name]);raise RuntimeError('Visual readiness deadline failed; inspect logs then make ui-down')
    data,info=session()
    if args.action=='info':
        print(json.dumps(data,indent=2));print('Container:',info['State']['Status'])
        for filename in ['visual-session.json','observer.json']:
            file=Path(data['evidence_dir'])/filename
            if file.exists():print(file.read_text())
    elif args.action=='hello':exec_ros(data,['python3','/opt/demo/scripts/sim_hello.py'])
    elif args.action=='telemetry':
        file=Path(data['evidence_dir'])/'observer.json'
        print(file.read_text())
        exec_ros(data,['ros2','topic','echo','/g2/joint_states','--once'],30)
    elif args.action=='check':exec_ros(data,['python3','/opt/demo/scripts/verify_visual.py','--output','/evidence/tf-check.json'],90)
    elif args.action=='record':
        tag='record-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        exec_ros(data,['python3','/opt/demo/scripts/record_visual.py','--output','/evidence/'+tag,'--motion'],310)
    elif args.action=='down':
        call(['docker','stop','--timeout','35',data['container']],50)
        out=Path(data['evidence_dir'])
        logs=call(['docker','logs',data['container']],capture_output=True,text=True)
        (out/'container.log').write_text(logs.stdout+logs.stderr)
        cleanup_file=out/'cleanup.json'
        cleanup=json.loads(cleanup_file.read_text()) if cleanup_file.exists() else None
        call(['docker','rm',data['container']],20)
        secret=out/'xauthority'
        if secret.exists():secret.unlink()
        STATE.unlink()
        if cleanup is None:
            raise RuntimeError('Container removed and cookie cleared, but process cleanup receipt is missing; inspect container.log')
        if cleanup['errors'] or cleanup['remaining_owned_pids']:raise RuntimeError('GUI cleanup failed: '+str(cleanup))
        print('STOPPED: owned GUI/physics processes removed; display cookie copy removed; no ports were exposed.')


if __name__=='__main__':
    main()
