"""The only backend owner. Every topic/service here is a project interface."""
import dataclasses
import json
import math
import time

from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_services_default)
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger

from . import implementation_identity, ros_main
from .motion import Config, Engine, MotionState, valid_fault, validate_observation


class SayHelloNode(Node):
    def __init__(self):
        super().__init__('sayHello', namespace='/g2')
        self.engine = self.gdk = self.sim = self.timer = None
        self.closed = False
        try:
            self._configure()
        except BaseException:
            self.close()
            self.destroy_node()
            raise

    def parameter(self, name, default, ignore_override=False):
        descriptor = ParameterDescriptor(
            read_only=True, description='Project configuration; restart to change')
        return self.declare_parameter(name, default, descriptor,
                                      ignore_override=ignore_override).value

    @staticmethod
    def guard_clock(parameters):
        for value in parameters:
            if value.name == 'use_sim_time' and (type(value.value) is not bool or value.value):
                return SetParametersResult(successful=False,
                    reason='this backend wrapper requires use_sim_time=false; timestamps are local reception/observation time')
        return SetParametersResult(successful=True)

    def _configure(self):
        self.backend = self.parameter('backend', 'mock')
        if self.backend == 'gazebo':
            from .backends.gazebo_backend import GazeboBackend
            self.sim = GazeboBackend(self, self.parameter)
            return
        if self.backend not in ('mock', 'gdk'):
            raise ValueError('backend must be mock or gdk')
        if self.get_parameter('use_sim_time').value:
            raise ValueError('sayHello requires use_sim_time=false for its local ROS timestamp mapping')
        self.add_on_set_parameters_callback(self.guard_clock)
        self.parameter('source', self.backend, ignore_override=True)
        self.enable_motion = self.parameter('enable_motion', False)
        self.publish_hz = self.parameter('publish_hz', 10.0)
        self.feedback_timeout = self.parameter('feedback_timeout', 0.6)
        if not math.isfinite(self.publish_hz) or not 0 < self.publish_hz <= 50:
            raise ValueError('publish_hz must be finite and in (0,50]')
        if not math.isfinite(self.feedback_timeout) or self.feedback_timeout <= 0:
            raise ValueError('feedback_timeout must be finite and positive')
        self.fault_mode = self.parameter('fault_mode', 'none')
        self.fault_after = self.parameter('fault_after', 0.5)
        if not valid_fault(self.fault_mode) or not math.isfinite(self.fault_after) or not 0 <= self.fault_after <= 60:
            raise ValueError('invalid mock fault_mode or fault_after outside [0,60] seconds')
        if self.backend == 'mock':
            config = Config()
            supplied = {'backend': self.backend, 'enable_motion': self.enable_motion,
                        'publish_hz': self.publish_hz, 'feedback_timeout': self.feedback_timeout,
                        'fault': 'none'}
            for field in dataclasses.fields(config):
                if field.name not in supplied:
                    supplied[field.name] = self.parameter(field.name, getattr(config, field.name))
            self.engine = Engine(Config(**supplied))
            self.clock_semantics = 'local_ros_observation_time'
        else:
            if self.enable_motion:
                raise RuntimeError('GDK motion UNIMPLEMENTED: enable_motion must remain false')
            if self.fault_mode != 'none':
                raise ValueError('fault injection is available only for backend=mock')
            from .backends.gdk_backend import GdkBackend
            self.gdk = GdkBackend(
                sdk_config_path=self.parameter('sdk_config_path', ''),
                expected_sdk_version='2.6.3',
                startup_timeout=self.parameter('gdk_startup_timeout', 5.0),
                poll_timeout=self.parameter('gdk_poll_timeout', 0.5))
            self.clock_semantics = 'local_receive_time_only; device timestamp opaque'
        stream = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                            durability=DurabilityPolicy.VOLATILE)
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.joint_publisher = self.create_publisher(JointState, 'internal/joint_states', stream)
        self.status_publisher = self.create_publisher(String, 'hello_status', latched)
        self.service = self.create_service(Trigger, 'say_hello', self.request,
                                           qos_profile=qos_profile_services_default)
        self.run_started = self.next_publication = self.last_status_time = 0.0
        self.fault_applied = False
        self.observation = None
        self.observed_sequence = self.published_sequence = self.mapped_stamp = None
        self.last_status = None
        self.gdk_error = ''
        self.timer_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(0.02, self.tick, clock=self.timer_clock)
        implementation_identity(self, self.backend, __file__)
        self.publish_status(time.monotonic(), force=True)
        self.get_logger().info(f'source={self.backend} enable_motion={self.enable_motion}; startup never requests movement')

    def healthy(self, current):
        if self.engine is not None:
            return self.engine.healthy(current)
        return self.gdk is not None and not self.gdk_error and self.gdk.healthy(current)

    def health_reason(self, current):
        if self.engine is not None:
            return self.engine.health_reason(current)
        return self.gdk_error or self.gdk.health_reason(current)

    def request(self, _request, response):
        current = time.monotonic()
        if self.engine is not None:
            result = self.engine.request(current)
            response.success = result.accepted
            run_id, reason = result.run_id, result.reason
            if result.accepted:
                self.run_started, self.fault_applied = current, False
        else:
            response.success = False
            run_id, reason = '', 'GDK motion UNIMPLEMENTED: this adapter is explicitly read-only'
        response.message = json.dumps({'source': self.backend, 'run_id': run_id, 'reason': reason})
        self.publish_status(current, force=True)
        return response

    def tick(self):
        current = time.monotonic()
        ros_sample_time = self.get_clock().now().to_msg()
        if self.engine is not None:
            if (self.engine.status.state == MotionState.RUNNING and not self.fault_applied and
                    self.fault_mode != 'none' and current - self.run_started >= self.fault_after):
                self.engine.set_fault(self.fault_mode)
                self.fault_applied = True
                self.get_logger().warning(f'injecting synthetic fault_mode={self.fault_mode}')
            self.engine.tick(current)
            observation = self.engine.observation
        else:
            observation = None
            if not self.gdk_error:
                try:
                    observation = self.gdk.poll(current)
                except Exception as error:
                    self.gdk_error = f'GDK read-only backend failure: {error}'
            if self.gdk.failed:
                self.gdk_error = 'GDK read-only backend failure: ' + self.gdk.failure_reason
            if self.gdk_error:
                self.publish_status(current, force=True)
                raise RuntimeError(self.gdk_error)
        if observation is not None:
            error = validate_observation(observation)
            if error:
                if self.backend == 'gdk':
                    self.gdk_error = 'invalid GDK observation: ' + error
                    self.publish_status(current, force=True)
                    raise RuntimeError(self.gdk_error)
                observation = None
            elif observation.sequence != self.observed_sequence:
                self.observation = observation
                self.observed_sequence = observation.sequence
                self.mapped_stamp = ros_sample_time
        if current >= self.next_publication:
            if (self.observation is not None and self.mapped_stamp is not None and
                    self.healthy(current) and self.observed_sequence != self.published_sequence):
                message = JointState()
                message.header.stamp = self.mapped_stamp
                message.header.frame_id = ('mock_joint_observation' if self.backend == 'mock'
                                           else 'gdk_local_receive_time_only')
                message.name = list(self.observation.names)
                message.position = list(self.observation.positions)
                message.velocity = list(self.observation.velocities)
                message.effort = list(self.observation.efforts)
                self.joint_publisher.publish(message)
                self.published_sequence = self.observed_sequence
            self.next_publication += 1.0 / self.publish_hz
            if self.next_publication <= current:
                self.next_publication = current + 1.0 / self.publish_hz
        self.publish_status(current)

    def publish_status(self, current, force=False):
        if self.engine is not None:
            status = self.engine.status
            state, run_id, reason = status.state.value, status.run_id, status.reason
        else:
            state = 'FAILED' if self.gdk_error else 'IDLE'
            run_id, reason = '', self.gdk_error or 'read-only GDK adapter; motion UNIMPLEMENTED'
        payload = {'source': self.backend, 'state': state, 'run_id': run_id, 'reason': reason,
                   'healthy': bool(self.healthy(current)), 'health_reason': self.health_reason(current)}
        if self.backend == 'gdk':
            payload.update(source_timestamp=getattr(self.gdk, 'last_source_timestamp', None),
                           stamp_kind=self.clock_semantics)
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        if force or encoded != self.last_status or current - self.last_status_time >= 0.5:
            self.status_publisher.publish(String(data=encoded))
            if encoded != self.last_status:
                self.get_logger().info(encoded)
            self.last_status, self.last_status_time = encoded, current

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.sim is not None:
            self.sim.close()
        if self.timer is not None:
            self.timer.cancel()
        if self.engine is not None:
            self.engine.shutdown(time.monotonic())
        if self.gdk is not None:
            self.gdk.shutdown(time.monotonic())
            self.get_logger().info('GDK release status: ' + self.gdk.release_status)


def main(args=None):
    return ros_main(SayHelloNode, args)
