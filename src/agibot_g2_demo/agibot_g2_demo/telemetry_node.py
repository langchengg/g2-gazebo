"""Validate source observations and publish each accepted observation once."""
from collections import deque
import json
import math
import time

from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from . import implementation_identity, ros_main
from .backends.base import Observation
from .motion import SourceFreshness, mock_joint_names, validate_observation


class TelemetryNode(Node):
    def __init__(self):
        super().__init__('telemetry', namespace='/g2')
        self.timer = self.sim = None
        self.closed = False
        try:
            self._configure()
        except BaseException:
            self.close()
            self.destroy_node()
            raise

    def parameter(self, name, default, ignore_override=False):
        return self.declare_parameter(name, default, ParameterDescriptor(
            read_only=True, description='Project configuration; restart to change'),
            ignore_override=ignore_override).value

    @staticmethod
    def guard_clock(parameters):
        for value in parameters:
            if value.name == 'use_sim_time' and (type(value.value) is not bool or value.value):
                return SetParametersResult(successful=False,
                    reason='telemetry requires use_sim_time=false; source header uses local ROS system time')
        return SetParametersResult(successful=True)

    def _configure(self):
        self.backend = self.parameter('backend', 'mock')
        if self.backend == 'gazebo':
            from .backends.gazebo_backend import GazeboTelemetry
            self.sim = GazeboTelemetry(self, self.parameter)
            return
        if self.backend not in ('mock', 'gdk'):
            raise ValueError('backend must be mock or gdk')
        if self.get_parameter('use_sim_time').value or self.get_clock().ros_time_is_active:
            raise ValueError('telemetry requires use_sim_time=false and the owner local ROS system-time domain')
        self.add_on_set_parameters_callback(self.guard_clock)
        self.parameter('source', self.backend, ignore_override=True)
        if self.backend == 'mock':
            self.expected_names = list(mock_joint_names())
            self.stamp_kind = 'local_ros_observation_time'
            self.clock_domain = 'mock_local_ros_system_time'
        else:
            from .backends.gdk_backend import preflight_gdk
            metadata = preflight_gdk(sdk_config_path=self.parameter('sdk_config_path', ''),
                                     expected_sdk_version='2.6.3')
            self.expected_names = list(metadata['joint_names'])
            self.stamp_kind = 'local_receive_time_only; not_hardware_sampling_time'
            self.clock_domain = 'gdk_bridge_local_ros_receive_time'
        self.publish_hz = self.parameter('publish_hz', 10.0)
        self.timeout = self.parameter('feedback_timeout', 0.6)
        self.future_tolerance = self.parameter('future_tolerance', 0.05)
        if not math.isfinite(self.publish_hz) or not 0 < self.publish_hz <= 50:
            raise ValueError('publish_hz must be finite and in (0,50]')
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('feedback_timeout must be finite and positive')
        if not math.isfinite(self.future_tolerance) or not 0 <= self.future_tolerance <= 0.1:
            raise ValueError('future_tolerance must be finite and in [0,0.1] seconds')
        self.freshness = SourceFreshness(self.timeout)
        self.started = time.monotonic()
        self.invalid = self.last_health = ''
        self.rejected_time = None
        self.non_advancing = self.seen = False
        self.accepted_stamp = None
        self.arrivals = deque()
        self.published = 0
        stream = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                            durability=DurabilityPolicy.VOLATILE)
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.joint_publisher = self.create_publisher(JointState, 'joint_states', stream)
        self.health_publisher = self.create_publisher(String, 'telemetry_health', latched)
        self.subscription = self.create_subscription(JointState, 'internal/joint_states', self.receive, stream)
        self.timer_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(0.1, self.health, clock=self.timer_clock)
        implementation_identity(self, self.backend, __file__)
        self.publish_health('WAITING', 'waiting for a valid advancing source observation')

    def check_local_stamp_age(self, stamp):
        # Mock header stamps use local observation time. GDK header stamps use
        # local bridge receipt time only: this does NOT validate device age or
        # establish any mapping from the opaque hardware sampling clock.
        if self.get_parameter('use_sim_time').value or self.get_clock().ros_time_is_active:
            return 'INVALID', 'local ROS system-time domain unavailable; use_sim_time must remain false'
        current = self.get_clock().now().nanoseconds
        if current <= 0:
            return 'INVALID', 'local ROS system time is unset or invalid'
        age = (current - stamp) / 1e9
        if not math.isfinite(age):
            return 'INVALID', 'source sample age is not finite'
        if age < -self.future_tolerance:
            return 'INVALID', 'source sample is in the future beyond future_tolerance'
        if age > self.timeout:
            return 'STALE', 'source sample expired: age exceeds feedback_timeout'
        return None

    def receive(self, message):
        received = time.monotonic()
        observation = Observation(names=list(message.name), positions=list(message.position),
                                  velocities=list(message.velocity), efforts=list(message.effort))
        error = validate_observation(observation)
        if error or list(message.name) != self.expected_names:
            self.invalid = error or 'unexpected joint names or order'
            self.publish_health('INVALID', self.invalid)
            return
        stamp = message.header.stamp
        if stamp.sec < 0 or stamp.nanosec >= 10**9 or (stamp.sec == 0 and stamp.nanosec == 0):
            self.invalid = 'invalid or unset source timestamp'
            self.publish_health('INVALID', self.invalid)
            return
        if self.backend == 'gdk' and message.header.frame_id != 'gdk_local_receive_time_only':
            self.invalid = 'GDK source must explicitly identify bridge local receive timestamps'
            self.publish_health('INVALID', self.invalid)
            return
        stamp_ns = stamp.sec * 10**9 + stamp.nanosec
        self.rejected_time = self.check_local_stamp_age(stamp_ns)
        if self.rejected_time:
            self.invalid = ''
            self.publish_health(*self.rejected_time)
            return
        if not self.freshness.observe(stamp_ns, None, received):
            self.invalid, self.non_advancing = '', True
            self.publish_health('STALE', 'source timestamp did not advance: ' + self.freshness.reason(received))
            return
        self.invalid, self.non_advancing, self.seen = '', False, True
        self.accepted_stamp = stamp_ns
        self.arrivals.append(received)
        while len(self.arrivals) > 1 and received - self.arrivals[0] > 5:
            self.arrivals.popleft()
        self.joint_publisher.publish(message)
        self.published += 1
        self.publish_health('HEALTHY', 'valid advancing source observation')

    def health(self):
        current = time.monotonic()
        if self.invalid:
            self.publish_health('INVALID', self.invalid)
        elif self.rejected_time:
            self.publish_health(*self.rejected_time)
        elif self.non_advancing:
            self.publish_health('STALE', 'source timestamp did not advance: ' + self.freshness.reason(current))
        elif not self.seen and current - self.started < self.timeout:
            self.publish_health('WAITING', 'waiting for source observation')
        elif not self.freshness.healthy(current):
            self.publish_health('STALE', self.freshness.reason(current))
        else:
            issue = self.check_local_stamp_age(self.accepted_stamp)
            self.publish_health(*(issue or ('HEALTHY', 'valid advancing source observation')))

    def publish_health(self, status, reason):
        current = time.monotonic()
        source_hz = 0.0
        if len(self.arrivals) >= 2 and current - self.arrivals[-1] <= self.timeout:
            duration = self.arrivals[-1] - self.arrivals[0]
            source_hz = (len(self.arrivals)-1) / duration if duration > 0 else 0.0
        payload = {'source': self.backend, 'status': status, 'reason': reason,
                   'source_hz': source_hz, 'configured_hz': self.publish_hz,
                   'future_tolerance_s': self.future_tolerance, 'source_clock_domain': self.clock_domain,
                   'source_rate_basis': 'unique_samples_local_receive_time',
                   'published_samples': self.published, 'stamp_kind': self.stamp_kind,
                   'position_unit': 'rad'}
        if self.backend == 'gdk':
            payload['hardware_sample_age'] = 'UNVERIFIED; opaque device clock has no ROS-time mapping'
        self.health_publisher.publish(String(data=json.dumps(payload, allow_nan=False)))
        if status != self.last_health and status in ('STALE', 'INVALID'):
            self.get_logger().warning(f'source={self.backend} status={status} reason={reason}')
        self.last_health = status

    def close(self):
        if not self.closed:
            self.closed = True
            if self.sim is not None:
                self.sim.close()
            if self.timer is not None:
                self.timer.cancel()


def main(args=None):
    return ros_main(TelemetryNode, args)
