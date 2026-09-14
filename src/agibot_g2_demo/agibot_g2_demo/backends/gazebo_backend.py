"""Gazebo simulation adapters using standard ROS interfaces, never vendor SDKs."""
from collections import deque
import copy
import json
import math
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.action import ActionClient
from rclpy.clock import Clock, ClockType
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock as ClockMessage
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint

from .. import implementation_identity
from ..simulation import SimConfig, SimFeedback, SimRun, ordered_sample


STREAM = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT,
                    durability=DurabilityPolicy.VOLATILE)
PUBLIC = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                    durability=DurabilityPolicy.VOLATILE)
STATUS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                    durability=DurabilityPolicy.TRANSIENT_LOCAL)


def load_config(node, parameter):
    if not node.get_parameter('use_sim_time').value:
        raise ValueError('backend=gazebo requires use_sim_time=true')

    def guard(parameters):
        if any(v.name == 'use_sim_time' and v.value is not True for v in parameters):
            return SetParametersResult(successful=False, reason='gazebo requires use_sim_time=true')
        return SetParametersResult(successful=True)
    node.add_on_set_parameters_callback(guard)
    parameter('source', 'gazebo', ignore_override=True)

    def required(name, kind):
        value = node.declare_parameter(name, kind, ParameterDescriptor(
            read_only=True, description='Required model inventory; restart to change')).value
        if not value:
            raise ValueError(name + ' must be supplied from the model joint inventory')
        return tuple(value)

    config = SimConfig(
        names=required('sim_joint_names', Parameter.Type.STRING_ARRAY),
        lower=required('sim_joint_lower_limits', Parameter.Type.DOUBLE_ARRAY),
        upper=required('sim_joint_upper_limits', Parameter.Type.DOUBLE_ARRAY),
        velocity_limits=required('sim_joint_velocity_limits', Parameter.Type.DOUBLE_ARRAY),
        target=parameter('target_joint', ''),
        delta=parameter('displacement', 0.05), duration=parameter('duration', 6.0),
        max_acceleration=parameter('max_acceleration', 0.5),
        position_tolerance=parameter('position_tolerance', 0.002),
        velocity_tolerance=parameter('velocity_tolerance', 0.01),
        stable_duration=parameter('stable_duration', 0.2),
        feedback_timeout=parameter('feedback_timeout', 3.0),
        source_timeout=parameter('sim_feedback_timeout', 1.0),
        pause_timeout=parameter('sim_pause_timeout', 3.0),
        wall_budget=parameter('motion_timeout', 180.0)).validate()
    interfaces = parameter('sim_state_interfaces', ['position', 'velocity'])
    if (len(set(interfaces)) != len(interfaces) or 'position' not in interfaces or
            'velocity' not in interfaces or set(interfaces) - {'position', 'velocity', 'effort'}):
        raise ValueError('simulation requires position and velocity state interfaces')
    return config, interfaces


class GazeboSource:
    """Subscribe to the one simulation world; no publishers synthesize feedback."""
    def __init__(self, node, parameter):
        self.node = node
        self.config, self.interfaces = load_config(node, parameter)
        self.feedback = SimFeedback(self.config)
        self.topic = parameter('sim_joint_topic', '/g2/sim/joint_states')
        if not isinstance(self.topic, str) or not self.topic.startswith('/') or self.topic == '/g2/joint_states':
            raise ValueError('sim_joint_topic must be an absolute simulator feedback topic, not public telemetry')
        self.clock_sub = node.create_subscription(ClockMessage, '/clock', self.clock, STREAM)
        self.state_sub = node.create_subscription(JointState, self.topic, self.receive, STREAM)
        self.steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.closed = False

    def clock(self, message):
        ns = message.clock.sec * 10**9 + message.clock.nanosec
        reset = self.feedback.clock(ns, time.monotonic())
        if reset:
            self.on_reset()

    def on_reset(self):
        pass

    def receive(self, message):
        stamp = message.header.stamp
        try:
            if stamp.sec < 0 or not 0 <= stamp.nanosec < 10**9:
                raise ValueError('invalid simulation timestamp')
            values = ordered_sample(message.name, message.position, message.velocity,
                                    message.effort, self.config, self.interfaces)
            if self.feedback.observe(stamp.sec * 10**9 + stamp.nanosec,
                                     time.monotonic(), *values):
                self.on_sample(message, values)
        except ValueError as error:
            self.feedback.error = str(error)

    def on_sample(self, message, values):
        pass


class GazeboBackend(GazeboSource):
    """Nonblocking trajectory action owner with independent observed completion."""
    def __init__(self, node, parameter):
        self.timer = self.action = self.manager = None
        self.goal = self.send_future = self.result_future = self.cancel_future = None
        self.manager_future = None
        self.manager_checked = self.manager_requested = self.next_manager = 0.0
        self.manager_active = False
        self.closing = False
        super().__init__(node, parameter)
        self.run = SimRun(self.config)
        self.enable_motion = parameter('enable_motion', False)
        if type(self.enable_motion) is not bool:
            raise ValueError('enable_motion must be a boolean')
        self.controller_name = parameter('sim_controller', 'arm_controller')
        manager_name = parameter('sim_controller_manager', '/g2/sim/controller_manager')
        action_name = parameter('sim_action', '/g2/sim/arm_controller/follow_joint_trajectory')
        self.manager = node.create_client(ListControllers, manager_name + '/list_controllers')
        self.action = ActionClient(node, FollowJointTrajectory, action_name)
        self.status_publisher = node.create_publisher(String, 'hello_status', STATUS)
        self.service = node.create_service(Trigger, 'say_hello', self.request)
        self.last_status = None
        self.last_status_wall = 0.0
        self.timer = node.create_timer(0.05, self.tick, clock=self.steady)
        implementation_identity(node, 'gazebo', __file__)
        self.publish_status(force=True)

    def readiness(self, wall):
        if self.closing:
            return 'application is shutting down'
        if self.send_future is not None or self.goal is not None:
            return 'previous controller goal is still awaiting terminal confirmation'
        return self.environment_reason(wall)

    def environment_reason(self, wall):
        reason = self.feedback.reason(wall)
        if reason:
            return reason
        if not self.manager_active or wall - self.manager_checked > 3.0:
            return 'trajectory controller is not freshly confirmed active'
        if not self.action.server_is_ready():
            return 'trajectory action server is unavailable'
        return ''

    def request(self, request, response):
        wall = time.monotonic()
        reason = ('simulation motion is disabled' if not self.enable_motion else
                  'a motion request is already running' if self.run.state == 'RUNNING' else
                  self.readiness(wall))
        response.success = False
        run_id = ''
        if not reason:
            try:
                points = self.run.begin(self.feedback, wall)
                run_id = self.run.run_id
                self.controller_result = None
                self.command_trajectory = None
                token = (run_id, self.run.epoch)
                goal = FollowJointTrajectory.Goal()
                goal.trajectory.joint_names = list(self.config.names)
                # A zero header requests start on controller receipt in sim time.
                for seconds, positions, velocities, accelerations in points:
                    point = JointTrajectoryPoint()
                    point.positions, point.velocities, point.accelerations = positions, velocities, accelerations
                    ns = round(seconds * 1e9)
                    point.time_from_start.sec, point.time_from_start.nanosec = divmod(ns, 10**9)
                    goal.trajectory.points.append(point)
                goal.goal_time_tolerance.sec = 2
                self.command_trajectory = {
                    'joint_names': list(goal.trajectory.joint_names),
                    'header_stamp_ns': 0, 'goal_time_tolerance_ns': 2_000_000_000,
                    'time_domain': 'relative simulation time; starts on controller receipt',
                    'points': [{'time_from_start_ns': p.time_from_start.sec * 10**9 + p.time_from_start.nanosec,
                                'position_rad': list(p.positions), 'velocity_rad_s': list(p.velocities),
                                'acceleration_rad_s2': list(p.accelerations)}
                               for p in goal.trajectory.points]}
                self.send_started = wall
                self.send_future = self.action.send_goal_async(
                    goal, feedback_callback=lambda msg: self.action_feedback(token, msg))
                self.send_future.add_done_callback(lambda future: self.goal_response(token, future))
                response.success = True
                reason = 'request accepted; controller acceptance and observed completion are asynchronous'
            except Exception as error:
                reason = 'trajectory request failed: ' + str(error)
                self.run.fail(reason)
        response.message = json.dumps({'source': 'gazebo', 'run_id': run_id, 'reason': reason})
        self.publish_status(force=True)
        return response

    def current(self, token):
        return (token == (self.run.run_id, self.run.epoch) and
                token[1] == self.feedback.epoch and self.run.state == 'RUNNING' and not self.closing)

    def goal_response(self, token, future):
        if self.send_future is future:
            self.send_future = None
        try:
            handle = future.result()
            if not handle.accepted:
                if self.current(token):
                    self.run.fail('trajectory controller rejected the goal')
                return
            self.goal = handle
            self.result_future = handle.get_result_async()
            self.result_future.add_done_callback(lambda result: self.goal_result(token, handle, result))
            if not self.current(token):
                self.cancel('canceling obsolete or timed-out goal')
            else:
                self.run.reason = 'controller accepted the trajectory; monitoring simulator feedback'
        except Exception as error:
            self.run.fail('controller goal response error: ' + str(error))
        self.publish_status(force=True)

    def action_feedback(self, token, message):
        # Action feedback is diagnostic only. Success requires broadcaster data.
        if self.current(token):
            self.last_action_feedback_wall = time.monotonic()

    def goal_result(self, token, handle, future):
        try:
            response = future.result()
            if self.current(token):
                ok = (response.status == GoalStatus.STATUS_SUCCEEDED and
                      response.result.error_code == FollowJointTrajectory.Result.SUCCESSFUL)
                reason = ('controller status=' + str(response.status) + ' error=' +
                          str(response.result.error_code) + ' ' + response.result.error_string)
                self.run.result(ok, reason, self.feedback)
                self.controller_result = {'status': response.status,
                                          'error_code': response.result.error_code,
                                          'error_string': response.result.error_string}
        except Exception as error:
            if self.current(token):
                self.run.fail('controller result error: ' + str(error))
        finally:
            if self.goal is handle:
                self.goal = self.result_future = self.cancel_future = None
        self.publish_status(force=True)

    def cancel(self, reason):
        self.run.fail(reason)
        if self.goal is not None and self.cancel_future is None:
            try:
                self.cancel_future = self.goal.cancel_goal_async()
                self.cancel_future.add_done_callback(self.cancel_response)
            except Exception as error:
                self.node.get_logger().error('goal cancellation request failed: ' + str(error))

    def cancel_response(self, future):
        try:
            response = future.result()
            self.node.get_logger().info('simulation cancellation response return_code=' +
                                        str(response.return_code) + '; awaiting action terminal result')
        except Exception as error:
            self.node.get_logger().error('simulation cancellation response failed: ' + str(error))

    def on_sample(self, message, values):
        if hasattr(self, 'run') and self.run.state == 'RUNNING':
            self.run.update(self.feedback, time.monotonic())
            if self.run.state == 'FAILED':
                self.cancel(self.run.reason)

    def on_reset(self):
        if hasattr(self, 'run'):
            self.cancel('simulation clock reset; old run cannot resume')
            self.publish_status(force=True)

    def manager_response(self, future):
        if self.manager_future is not future:
            return
        self.manager_future = None
        try:
            controllers = future.result().controller
            matches = [c for c in controllers if c.name == self.controller_name]
            self.manager_active = len(matches) == 1 and matches[0].state == 'active'
            self.manager_checked = time.monotonic()
        except Exception:
            self.manager_active = False

    def tick(self):
        wall = time.monotonic()
        if self.manager_future is not None and wall - self.manager_requested > 3.0:
            expired, self.manager_future = self.manager_future, None
            expired.cancel()
            self.manager_active = False
        if not self.closing and wall >= self.next_manager and self.manager_future is None:
            self.next_manager = wall + 0.5
            if self.manager.service_is_ready():
                self.manager_requested = wall
                self.manager_future = self.manager.call_async(ListControllers.Request())
                self.manager_future.add_done_callback(self.manager_response)
            else:
                self.manager_active = False
        if self.run.state == 'RUNNING':
            if self.send_future is not None and wall - self.send_started > 3.0:
                self.cancel('controller acceptance wall timeout; late acceptance will be canceled')
            else:
                reason = self.environment_reason(wall)
                if reason:
                    self.cancel(reason)
                else:
                    self.run.update(self.feedback, wall)
                    if self.run.state == 'FAILED':
                        self.cancel(self.run.reason)
        self.publish_status()

    def publish_status(self, force=False):
        wall = time.monotonic()
        reason = self.environment_reason(wall)
        payload = {'source': 'gazebo', 'backend': 'gazebo', 'run_id': self.run.run_id,
                   'state': self.run.state, 'reason': self.run.reason,
                   'healthy': not bool(reason), 'health_reason': reason,
                   'clock_epoch': self.feedback.epoch, 'simulation_time_ns': self.feedback.clock_ns,
                   'source_stamp_ns': self.feedback.stamp_ns, 'observed_excursion_rad': self.run.peak,
                   'controller_result': getattr(self, 'controller_result', None),
                   'command_trajectory': getattr(self, 'command_trajectory', None),
                   'pending_controller_goal': self.goal is not None or self.send_future is not None}
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        if force or encoded != self.last_status or wall - self.last_status_wall >= 0.5:
            self.status_publisher.publish(String(data=encoded))
            # Avoid emitting a console line for every physics sample timestamp.
            key = (self.run.run_id, self.run.state, self.run.reason, bool(reason))
            if key != getattr(self, 'last_log_key', None):
                self.node.get_logger().info(encoded)
                self.last_log_key = key
            self.last_status, self.last_status_wall = encoded, wall

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.cancel('application shutdown during simulation motion')
        if self.timer is not None:
            self.timer.cancel()
        self.publish_status(force=True)

    def shutdown_pending(self):
        return self.send_future is not None or self.goal is not None


class GazeboTelemetry(GazeboSource):
    """Forward only new simulator samples, throttled by their sampling clock."""
    def __init__(self, node, parameter):
        super().__init__(node, parameter)
        self.publish_hz = parameter('publish_hz', 10.0)
        if not isinstance(self.publish_hz, (float, int)) or not math.isfinite(self.publish_hz) or not 0 < self.publish_hz <= 100:
            raise ValueError('publish_hz must be finite in (0,100]')
        self.publisher = node.create_publisher(JointState, 'joint_states', PUBLIC)
        self.health_publisher = node.create_publisher(String, 'telemetry_health', STATUS)
        self.last_published_stamp = None
        self.published = 0
        self.arrivals = deque(maxlen=500)
        self.timer = node.create_timer(0.2, self.health, clock=self.steady)
        implementation_identity(node, 'gazebo', __file__)
        self.health()

    def on_reset(self):
        self.last_published_stamp = None
        self.arrivals.clear()

    def on_sample(self, message, values):
        ns = self.feedback.stamp_ns
        self.arrivals.append((ns, time.monotonic()))
        if self.last_published_stamp is not None and ns - self.last_published_stamp < round(1e9 / self.publish_hz):
            return
        forwarded = copy.deepcopy(message)
        forwarded.name = list(self.config.names)
        forwarded.position, forwarded.velocity, forwarded.effort = values
        self.publisher.publish(forwarded)
        self.published += 1
        self.last_published_stamp = ns

    def health(self):
        wall = time.monotonic()
        reason = self.feedback.reason(wall)
        sim_hz = wall_hz = rtf = 0.0
        if len(self.arrivals) > 1 and not reason:
            sim_duration = (self.arrivals[-1][0] - self.arrivals[0][0]) / 1e9
            wall_duration = self.arrivals[-1][1] - self.arrivals[0][1]
            if sim_duration > 0 and wall_duration > 0:
                sim_hz = (len(self.arrivals) - 1) / sim_duration
                wall_hz = (len(self.arrivals) - 1) / wall_duration
                rtf = sim_duration / wall_duration
        payload = {'source': 'gazebo', 'status': 'STALE' if reason else 'HEALTHY',
                   'reason': reason or 'new simulator observations', 'published_samples': self.published,
                   'configured_hz': self.publish_hz, 'source_sim_hz': sim_hz,
                   'source_wall_hz': wall_hz, 'measured_real_time_factor': rtf,
                   'source_clock_domain': 'gazebo_simulation', 'clock_epoch': self.feedback.epoch,
                   'stamp_kind': 'preserved_simulator_sample_time', 'position_unit': 'rad'}
        self.health_publisher.publish(String(data=json.dumps(payload, allow_nan=False)))

    def close(self):
        if not self.closed:
            self.closed = True
            self.timer.cancel()
