#!/usr/bin/env python3
"""Convert the pinned HF G2 USD geometry to local OBJ and a Gazebo URDF.

Requires usd-core==26.8 in a conversion-only environment. Runtime needs no USD.
Original assets are never edited. Generated assets retain CC-BY-NC-SA-4.0.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

PREFIX = Path('robot/curobo_robot/assets/robot/G2')
ARM = [f'idx{21+i}_arm_l_joint{i+1}' for i in range(7)]


def numbers(values):
    return ' '.join(f'{float(x):.12g}' for x in values)


def primitive_mesh(prim):
    """Tessellate authored collision primitives; retain their USD transforms."""
    if prim.IsA(UsdGeom.Cube):
        size = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2
        points = [Gf.Vec3d(x*size, y*size, z*size)
                  for x, y, z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                  (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        faces = [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
        return points, faces
    if prim.IsA(UsdGeom.Cylinder):
        cylinder = UsdGeom.Cylinder(prim)
        radius, height = cylinder.GetRadiusAttr().Get(), cylinder.GetHeightAttr().Get()
        axis = str(cylinder.GetAxisAttr().Get())
        points = []
        for z in [-height/2, height/2]:
            for index in range(32):
                x, y = radius*math.cos(index*math.tau/32), radius*math.sin(index*math.tau/32)
                v = (z,x,y) if axis=='X' else (y,z,x) if axis=='Y' else (x,y,z)
                points.append(Gf.Vec3d(*v))
        faces = [list(reversed(range(32))),list(range(32,64))]
        faces += [[i,(i+1)%32,(i+1)%32+32,i+32] for i in range(32)]
        return points, faces
    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)
        points = [Gf.Vec3d(p) for p in mesh.GetPointsAttr().Get()]
        indices = list(mesh.GetFaceVertexIndicesAttr().Get())
        faces, offset = [], 0
        for size in mesh.GetFaceVertexCountsAttr().Get():
            faces.append(indices[offset:offset+size]); offset += size
        if offset != len(indices):
            raise ValueError('Invalid USD polygon indices')
        if mesh.GetOrientationAttr().Get() == 'leftHanded':
            faces = [list(reversed(face)) for face in faces]
        return points, faces
    raise ValueError('Unsupported geometry: ' + str(prim.GetPath()))


def color_for(prim):
    material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    if material:
        for child in Usd.PrimRange(material.GetPrim()):
            if child.IsA(UsdShade.Shader):
                shader = UsdShade.Shader(child)
                for name in ['diffuseColor', 'diffuse_color_constant', 'base_color']:
                    value = shader.GetInput(name).Get()
                    if value is not None:
                        return tuple(max(0., min(1., float(x))) for x in value[:3])
    if prim.IsA(UsdGeom.Gprim):
        values = UsdGeom.Gprim(prim).GetDisplayColorAttr().Get()
        if values:
            return tuple(values[0])
    return (0.65, 0.65, 0.65)


def export_geometry(prim, link, dst, cache):
    points, faces = primitive_mesh(prim)
    transform, resets = cache.ComputeRelativeTransform(prim, link)
    if resets:
        raise ValueError('Unexpected resetXformStack below a link')
    points = [transform.Transform(point) for point in points]
    if not points or not faces or not all(math.isfinite(x) for p in points for x in p):
        raise ValueError('Empty/nonfinite geometry')
    material_colors = {'default': color_for(prim)}
    face_materials = {}
    for subset in prim.GetChildren():
        if subset.IsA(UsdGeom.Subset):
            data = UsdGeom.Subset(subset)
            if data.GetElementTypeAttr().Get() == 'face':
                name = f'm{len(material_colors)}'
                material_colors[name] = color_for(subset)
                for index in data.GetIndicesAttr().Get():
                    face_materials[index] = name
    # DART's custom mesh adapter requires one normal for every imported vertex.
    # USD normals are usually face-varying: split vertices at normal seams,
    # retain authored smooth normals, and use matched OBJ v//vn indices.
    source_normals = None
    normal_interpolation = 'generated-flat'
    reverse_corners = False
    if prim.IsA(UsdGeom.Mesh):
        usd_mesh = UsdGeom.Mesh(prim)
        source_normals = usd_mesh.GetNormalsAttr().Get()
        normal_interpolation = str(usd_mesh.GetNormalsInterpolation())
        reverse_corners = usd_mesh.GetOrientationAttr().Get() == 'leftHanded'
        if source_normals:
            expected = {'faceVarying': sum(len(f) for f in faces),
                        'vertex': len(points), 'varying': len(points),
                        'uniform': len(faces), 'constant': 1}
            if normal_interpolation not in expected or len(source_normals) != expected[normal_interpolation]:
                raise ValueError('Unsupported or malformed authored USD normals')
    normal_transform = transform.GetInverse().GetTranspose()
    normal_cache = {}
    vertices, normals, triangles = [], [], []
    vertex_lookup = {}
    skipped_degenerate = 0
    generated_normal_corners = 0
    offset = 0
    for face_index, face in enumerate(faces):
        corner_ids = list(range(len(face)))
        if reverse_corners:
            corner_ids.reverse()
        for fan in range(1, len(face)-1):
            local_corners = [0, fan, fan+1]
            original_indices = [face[c] for c in local_corners]
            p0, p1, p2 = [points[i] for i in original_indices]
            cross = Gf.Cross(p1-p0, p2-p0)
            length = cross.GetLength()
            if length == 0:
                # Exact zero-area triangles carry no surface or collision volume.
                skipped_degenerate += 1
                continue
            if not math.isfinite(length):
                raise ValueError('Nonfinite triangle area')
            face_normal = cross / length
            ids = []
            for corner, original_index in zip(local_corners, original_indices):
                normal = None
                if source_normals:
                    normal_index = {'faceVarying': offset + corner_ids[corner],
                                    'vertex': original_index, 'varying': original_index,
                                    'uniform': face_index, 'constant': 0}[normal_interpolation]
                    raw = tuple(float(v) for v in source_normals[normal_index])
                    if raw not in normal_cache:
                        n = normal_transform.TransformDir(Gf.Vec3d(*raw))
                        norm = n.GetLength()
                        normal_cache[raw] = n / norm if norm > 0 and math.isfinite(norm) else None
                    normal = normal_cache[raw]
                if normal is None:
                    normal = face_normal
                    generated_normal_corners += 1
                if not all(math.isfinite(v) for v in normal):
                    raise ValueError('Nonfinite mesh normal')
                # Keep normal seams and authored smooth normals exactly; points
                # shared across materials remain valid as each face has v//vn.
                key = (original_index, tuple(normal))
                if key not in vertex_lookup:
                    vertex_lookup[key] = len(vertices) + 1
                    vertices.append(points[original_index]); normals.append(normal)
                ids.append(vertex_lookup[key])
            triangles.append((face_index, ids))
        offset += len(face)
    if not triangles or len(vertices) != len(normals):
        raise ValueError('Empty geometry or incomplete normals')
    with dst.open('w') as stream:
        stream.write('# CC-BY-NC-SA-4.0; derived from AgiBot World GenieSimAssets.\n')
        stream.write('mtllib ' + dst.with_suffix('.mtl').name + '\n')
        for point in vertices:
            stream.write('v ' + ' '.join(format(float(v), '.17g') for v in point) + '\n')
        for normal in normals:
            stream.write('vn ' + ' '.join(format(float(v), '.17g') for v in normal) + '\n')
        current = None
        for face_index, ids in triangles:
            material = face_materials.get(face_index, 'default')
            if material != current:
                stream.write('usemtl ' + material + '\n'); current = material
            stream.write('f ' + ' '.join(f'{v}//{v}' for v in ids) + '\n')
    with dst.with_suffix('.mtl').open('w') as stream:
        for name, color in material_colors.items():
            stream.write('newmtl '+name+'\nKd '+numbers(color)+'\nKa 0.2 0.2 0.2\nKs 0 0 0\nd 1\n')
    return {'usd_prim': str(prim.GetPath()), 'file': 'meshes/'+dst.name,
            'vertices': len(vertices), 'normals': len(normals), 'faces': len(triangles),
            'source_vertices': len(points), 'source_faces': len(faces),
            'normal_interpolation': normal_interpolation,
            'generated_normal_corners': generated_normal_corners,
            'skipped_exact_zero_area_triangles': skipped_degenerate,
            'bounds': [[min(p[a] for p in points) for a in range(3)],
                       [max(p[a] for p in points) for a in range(3)]],
            'transform_to_link': [[float(transform[i][j]) for j in range(4)] for i in range(4)],
            'materials': material_colors,
            'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()}


def validate_inertia(link):
    inertial = link.find('inertial')
    if inertial is None:
        return
    mass = float(inertial.find('mass').get('value'))
    v = {k: float(x) for k,x in inertial.find('inertia').attrib.items()}
    a,b,c,d,e,f = (v[k] for k in ['ixx','iyy','izz','ixy','ixz','iyz'])
    determinant = a*b*c + 2*d*e*f - a*f*f - b*e*e - c*d*d
    if not all(math.isfinite(x) for x in [mass,*v.values()]) or mass <= 0 or a <= 0 or a*b-d*d <= 0 or determinant <= 0:
        raise ValueError('Nonphysical inertia at '+link.get('name'))
    if a+b<c or a+c<b or b+c<a:
        raise ValueError('Inertia diagonal triangle inequality at '+link.get('name'))


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=root/'.artifacts/gazebo-model')
    parser.add_argument('--output', type=Path, default=root/'.artifacts/gazebo-model/generated')
    parser.add_argument('--asset-root', default='/opt/g2-model')
    parser.add_argument('--controllers', default='/opt/demo/install/agibot_g2_description/share/agibot_g2_description/config/controllers.yaml')
    parser.add_argument('--plugin-filename', required=True)
    parser.add_argument('--plugin-name', required=True)
    parser.add_argument('--hardware-plugin', required=True)
    args = parser.parse_args()
    lock = json.loads((root/'model_sources/g2.lock.json').read_text())
    for item in lock['files']:
        path = args.cache/'raw'/item['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Missing or changed original: '+item['path'])
    source = args.cache/'raw'/PREFIX
    stage = Usd.Stage.Open(str(source/'robot.usda'))
    if UsdGeom.GetStageMetersPerUnit(stage)!=1 or str(UsdGeom.GetStageUpAxis(stage))!='Z':
        raise ValueError('Unexpected model coordinate convention')
    locked_paths = {item['path'] for item in lock['files']}
    # Fail on a missing layer or external file asset; MDL shader implementation
    # identifiers are omitted because only constant diffuse colors are exported.
    dependencies = []
    for prim in stage.Traverse():
        for attr in prim.GetAttributes():
            if attr.GetTypeName() in (Sdf.ValueTypeNames.Asset, Sdf.ValueTypeNames.AssetArray):
                value = attr.Get()
                values = value if attr.GetTypeName() == Sdf.ValueTypeNames.AssetArray else [value]
                for asset in values or []:
                    if asset and asset.path and asset.path != 'OmniPBR.mdl':
                        raise ValueError('Unreviewed texture or shader asset: ' + asset.path)
    for layer in stage.GetUsedLayers():
        if not layer.anonymous:
            resolved = Path(layer.realPath).resolve()
            if not resolved.is_relative_to((args.cache/'raw').resolve()):
                raise ValueError('External USD layer')
            relative = str(resolved.relative_to((args.cache/'raw').resolve()))
            if relative not in locked_paths:
                raise ValueError('Composed USD layer is missing from source lock: ' + relative)
            dependencies.append(relative)
    missing = stage.GetCompositionErrors()
    if missing:
        raise ValueError('USD composition errors: '+str(missing))
    output = args.output
    if output.exists() and any(output.iterdir()):
        raise ValueError('Conversion requires an empty output directory')
    (output/'meshes').mkdir(parents=True,exist_ok=True)
    robot = ET.parse(source/'G2_omnipicker_fixed_dual.urdf').getroot()
    robot.set('name','g2_gazebo_simulation')
    report = {'revision':lock['revision'],'usd_version':'.'.join(map(str,Usd.GetVersion())),
              'layers':sorted(dependencies),'meshes':[], 'frozen_joints':[],
              'coordinate_system':{'meters_per_unit':1,'up_axis':'Z'},
              'geometry_source':'composed HF robot.usda; link-local transforms baked'}
    cache = UsdGeom.XformCache()
    for link in robot.findall('link'):
        name = link.get('name'); validate_inertia(link)
        for old in list(link):
            if old.tag in ['visual','collision']:
                link.remove(old)
        prim = stage.GetPrimAtPath('/genie/'+name)
        if not prim:
            # Camera geometry is already authored under the gripper base prim.
            if name not in ['gripper_l_camera_link','gripper_r_camera_link']:
                raise ValueError('URDF link absent from USD: '+name)
            continue
        count = 0
        for geometry in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
            if not any(geometry.IsA(kind) for kind in [UsdGeom.Mesh,UsdGeom.Cube,UsdGeom.Cylinder]):
                continue
            path = str(geometry.GetPath())
            collision = '/collisions/' in path
            if not collision and ('/visuals/' not in path and '/Cam/' not in path):
                continue
            suffix = 'collision' if collision else 'visual'
            dst = output/'meshes'/f'{name}_{suffix}_{count}.obj';count+=1
            entry = export_geometry(geometry,prim,dst,cache)
            report['meshes'].append(dict(entry,link=name,kind=suffix))
            element = ET.SubElement(link,suffix,{'name':dst.stem})
            shape = ET.SubElement(element,'geometry')
            # RViz resource_retriever/libcurl requires an explicit file URI;
            # Gazebo and RViz still consume this same generated URDF.
            ET.SubElement(shape,'mesh',{'filename':(Path(args.asset_root)/'meshes'/dst.name).as_uri()})
        if name in [f'arm_l_link{i}' for i in range(1,8)] and not link.findall('collision'):
            raise ValueError('Controlled link without collision')
    # The same HF URDF and USD differ in fixed tool attachments and helper centers. Use
    # the composed USD attachment transforms to avoid a 13.1 mm visual gap.
    # Controlled joint origins are never modified.
    report['fixed_attachment_repairs'] = []
    for name in ['arm_l_end_joint', 'arm_r_end_joint', 'idx51_ee_l_joint', 'idx91_ee_r_joint', 'idx52_gripper_l_center_joint', 'idx92_gripper_r_center_joint']:
        joint = robot.find("joint[@name='%s']" % name)
        child = stage.GetPrimAtPath('/genie/' + joint.find('child').get('link'))
        parent = stage.GetPrimAtPath('/genie/' + joint.find('parent').get('link'))
        transform = cache.GetLocalToWorldTransform(child) * cache.GetLocalToWorldTransform(parent).GetInverse()
        pitch = math.atan2(-transform[0][2], math.hypot(transform[0][0], transform[0][1]))
        roll = math.atan2(transform[1][2], transform[2][2])
        yaw = math.atan2(transform[0][1], transform[0][0])
        replacement = {'xyz': numbers(transform.ExtractTranslation()), 'rpy': numbers([roll, pitch, yaw])}
        origin = joint.find('origin')
        report['fixed_attachment_repairs'].append({'joint': name, 'source': str(child.GetPath()),
            'before': dict(origin.attrib), 'after': replacement,
            'relative_matrix': [[float(transform[i][j]) for j in range(4)] for i in range(4)]})
        origin.attrib.clear(); origin.attrib.update(replacement)
    # Keep only the selected 7-DOF arm mobile. Zero-angle freezing preserves the
    # original origin transforms exactly; no source geometry or inertia is edited.
    inventory=[]
    for joint in robot.findall('joint'):
        name=joint.get('name')
        item={'name':name,'original_type':joint.get('type'),'controlled':name in ARM}
        for tag in ['origin','axis','limit','parent','child']:
            node=joint.find(tag)
            if node is not None:item[tag]=dict(node.attrib)
        if name not in ARM and joint.get('type')!='fixed':
            report['frozen_joints'].append({'name':name,'position_rad':0.,'origin_preserved':True})
            joint.set('type','fixed')
            for node in list(joint):
                if node.tag in ['axis','limit','mimic','dynamics','safety_controller']:
                    joint.remove(node)
        if name in ARM:
            limit=joint.find('limit');lo=float(limit.get('lower'));hi=float(limit.get('upper'))
            if not lo<=0<=hi:raise ValueError('Initial controlled position outside limits')
            ET.SubElement(joint,'dynamics',{'damping':'0.1','friction':'0.0'})
        inventory.append(item)
    ET.SubElement(robot,'link',{'name':'world'})
    joint=ET.SubElement(robot,'joint',{'name':'world_to_base','type':'fixed'})
    ET.SubElement(joint,'parent',{'link':'world'});ET.SubElement(joint,'child',{'link':'base_link'})
    ET.SubElement(joint,'origin',{'xyz':'0 0 0.04','rpy':'0 0 0'})
    control=ET.SubElement(robot,'ros2_control',{'name':'G2GazeboSystem','type':'system'})
    hardware=ET.SubElement(control,'hardware');ET.SubElement(hardware,'plugin').text=args.hardware_plugin
    for name in ARM:
        j=ET.SubElement(control,'joint',{'name':name})
        ET.SubElement(j,'command_interface',{'name':'position'})
        for interface in ['position','velocity','effort']:
            state=ET.SubElement(j,'state_interface',{'name':interface})
            if interface=='position':ET.SubElement(state,'param',{'name':'initial_value'}).text='0.0'
    gazebo=ET.SubElement(robot,'gazebo')
    plugin=ET.SubElement(gazebo,'plugin',{'filename':args.plugin_filename,'name':args.plugin_name})
    ET.SubElement(plugin,'parameters').text=args.controllers
    ET.SubElement(plugin,'robot_param').text='robot_description'
    # This plugin revision prepends the ROS namespace itself.
    ET.SubElement(plugin,'robot_param_node').text='robot_state_publisher'
    ros=ET.SubElement(plugin,'ros');ET.SubElement(ros,'namespace').text='/g2/sim'
    ET.indent(robot);ET.ElementTree(robot).write(output/'g2.urdf',encoding='utf-8',xml_declaration=True)
    controlled = [{'name': item['name'], **{key: float(value) for key, value in item['limit'].items()}, 'initial_position': 0.0} for item in inventory if item['controlled']]
    (output/'joint_inventory.json').write_text(json.dumps({'controlled_joints': controlled, 'target_joint': 'idx22_arm_l_joint2', 'joints': inventory},indent=2)+'\n')
    report['controlled_joints']=ARM;report['initial_positions']=[0.]*7
    report['target_joint']='idx22_arm_l_joint2'
    report['pose_status']='Source zero articulation pose, base raised 0.04m; Gazebo visual/collision validation required'
    (output/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    for file in ['LICENSE','README.md']:
        shutil.copyfile(args.cache/'raw'/file,output/('SOURCE_'+file))
    hashes={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.rglob('*')) if p.is_file() and p.name!='generated_manifest.json'}
    (output/'generated_manifest.json').write_text(json.dumps({
        'files': hashes, 'revision': lock['revision'],
        'converter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_lock_sha256': hashlib.sha256((root/'model_sources/g2.lock.json').read_bytes()).hexdigest(),
        'runtime_arguments': {'asset_root': args.asset_root, 'controllers': args.controllers,
                              'plugin_filename': args.plugin_filename, 'plugin_name': args.plugin_name,
                              'hardware_plugin': args.hardware_plugin}}, indent=2)+'\n')
    print(json.dumps({'meshes':len(report['meshes']),'joints':ARM,'output':str(output)},indent=2))


if __name__=='__main__':
    main()
