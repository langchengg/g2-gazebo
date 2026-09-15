#!/usr/bin/env python3
"""Orchestrate and validate the isolated G2 model conversion pipeline.

OpenUSD stays in a dedicated model-tools image instead of the ROS Humble runtime.
The host validates locked inputs and generated resources; conversion itself runs
without network access against read-only source mounts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.artifacts/gazebo-model'
ARM = [f'idx{21+i}_arm_l_joint{i+1}' for i in range(7)]
RUNTIME_ARGUMENTS = {
    'asset_root': '/opt/g2-model',
    'controllers': '/opt/demo/install/agibot_g2_description/share/agibot_g2_description/config/controllers.yaml',
    'plugin_filename': 'gz_ros2_control-system',
    'plugin_name': 'gz_ros2_control::GazeboSimROS2ControlPlugin',
    'hardware_plugin': 'gz_ros2_control/GazeboSimSystem',
}


def run(args, timeout=600):
    subprocess.run(args, check=True, timeout=timeout)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_usd_version(python):
    """Retained for direct diagnostic use; normal preparation uses Docker."""
    version = json.loads(subprocess.check_output(
        [python, '-c', 'from pxr import Usd; import json; print(json.dumps(Usd.GetVersion()))'],
        text=True, timeout=30))
    if version != [0, 26, 8]:
        raise RuntimeError(f'OpenUSD 26.8 is required; selected interpreter reports {version!r}')


def validate_model_resources(generated):
    """Independently check URDF, joint inventory, and local mesh containment."""
    robot = ET.parse(generated / 'g2.urdf').getroot()
    links = [link.get('name') for link in robot.findall('link')]
    if not links or None in links or len(set(links)) != len(links):
        raise ValueError('Invalid or duplicate URDF link names')
    parents, joint_names, mobile = {}, set(), set()
    for joint in robot.findall('joint'):
        name = joint.get('name')
        if not name or name in joint_names:
            raise ValueError('Invalid or duplicate URDF joint names')
        joint_names.add(name)
        parent, child = joint.find('parent'), joint.find('child')
        if parent is None or child is None:
            raise ValueError('URDF joint missing parent/child')
        parent, child = parent.get('link'), child.get('link')
        if parent not in links or child not in links or child in parents:
            raise ValueError('URDF joint tree has missing links or multiple parents')
        parents[child] = parent
        if joint.get('type') != 'fixed':
            mobile.add(name)
            if name not in ARM or joint.get('type') != 'revolute':
                raise ValueError('Unexpected mobile URDF joint; non-task joints must be fixed')
    if mobile != set(ARM):
        raise ValueError('URDF must contain exactly the seven controlled G2 left-arm joints')
    if set(links) - set(parents) != {'world'} or parents.get('base_link') != 'world':
        raise ValueError('URDF must have world as sole root and world-to-base connection')
    for link in links:
        seen = set()
        while link != 'world':
            if link in seen or link not in parents:
                raise ValueError('URDF joint tree is cyclic or disconnected')
            seen.add(link)
            link = parents[link]

    def local_file(relative):
        path = generated / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.resolve().is_relative_to(generated.resolve()) or not path.is_file()):
            raise ValueError('Unresolved or escaping model resource: ' + str(relative))
        return path

    meshes = robot.findall('.//mesh')
    if not meshes:
        raise ValueError('URDF contains no model meshes')
    for mesh in meshes:
        uri = mesh.get('filename', '')
        prefix = Path(RUNTIME_ARGUMENTS['asset_root']).as_uri() + '/'
        if not uri.startswith(prefix):
            raise ValueError('Unexpected model mesh URI: ' + uri)
        path = local_file(Path(unquote(uri[len(prefix):])))
        if path.suffix != '.obj':
            raise ValueError('Expected converted OBJ mesh')
    if robot.findall('.//texture'):
        raise ValueError('Unexpected URDF texture; conversion uses constant diffuse materials')
    for obj in generated.rglob('*.obj'):
        libraries, used = [], set()
        with obj.open(encoding='utf-8') as stream:
            for line in stream:
                tokens = line.split()
                if tokens and tokens[0] == 'mtllib':
                    if len(tokens) != 2:
                        raise ValueError('Invalid OBJ material library reference')
                    libraries.append(local_file(obj.relative_to(generated).parent / tokens[1]))
                elif tokens and tokens[0] == 'usemtl':
                    used.add(' '.join(tokens[1:]))
        defined = set()
        for library in libraries:
            for line in library.read_text(encoding='utf-8').splitlines():
                tokens = line.split()
                if tokens and tokens[0] == 'newmtl':
                    defined.add(' '.join(tokens[1:]))
                elif tokens and (tokens[0].startswith('map_') or tokens[0] in ('bump', 'disp', 'decal', 'refl')):
                    raise ValueError('Unexpected MTL texture dependency; expected constant diffuse materials')
        if not libraries or not used or not used <= defined:
            raise ValueError('OBJ material references are not closed: ' + obj.name)


def validate_generated(generated, root=ROOT):
    """Accept generated cache only when identity, file set, and hashes all match."""
    data = json.loads((generated / 'generated_manifest.json').read_text())
    lock = json.loads((root / 'model_sources/g2.lock.json').read_text())
    for field, expected in {
        'converter_sha256': digest(root / 'scripts/convert_g2_model.py'),
        'source_lock_sha256': digest(root / 'model_sources/g2.lock.json'),
        'revision': lock['revision'], 'runtime_arguments': RUNTIME_ARGUMENTS,
    }.items():
        if data.get(field) != expected:
            raise ValueError('Generated model mismatch: ' + field + '; use a new output directory')
    actual = {str(p.relative_to(generated)) for p in generated.rglob('*') if p.is_file()}
    if actual != set(data['files']) | {'generated_manifest.json'}:
        raise ValueError('Generated model file set differs from its manifest')
    for relative, expected in data['files'].items():
        path = generated / relative
        if path.is_symlink() or not path.resolve().is_relative_to(generated.resolve()) or digest(path) != expected:
            raise ValueError('Invalid generated model: ' + relative)
    inventory = json.loads((generated / 'joint_inventory.json').read_text())
    names = [item.get('name') for item in inventory['controlled_joints'] if isinstance(item, dict)]
    if len(names) != 7 or set(names) != set(ARM):
        raise ValueError('Expected exactly the seven controlled G2 left-arm joint names')
    validate_model_resources(generated)
    print('Verified generated model cache:', generated)
    return data


def build_tools(image, root=ROOT):
    """Build or reuse the converter image identified by Dockerfile content.

    The cache check promises only the source label verified below; it does not
    independently attest architecture or the wider native toolchain identity.
    """
    dockerfile = root / 'Dockerfile.model-tools'
    label = 'org.agibot-g2.model-tools-source'
    expected = digest(dockerfile)
    result = subprocess.run(['docker', 'image', 'inspect', image, '--format',
                             '{{index .Config.Labels "' + label + '"}}'],
                            text=True, capture_output=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip() == expected:
        print('Reusing verified model-tools build:', image)
        return
    run(['docker', 'build', '--label', label + '=' + expected, '--build-arg',
         'BUILD_JOBS=2', '-f', str(dockerfile), '-t', image, str(root)], timeout=10800)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--image', default='agibot-g2-model-tools:26.8')
    parser.add_argument('--accept-noncommercial-license', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    cache = args.cache.resolve()
    generated = (args.output or cache / 'generated').resolve()
    if args.build_only:
        build_tools(args.image)
        return
    if (generated / 'generated_manifest.json').exists() or args.check_only:
        validate_generated(generated)
        return
    if generated.exists() and any(generated.iterdir()):
        raise ValueError('Output must be empty. Preserve existing data and select --output NEW_DIRECTORY')
    fetch = [sys.executable, str(ROOT / 'scripts/fetch_g2_model.py'), '--cache', str(cache)]
    if args.accept_noncommercial_license:
        fetch.append('--accept-noncommercial-license')
    run(fetch, timeout=1800)
    build_tools(args.image)
    generated.mkdir(parents=True, exist_ok=True)
    # Fetch and image build may use the network, but conversion cannot. Read-only
    # source mounts plus an empty writable output exclude hidden generated inputs.
    command = ['docker', 'run', '--rm', '--network', 'none', '--memory', '3g', '--cpus', '2',
               '--user', f'{os.getuid()}:{os.getgid()}', '--read-only', '--tmpfs', '/tmp:rw,size=128m',
               '--mount', f'type=bind,src={ROOT},dst=/workspace,readonly',
               '--mount', f'type=bind,src={cache / "raw"},dst=/model-cache/raw,readonly',
               '--mount', f'type=bind,src={generated},dst=/output',
               args.image, '/workspace/scripts/convert_g2_model.py',
               '--cache', '/model-cache', '--output', '/output']
    for name, value in RUNTIME_ARGUMENTS.items():
        command += ['--' + name.replace('_', '-'), value]
    run(command, timeout=1800)
    validate_generated(generated)


if __name__ == '__main__':
    main()
