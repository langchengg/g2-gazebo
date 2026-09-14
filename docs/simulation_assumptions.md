# G2 Gazebo simulation assumptions

## Model and physics

The selected model is the official HF G2 Omnipicker dual-arm description. Its
58 URDF links and 57 original joints describe the body, head, steerable wheels,
two seven-joint arms and grippers. The generated wrapper fixes `base_link` to
`world` with a fixed joint at z=0.04 m, matching the source USD's base elevation.
It does not mark the articulated robot static. The world retains gravity
(0, 0, -9.81), a physical ground plane, lighting and Gazebo's physics system.

Only the left arm's seven joints remain revolute:
`idx21_arm_l_joint1`, `idx22_arm_l_joint2`, `idx23_arm_l_joint3`,
`idx24_arm_l_joint4`, `idx25_arm_l_joint5`, `idx26_arm_l_joint6`,
`idx27_arm_l_joint7`. Other originally movable joints are frozen at zero by the
wrapper with their original origin transforms unchanged. Six already-fixed tool attachment/helper origins are separately repaired from the same-source USD, as described below. This specifically
preserves the geometric transform for a zero-angle freeze. Nonzero frozen poses
would require composing the axis rotation into the origin; this converter does
not pretend that changing the joint type preserves a nonzero pose.

All seven controlled initial positions are zero, taken from the source USD's
authored arm state rather than generated from an assumed safe robot position.
The accepted demonstration target is the second left arm joint, +0.05 rad,
then return over six simulation seconds. Actual Gazebo feedback and GUI frames
confirmed this path without obvious severe penetration, falling or unrelated body
movement. This limited visual check is not an exhaustive collision analysis or a
real-robot safety assertion. Full controlled vectors hold the six non-target joints at
measured baseline positions.

Original positive masses and inertia tensors are retained. The converter checks
finite values, positive mass, positive-definite inertia tensors and diagonal
triangle inequalities. Fixed helper frames without inertia remain fixed frames
and can be lumped into their physical parent by the URDF/SDF conversion; no
arbitrary placeholder masses are introduced. Gripper camera visual geometry is
already in the USD gripper base subtree; the original camera frames/masses are
retained without adding a duplicate visual.

Collision geometry comes from the same USD's authored convex meshes, body box /
cylinder approximations and wheel cylinders. Those approximations are preserved
and recorded; all arm collision geometry remains present. The project does not
claim the original approximations are a measured collision model. Whole-robot
self-collision and contact behavior require explicit Gazebo verification; merely
having collision tags is not evidence that contacts were checked.

## Control and rendering

Position command interfaces drive Gazebo joints through gz_ros2_control and the
standard joint trajectory controller. Position, velocity and effort state
interfaces expose the plugin's simulation state; these are simulation quantities,
not G2 hardware measurements. A small 0.1 joint damping term and zero friction
are declared simulation settings, not motor identification results. The joint
state broadcaster is the authoritative application feedback source.

The world camera starts at (2.3, 2.3, 1.65) m with roll/pitch/yaw
(0, 0.22, -2.35) rad aimed toward the robot, and uses the
Fortress Ogre 1 renderer. The recorded GUI uses Xvfb and Mesa llvmpipe software
OpenGL; inspected frames show the complete G2 and its moving arm. Material
colors are retained, but complex vendor MDL shading is reduced to diffuse MTL;
no photorealism or sensor calibration is claimed.

## Out of scope

Real GDK installation, hardware SDK compatibility, firmware, hardware control,
mobile navigation, grasp planning, closed-chain gripper actuation, whole-body
balance and calibrated actuator dynamics are outside this simulation task.
Their absence does not prevent a completed Gazebo software acceptance.

## Same-source fixed attachment corrections

The HF URDF and USD disagree on fixed tool attachments and helper-center frames. The original
end-link origin is 0.095 m along the final arm link; the composed USD uses about
0.088 m. The original gripper mount adds another 0.0061 m, whereas the USD mount
is coincident. Together they otherwise produce a 13.1 mm tool-placement gap.
The converter repairs `arm_l_end_joint`, `arm_r_end_joint`, `idx51_ee_l_joint` and
`idx91_ee_r_joint`, `idx52_gripper_l_center_joint`, and
`idx92_gripper_r_center_joint` from the composed USD child-to-parent transforms, including
rotation. Controlled-joint origins are untouched. `conversion.json` stores exact
original/replacement values and source matrix evidence. The repair reproduces
the selected complete USD model appearance rather than guessing new dimensions.

The pinned control plugin prepends its namespace to `robot_param_node`. Therefore
the URDF uses the relative value `robot_state_publisher` with namespace `/g2/sim`,
resolving to `/g2/sim/robot_state_publisher`. An absolute value would be incorrectly
doubled by this plugin revision and prevent startup.
