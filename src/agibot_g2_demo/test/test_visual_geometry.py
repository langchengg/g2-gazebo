"""Independent forward-kinematic evidence math; these do not prove rendering."""
from types import SimpleNamespace as Item
import xml.etree.ElementTree as ET
import math
import numpy as np
import pytest
from agibot_g2_demo.visual_geometry import fk, origin_matrix, transform_matrix

pytestmark = pytest.mark.unit


def test_fixed_nonzero_pose_is_preserved_before_revolute_rotation():
    joint = ET.fromstring('<joint name="test" type="revolute"><origin xyz="1 2 3" rpy="0 0 1.5707963267948966"/><axis xyz="0 1 0"/></joint>')
    matrix = fk([joint], {'test': math.pi/2})
    assert matrix[:3, 3] == pytest.approx([1, 2, 3])
    assert matrix[:3, :3] @ [1, 0, 0] == pytest.approx([0, 0, -1])
    assert np.linalg.det(matrix[:3, :3]) == pytest.approx(1.)


def test_chain_composition_and_prismatic_in_rotated_frame():
    fixed = ET.fromstring('<joint name="base" type="fixed"><origin xyz="0 0 1" rpy="0 0 1.5707963267948966"/></joint>')
    slide = ET.fromstring('<joint name="slide" type="prismatic"><axis xyz="1 0 0"/></joint>')
    assert fk([fixed, slide], {'slide': .3})[:3, 3] == pytest.approx([0, .3, 1])


def test_ros_quaternion_and_urdf_rpy_agree():
    value = Item(transform=Item(translation=Item(x=1., y=2., z=3.),
        rotation=Item(x=0., y=0., z=math.sin(.25), w=math.cos(.25))))
    joint = ET.fromstring('<joint name="base" type="fixed"><origin xyz="1 2 3" rpy="0 0 0.5"/></joint>')
    assert transform_matrix(value) == pytest.approx(origin_matrix(joint))
