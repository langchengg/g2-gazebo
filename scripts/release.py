#!/usr/bin/env python3
"""Allowlisted source packaging and bounded fresh-directory release verification."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
from source_manifest import manifest

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def isolated_environment(parent):
    """Use public system tools and the local daemon without inherited credentials."""
    env = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
           'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
           'DOCKER_HOST': 'unix:///var/run/docker.sock', 'DOCKER_CONTEXT': 'default',
           'PIP_CONFIG_FILE': os.devnull, 'PYTHONNOUSERSITE': '1'}
    for key, name in {'HOME': 'home', 'XDG_CACHE_HOME': 'xdg-cache',
                      'XDG_CONFIG_HOME': 'xdg-config', 'XDG_DATA_HOME': 'xdg-data',
                      'XDG_STATE_HOME': 'xdg-state', 'HF_HOME': 'hf-cache',
                      'PIP_CACHE_DIR': 'pip-cache', 'DOCKER_CONFIG': 'docker-config',
                      'TMPDIR': 'tmp'}.items():
        directory = parent / name
        directory.mkdir(mode=0o700)
        env[key] = str(directory)
    return env


def run_recorded(command, timeout, root, env, evidence, report, receipt):
    """Record normal failures, spawn errors and bounded timeout cleanup alike."""
    records = report['commands']
    log = evidence / (str(len(records)).zfill(2) + '.log')
    started = time.monotonic()
    code, error, process = 1, None, None
    try:
        with log.open('w') as stream:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout)
            except BaseException as exc:
                code = (124 if isinstance(exc, subprocess.TimeoutExpired) else
                        int(exc.code) if isinstance(exc, SystemExit) and isinstance(exc.code, int) else 130)
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass  # The child exited between poll and signal.
                    try:
                        process.wait(50)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(5)
                raise
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        records.append({'command': command, 'cwd': str(root), 'exit_code': code,
                        'process_exit_code': process.returncode if process else None,
                        'error': error, 'wall_seconds': time.monotonic() - started,
                        'log': str(log)})
        receipt.write_text(json.dumps(report, indent=2))
    if code:
        raise RuntimeError('Failed: ' + str(command) + '; see ' + str(log))


def collect_simulation_evidence(root, report):
    entries = []
    for path in sorted((root / '.artifacts/gazebo').glob('*/environment.json')):
        data = json.loads(path.read_text())
        item = {'path': str(path), 'sha256': digest(path),
                'image': data.get('image'),
                'source_hash': data.get('source', {}).get('source_hash'),
                'image_source_matches': data.get('image_source_matches', False)}
        entries.append(item)
    report['simulation_evidence'] = entries
    report['image_ids'] = sorted({item['image'].split()[0] for item in entries if item['image']})
    report['nested_evidence_root'] = str(root / '.artifacts')


def package(output):
    data=manifest(ROOT,'delivery')
    required = {'README.md', 'README.zh-CN.md', 'Makefile', 'Dockerfile.sim',
                'Dockerfile.model-tools', 'compose.sim.yaml', 'model_sources/g2.lock.json',
                'scripts/release.py', 'scripts/source_manifest.py', 'scripts/doctor.py',
                'scripts/fetch_g2_model.py', 'scripts/prepare_model.py', 'scripts/convert_g2_model.py',
                'scripts/ui_manage.py', 'scripts/visual_session.py',
                'src/agibot_g2_demo/setup.py', 'src/agibot_g2_demo/setup.cfg',
                'src/agibot_g2_demo/package.xml', 'src/agibot_g2_demo/launch/sim.launch.py',
                'src/agibot_g2_demo/config/g2_demo.rviz',
                'src/agibot_g2_description/config/controllers.yaml',
                'src/agibot_g2_description/worlds/g2_demo.sdf',
                'docs/quickstart.commands.sh', 'docs/reproduction_gap_audit.md'}
    missing = sorted(required - set(data['files']))
    if missing:
        raise ValueError('Required release files missing: ' + ', '.join(missing))
    output.mkdir(parents=True,exist_ok=True)
    archive=output/('g2-gazebo-source-'+data['source_hash'][:12]+'.tar.gz')
    with archive.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as compressed:
            with tarfile.open(fileobj=compressed,mode='w') as stream:
                for name in data['files']:
                    path=ROOT/name;info=stream.gettarinfo(str(path),arcname='g2-gazebo/'+name)
                    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                    with path.open('rb') as f:stream.addfile(info,f)
    checksum=digest(archive)
    archive.with_suffix(archive.suffix+'.sha256').write_text(checksum+'  '+archive.name+'\n')
    archive.with_suffix(archive.suffix+'.manifest.json').write_text(json.dumps(data,indent=2))
    for name in ['README.md','README.zh-CN.md']:
        dest=output/(archive.stem+'-'+name)
        with dest.open('xb') as f:f.write((ROOT/name).read_bytes())
    print(json.dumps({'archive':str(archive),'sha256':checksum,'files':len(data['files']),
                      'source_hash':data['source_hash']},indent=2))
    return archive


def extract(archive,parent):
    expected=archive.with_suffix(archive.suffix+'.sha256').read_text().split()[0]
    if digest(archive)!=expected:raise ValueError('Archive checksum mismatch')
    source_manifest=json.loads(archive.with_suffix(archive.suffix+'.manifest.json').read_text())
    directory=Path(tempfile.mkdtemp(prefix='g2 release ',dir=parent))
    with tarfile.open(archive) as stream:
        seen=set()
        for item in stream.getmembers():
            p=PurePosixPath(item.name)
            if not item.isfile() or p.is_absolute() or '..' in p.parts or p.parts[0]!='g2-gazebo':
                raise ValueError('Unsafe archive entry: '+item.name)
            relative=str(PurePosixPath(*p.parts[1:]))
            if relative in seen or relative not in source_manifest['files']:raise ValueError('Unexpected/duplicate entry')
            content=stream.extractfile(item).read()
            if hashlib.sha256(content).hexdigest()!=source_manifest['files'][relative]:raise ValueError('Source checksum mismatch')
            destination=directory/item.name;destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(content);destination.chmod(item.mode&0o777);seen.add(relative)
    if seen!=set(source_manifest['files']):raise ValueError('Incomplete archive')
    target=directory/'g2-gazebo'
    if manifest(target,'delivery')!=source_manifest:raise ValueError('Extracted manifest differs')
    return target,source_manifest


def verify(args):
    if not args.accept_noncommercial_license:raise ValueError('Review the model license, then explicitly accept noncommercial use for this experiment')
    parent=args.parent.resolve();parent.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(parent).free < 4*1024**3:raise RuntimeError('At least4GiB free required; no old resources will be pruned')
    root,source=extract(args.archive.resolve(),parent)
    evidence=root.parent/'acceptance';evidence.mkdir();cache=root/'.artifacts/gazebo-model'
    assert not cache.exists() and not (root/'.git').exists()
    env=isolated_environment(root.parent)
    records=[];report={'archive':str(args.archive.resolve()),'archive_sha256':digest(args.archive),
      'source_hash':source['source_hash'],'extracted_root':str(root),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'cache_boundary':'new HOME/raw/generated/XDG/HF/pip/Docker client configuration; local Unix Docker daemon public base/toolchain caches allowed; no old HOME, model or project mounted; system-installed CLI plugins used',
      'environment':env,'model_lock_sha256':digest(root/'model_sources/g2.lock.json'),
      'commands':records,'result':'RUNNING','gui':'PENDING separate visible-desktop acceptance'}
    receipt=evidence/'receipt.json'
    def run(command,timeout):
        run_recorded(command,timeout,root,env,evidence,report,receipt)
    try:
        run(['make','doctor'],180)
        run(['make','fetch-model','ACCEPT_MODEL_LICENSE=yes'],1800)
        run(['make','prepare-model'],10800)
        run(['python3','scripts/prepare_model.py','--output',str(cache/'generated-second')],1800)
        first=json.loads((cache/'generated/generated_manifest.json').read_text())
        second=json.loads((cache/'generated-second/generated_manifest.json').read_text())
        if first!=second:raise ValueError('Two empty-output conversions differ')
        report['model_generation']={'result':'PASS','two_output_manifests_identical':True,
             'manifest_sha256':digest(cache/'generated/generated_manifest.json'),'files':len(first['files'])}
        # Exercise the documented entry before the independent no-cache rebuild;
        # do not retag the tested image afterwards with another cached build.
        run(['make','build-sim'],7200)
        run(['make','rebuild-sim'],7200)
        run(['make','test-sim'],1100)
        run(['make','verify-sim'],700)
        report['result']='SOFTWARE_PASS_GUI_PENDING'
    except BaseException as error:
        report['result']='FAIL';report['error']=str(error);raise
    finally:
        collect_simulation_evidence(root,report)
        report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt.write_text(json.dumps(report,indent=2))
        print(json.dumps({'root':str(root),'receipt':str(receipt),'result':report['result']},indent=2),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    pack=sub.add_parser('package');pack.add_argument('--output',type=Path,default=ROOT/'.artifacts/releases')
    v=sub.add_parser('verify');v.add_argument('--archive',type=Path,required=True)
    v.add_argument('--parent',type=Path,default=Path(tempfile.gettempdir())/'g2-reproduction')
    v.add_argument('--accept-noncommercial-license',action='store_true')
    a=p.parse_args();package(a.output) if a.action=='package' else verify(a)

if __name__=='__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    main()
