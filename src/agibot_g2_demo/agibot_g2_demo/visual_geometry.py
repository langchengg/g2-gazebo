"""Independent URDF forward kinematics for the optional visual evidence probe."""
import math
import numpy as np


def rotation(axis, angle):
    axis = np.array(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3)*math.cos(angle)+(1-math.cos(angle))*np.outer(axis, axis)+math.sin(angle)*cross


def origin_matrix(joint):
    origin = joint.find('origin')
    xyz = [0., 0., 0.] if origin is None else [float(v) for v in origin.get('xyz', '0 0 0').split()]
    rpy = [0., 0., 0.] if origin is None else [float(v) for v in origin.get('rpy', '0 0 0').split()]
    result = np.eye(4)
    result[:3, :3] = rotation([0, 0, 1], rpy[2]) @ rotation([0, 1, 0], rpy[1]) @ rotation([1, 0, 0], rpy[0])
    result[:3, 3] = xyz
    return result


def fk(chain, positions):
    result = np.eye(4)
    for joint in chain:
        matrix = origin_matrix(joint)
        kind = joint.get('type')
        if kind != 'fixed':
            value = positions[joint.get('name')]
            axis = [float(v) for v in joint.find('axis').get('xyz').split()]
            motion = np.eye(4)
            if kind in ('revolute', 'continuous'):
                motion[:3, :3] = rotation(axis, value)
            elif kind == 'prismatic':
                motion[:3, 3] = np.array(axis)*value
            else:
                raise ValueError('unsupported URDF joint type: '+kind)
            matrix = matrix @ motion
        result = result @ matrix
    return result


def transform_matrix(msg):
    t = msg.transform
    x, y, z, w = t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w
    result = np.eye(4)
    result[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                      [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                      [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    result[:3, 3] = [t.translation.x, t.translation.y, t.translation.z]
    return result


