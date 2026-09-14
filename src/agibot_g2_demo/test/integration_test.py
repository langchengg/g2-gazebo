#!/usr/bin/env python3
"""Actual ROS service/topic tests. No hardware backend is ever enabled."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import pytest
import rclpy
from ament_index_python.packages import get_package_prefix
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger

pytestmark = pytest.mark.integration

STREAM = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                    durability=DurabilityPolicy.VOLATILE)
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
BASE = Path(os.environ.get('EVIDENCE_DIR', '/tmp/g2-test-evidence'))
BIN = Path(get_package_prefix('agibot_g2_demo')) / 'lib' / 'agibot_g2_demo'
ACTIVE = set()


def terminate_runner(_signum, _frame):
    for harness in list(ACTIVE):
        harness.stop()
    raise SystemExit(143)


@pytest.fixture(scope='module', autouse=True)
def ros_context():
    rclpy.init()
    previous=signal.signal(signal.SIGTERM,terminate_runner)
    try:
        yield
    finally:
        for harness in list(ACTIVE):
            harness.stop()
        signal.signal(signal.SIGTERM,previous)
        rclpy.shutdown()


class Harness:
    def __init__(self, label, motion=False, fault='none', namespace=None, owner=True, out=None):
        self.path = Path(out or BASE) / (label + '-' + uuid.uuid4().hex[:8])
        self.path.mkdir(parents=True, exist_ok=True)
        self.ns = namespace or '/g2test_' + uuid.uuid4().hex[:8]
        self.samples, self.internal, self.states, self.health = [], [], [], []
        self.processes, self.logs = {}, []
        self.identities = {}
        self.closed = False
        self.node = rclpy.create_node('test_probe', namespace=self.ns)
        self.subs = [
            self.node.create_subscription(JointState, self.ns+'/joint_states', self.sample, STREAM),
            self.node.create_subscription(JointState, self.ns+'/internal/joint_states',
                                          lambda m: self.internal.append(m), STREAM),
            self.node.create_subscription(String, self.ns+'/hello_status',
                                          lambda m: self.states.append(json.loads(m.data)), LATCHED),
            self.node.create_subscription(String, self.ns+'/telemetry_health',
                                          lambda m: self.health.append(json.loads(m.data)), LATCHED)]
        self.client = self.node.create_client(Trigger, self.ns+'/say_hello')
        ACTIVE.add(self)
        try:
            if owner:
                self.start('sayHello', {'enable_motion': motion, 'fault_mode': fault})
            self.start('telemetry', {})
        except BaseException:
            self.stop()
            raise

    def start(self, executable, params):
        args = [str(BIN/executable), '--ros-args', '-r', '__ns:='+self.ns]
        for key, value in params.items():
            encoded=json.dumps(value) if isinstance(value,str) else str(value).lower()
            args += ['-p', key+':='+encoded]
        log = (self.path/(executable+'.log')).open('w')
        self.logs.append(log)
        self.processes[executable] = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                                     start_new_session=True,
                                                     env=dict(os.environ, EVIDENCE_DIR=str(self.path)))

    def verify_python_identity(self):
        modules = {'sayHello': 'say_hello_node.py', 'telemetry': 'telemetry_node.py'}
        for name, process in self.processes.items():
            entrypoint = BIN / name
            content = entrypoint.read_bytes()
            assert content.startswith(b'#!') and not content.startswith(b'\x7fELF'), entrypoint
            assert b'python' in content.splitlines()[0].lower(), content[:100]
            identity_path = self.path / f'identity-{name}-{process.pid}.json'
            assert identity_path.exists(), identity_path
            identity = json.loads(identity_path.read_text())
            assert identity['implementation'] == 'python-rclpy'
            assert identity['backend'] == 'mock' and identity['pid'] == process.pid
            assert identity['node_name'] == name and identity['namespace'] == self.ns
            module = Path(identity['module_file'])
            loaded_module = Path(identity['module_loaded_file'])
            assert module.name == modules[name] and module.suffix == '.py'
            assert 'legacy' not in module.parts and module.exists()
            prefix = Path(get_package_prefix('agibot_g2_demo')).resolve()
            assert loaded_module.is_relative_to(prefix), (loaded_module, prefix)
            proc = Path('/proc') / str(process.pid)
            assert proc.exists(), 'process identity verification requires the target Linux environment'
            command_line = (proc / 'cmdline').read_bytes().split(b'\0')
            command_line = [x.decode(errors='replace') for x in command_line if x]
            interpreter = os.readlink(proc / 'exe')
            assert 'python' in Path(interpreter).name.lower(), interpreter
            assert str(entrypoint) in command_line, command_line
            assert all('legacy/cpp' not in arg for arg in command_line)
            identity.update(installed_entrypoint=str(entrypoint),
                            proc_executable=interpreter, proc_command_line=command_line)
            self.identities[name] = identity
        (self.path / 'identity.json').write_text(json.dumps(self.identities, indent=2))

    def sample(self, msg):
        self.samples.append({'receive_monotonic': time.monotonic(),
            'stamp_ns': msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,
            'frame_id': msg.header.frame_id, 'names': list(msg.name),
            'positions': list(msg.position), 'velocities': list(msg.velocity), 'efforts': list(msg.effort)})

    def spin_until(self, predicate, timeout=10, alive=True):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():
                return
            if alive:
                for name, p in self.processes.items():
                    assert p.poll() is None, f'{name} exited: {p.returncode}; {self.path}'
            rclpy.spin_once(self.node, timeout_sec=0.03)
        assert predicate(), f'ROS condition timed out after {timeout}s; {self.path}'

    def spin_for(self, seconds):
        end = time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(self.node, timeout_sec=0.03)

    def ready(self):
        self.spin_until(lambda: self.client.service_is_ready() and len(self.samples)>=12 and
                        any(h.get('status')=='HEALTHY' for h in self.health), 15)
        actual = {(n,ns) for n,ns in self.node.get_node_names_and_namespaces()}
        assert ('sayHello',self.ns) in actual and ('telemetry',self.ns) in actual
        apps = {(n,ns) for n,ns in actual if ns==self.ns and n!='test_probe'}
        assert apps=={('sayHello',self.ns),('telemetry',self.ns)}, apps
        self.verify_python_identity()

    def request(self):
        fut = self.client.call_async(Trigger.Request())
        self.spin_until(fut.done, 4)
        assert fut.exception() is None
        return fut.result()

    def stop(self):
        if self.closed:
            return
        self.closed=True
        ACTIVE.discard(self)
        failures=[]
        for name,p in self.processes.items():
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for name,p in self.processes.items():
            try:
                p.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait(timeout=3)
                failures.append(name+' required SIGKILL')
        (self.path/'samples.json').write_text(json.dumps(self.samples, indent=2))
        (self.path/'states.json').write_text(json.dumps(self.states, indent=2))
        (self.path/'health.json').write_text(json.dumps(self.health, indent=2))
        for f in self.logs:
            f.close()
        self.node.destroy_node()
        assert not failures, failures

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()


def validate_samples(h, samples):
    assert len(samples)>=25
    names=samples[0]['names']
    assert len(names)==len(set(names)) and all(n.startswith('mock_') for n in names)
    for s in samples:
        assert s['names']==names and len(s['positions'])==len(names)
        assert len(s['velocities']) in (0,len(names)) and s['efforts']==[]
        assert all(math.isfinite(v) for v in s['positions']+s['velocities'])
    stamps=[s['stamp_ns'] for s in samples]
    assert all(b>a for a,b in zip(stamps,stamps[1:]))
    hz=(len(samples)-1)/(samples[-1]['receive_monotonic']-samples[0]['receive_monotonic'])
    # Container scheduling may delay individual deliveries; long-window mean stays close to 10Hz.
    assert 7.0<=hz<=13.0, hz
    source_stamps={m.header.stamp.sec*10**9+m.header.stamp.nanosec for m in h.internal}
    assert set(stamps)<=source_stamps, 'telemetry must preserve the observed source timestamp'
    return hz


def success_path(h, concurrent=True):
    h.ready()
    baseline=h.samples[-1]['positions'][:]
    target=h.samples[-1]['names'].index('mock_left_arm_joint1')
    start=len(h.samples)
    if concurrent:
        calls=[h.client.call_async(Trigger.Request()) for _ in range(2)]
        h.spin_until(lambda: all(f.done() for f in calls),4)
        responses=[f.result() for f in calls]
        assert sum(r.success for r in responses)==1, 'concurrent requests must not both start'
        response=next(r for r in responses if r.success)
    else:
        response=h.request()
        assert response.success, response.message
    run_id=json.loads(response.message)['run_id']
    assert run_id
    h.spin_until(lambda: any(s['run_id']==run_id and s['state']=='RUNNING' for s in h.states),3)
    duplicate=h.request()
    assert not duplicate.success
    h.spin_until(lambda: any(s['run_id']==run_id and s['state'] in ('SUCCEEDED','FAILED')
                            for s in h.states),10)
    terminal=next(s for s in reversed(h.states) if s['run_id']==run_id and s['state'] in ('SUCCEEDED','FAILED'))
    assert terminal['state']=='SUCCEEDED', terminal
    assert terminal['source']=='mock'
    h.spin_for(0.3)
    data=h.samples[start:]
    assert data
    excursion=max(abs(s['positions'][target]-baseline[target]) for s in data)
    assert 0.04<=excursion<=0.051, excursion
    assert abs(data[-1]['positions'][target]-baseline[target])<=0.002
    for s in data:
        for i,p in enumerate(s['positions']):
            if i!=target:
                assert abs(p-baseline[i])<1e-10, 'non-target joint changed'
    elapsed=data[-1]['receive_monotonic']-data[0]['receive_monotonic']
    assert 3.5<=elapsed<=8.0
    hz=validate_samples(h,data)
    metrics={'run_id':run_id,'source':'mock','samples':len(data),'observed_hz':hz,
             'excursion_rad':excursion,'final_error_rad':abs(data[-1]['positions'][target]-baseline[target]),
             'observed_duration_s':elapsed,'result':'PASS'}
    (h.path/('metrics-'+run_id+'.json')).write_text(json.dumps(metrics,indent=2))
    return metrics


def test_default_no_motion_and_disabled_service():
    with Harness('default-disabled') as h:
        h.ready()
        assert not h.request().success
        h.spin_for(0.5)
        assert all(s['positions']==h.samples[0]['positions'] for s in h.samples)
        assert not any(s['state']=='RUNNING' for s in h.states)


def test_movement_concurrency_repeat_and_old_latched_status():
    with Harness('success-and-repeat',motion=True) as h:
        first=success_path(h)
        late=[]
        sub=h.node.create_subscription(String,h.ns+'/hello_status',lambda m:late.append(json.loads(m.data)),LATCHED)
        h.spin_until(lambda: bool(late),3)
        assert late[-1]['run_id']==first['run_id'] and late[-1]['state']=='SUCCEEDED'
        second=success_path(h,concurrent=False)
        assert second['run_id']!=first['run_id']
        h.node.destroy_subscription(sub)


@pytest.mark.parametrize('fault',['freeze','repeat','error','nan','inf','invalid','timeout','watchdog'])
def test_faults_never_succeed(fault):
    with Harness('fault-'+fault,motion=True,fault=fault) as h:
        h.ready()
        response=h.request()
        assert response.success, response.message
        run_id=json.loads(response.message)['run_id']
        h.spin_until(lambda:any(s['run_id']==run_id and s['state']=='FAILED' for s in h.states),10)
        assert not any(s['run_id']==run_id and s['state']=='SUCCEEDED' for s in h.states)
        assert not h.request().success, 'fault must not automatically resume or restart'


def test_telemetry_rejects_bad_and_repeated_samples():
    with Harness('telemetry-validation',owner=False) as h:
        pub=h.node.create_publisher(JointState,h.ns+'/internal/joint_states',STREAM)
        h.spin_until(lambda:pub.get_subscription_count()>=2,8)
        stamp=time.time_ns()
        def emit(offset=0,positions=None,names=None):
            m=JointState()
            m.header.stamp.sec=(stamp+offset)//10**9
            m.header.stamp.nanosec=(stamp+offset)%10**9
            m.header.frame_id='mock_base_link'
            m.name=names if names is not None else [
                f'mock_{side}_arm_joint{i}' for side in ('left','right') for i in range(1,4)]
            m.position=positions if positions is not None else [0.3]*6
            pub.publish(m)
        emit()
        h.spin_until(lambda:len(h.samples)==1,3)
        assert h.samples[0]['stamp_ns']==stamp
        end=time.monotonic()+0.9
        while time.monotonic()<end:
            emit()
            h.spin_for(0.05)
        assert len(h.samples)==1, 'repeated cache must not be republished as new'
        h.spin_until(lambda:h.health and h.health[-1].get('status')!='HEALTHY',3)
        expected_names=[f'mock_{side}_arm_joint{i}' for side in ('left','right') for i in range(1,4)]
        invalid=[([],expected_names),([math.nan]+[0.3]*5,expected_names),
                 ([math.inf]+[0.3]*5,expected_names),([0.0,0.0],['mock_dup','mock_dup']),
                 ([0.3],['mock_test_joint'])]
        for positions,names in invalid:
            # Keep invalid-field samples fresh so age rejection cannot mask a
            # regression in name/dimension/finiteness validation.
            emit(h.node.get_clock().now().nanoseconds-stamp,positions,names)
            h.spin_for(0.15)
        assert len(h.samples)==1
        # An advancing marker can still describe a buffered, expired sample.
        emit(1)
        h.spin_for(0.15)
        assert len(h.samples)==1
        # A future stamp is not a validated observation either.
        emit(h.node.get_clock().now().nanoseconds-stamp+10**10)
        h.spin_for(0.15)
        assert len(h.samples)==1
        emit(h.node.get_clock().now().nanoseconds-stamp)
        h.spin_until(lambda:len(h.samples)==2,3)
        h.spin_for(0.9)
        assert len(h.samples)==2
        assert h.health[-1]['status']!='HEALTHY'


@pytest.mark.parametrize('sig',[signal.SIGINT,signal.SIGTERM])
def test_signal_shutdown_during_motion(sig):
    with Harness('signal-'+str(sig),motion=True) as h:
        h.ready()
        assert h.request().success
        p=h.processes['sayHello']
        p.send_signal(sig)
        assert p.wait(timeout=5)==0
        h.spin_for(0.8)
        assert h.processes['telemetry'].poll() is None


@pytest.mark.parametrize('key,value',[('backend','gdk'),('backend','unknown'),('duration','-1.0'),
    ('displacement','0.5'),('target_joint','NOT_A_JOINT'),('publish_hz','0.0')])
def test_invalid_startup_and_unavailable_gdk_fail_closed(key,value,tmp_path):
    p=subprocess.run([str(BIN/'sayHello'),'--ros-args','-p',key+':='+value],
                     capture_output=True,text=True,timeout=5)
    (tmp_path/'startup.log').write_text(p.stdout+p.stderr)
    assert p.returncode!=0


def test_python_gdk_dependency_guard_never_falls_back(tmp_path):
    # Importing the optional adapter does not import/connect SDK. Explicit gdk
    # startup must fail without a verified, authorized deployment configuration.
    p=subprocess.run([str(BIN/'sayHello'),'--ros-args','-p','backend:=gdk',
                      '-p','sdk_config_path:="/definitely_missing_gdk_config.json"'],
                     capture_output=True,text=True,timeout=8)
    (tmp_path/'gdk-python-guard.log').write_text(p.stdout+p.stderr)
    assert p.returncode!=0
    assert 'GDK' in p.stdout+p.stderr
    assert '"source": "mock"' not in p.stdout+p.stderr
    assert 'SUCCEEDED' not in p.stdout+p.stderr


def test_python_install_metadata_has_two_console_scripts():
    from importlib.metadata import distribution
    dist=distribution('agibot_g2_demo')
    entries={entry.name:entry.value for entry in dist.entry_points if entry.group=='console_scripts'}
    assert entries=={'sayHello':'agibot_g2_demo.say_hello_node:main',
                     'telemetry':'agibot_g2_demo.telemetry_node:main'}
    share=Path(get_package_prefix('agibot_g2_demo'))/'share'/'agibot_g2_demo'
    assert (share/'launch'/'demo.launch.py').is_file()
    assert (share/'config'/'mock.yaml').is_file()
    assert '<build_type>ament_python</build_type>' in (share/'package.xml').read_text()


@pytest.mark.parametrize('executable',['sayHello','telemetry'])
def test_simulated_ros_clock_is_explicitly_rejected(executable,tmp_path):
    result=subprocess.run([str(BIN/executable),'--ros-args','-p','use_sim_time:=true'],
                          capture_output=True,text=True,timeout=6)
    (tmp_path/'clock-rejection.log').write_text(result.stdout+result.stderr)
    assert result.returncode==2
    assert 'use_sim_time=false' in result.stdout+result.stderr


def test_ros_parameters_cannot_enable_motion_or_switch_clock():
    with Harness('immutable-parameters') as h:
        h.ready()
        for executable,key in [('sayHello','enable_motion'),('sayHello','use_sim_time'),
                               ('telemetry','use_sim_time')]:
            client=h.node.create_client(SetParameters,h.ns+'/'+executable+'/set_parameters')
            h.spin_until(client.service_is_ready,3)
            request=SetParameters.Request(parameters=[Parameter(name=key,
                value=ParameterValue(type=ParameterType.PARAMETER_BOOL,bool_value=True))])
            future=client.call_async(request)
            h.spin_until(future.done,3)
            assert future.exception() is None
            assert not future.result().results[0].successful, (executable,key)
            h.node.destroy_client(client)
        assert not h.request().success
        assert not any(state['state']=='RUNNING' for state in h.states)


def test_partial_harness_startup_cleans_first_process(monkeypatch):
    actual=subprocess.Popen
    children=[]
    def fail_second(args,**kwargs):
        if str(args[0]).endswith('/telemetry'):
            raise OSError('injected second executable launch failure')
        child=actual(args,**kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(subprocess,'Popen',fail_second)
    with pytest.raises(OSError,match='injected second'):
        Harness('partial-start')
    assert children and all(child.poll() is not None for child in children)
    assert not ACTIVE


def test_runner_sigterm_cleans_child_sessions(tmp_path):
    log=(tmp_path/'runner.log').open('w')
    runner=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),
        '--hold-for-termination','--output',str(tmp_path)],stdout=log,stderr=subprocess.STDOUT)
    children=[]
    try:
        ready=tmp_path/'runner-ready.json'
        deadline=time.monotonic()+20
        while not ready.exists() and time.monotonic()<deadline:
            assert runner.poll() is None, (tmp_path/'runner.log').read_text()
            time.sleep(0.05)
        assert ready.exists()
        children=json.loads(ready.read_text())['pids']
        runner.terminate()
        assert runner.wait(timeout=15)==143
        for pid in children:
            with pytest.raises(ProcessLookupError):
                os.kill(pid,0)
    finally:
        if runner.poll() is None:
            runner.terminate()
            try:
                runner.wait(timeout=15)
            except subprocess.TimeoutExpired:
                runner.kill()
                runner.wait(timeout=3)
        for pid in children:
            try:
                os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
        log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--hold-for-termination',action='store_true')
    parser.add_argument('--output',default=str(BASE))
    args=parser.parse_args()
    rclpy.init()
    signal.signal(signal.SIGTERM,terminate_runner)
    try:
        if args.hold_for_termination:
            with Harness('termination',out=args.output) as harness:
                harness.ready()
                (Path(args.output)/'runner-ready.json').write_text(
                    json.dumps({'pids':[p.pid for p in harness.processes.values()]}))
                harness.spin_until(lambda:False,60)
        else:
            with Harness('clean-e2e',motion=True,namespace='/g2',out=args.output) as harness:
                print(json.dumps(success_path(harness),indent=2))
    finally:
        rclpy.shutdown()
