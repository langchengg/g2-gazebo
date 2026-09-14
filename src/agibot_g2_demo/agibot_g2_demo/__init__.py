"""Project-owned Python ROS demo; importing the package does not load ROS or GDK."""

__version__ = '0.2.0'


def implementation_identity(node, backend, module_file):
    """Record the actual Python module/process, never an inferred implementation."""
    import json
    import os
    from pathlib import Path
    import platform
    import sys

    identity = {
        'implementation': 'python-rclpy', 'package_version': __version__,
        'node_name': node.get_name(), 'namespace': node.get_namespace(),
        'backend': backend, 'module_file': str(Path(module_file).resolve()),
        'module_loaded_file': str(module_file),
        'package_file': str(Path(__file__).resolve()),
        'package_loaded_file': __file__,
        'python_executable': sys.executable, 'python_version': platform.python_version(),
        'pid': os.getpid(), 'argv': sys.argv,
    }
    node.get_logger().info('IMPLEMENTATION_IDENTITY ' + json.dumps(identity, sort_keys=True))
    evidence = os.environ.get('EVIDENCE_DIR')
    if evidence:
        directory = Path(evidence)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f'identity-{node.get_name()}-{os.getpid()}.json').write_text(
            json.dumps(identity, indent=2) + '\n')
    return identity


def ros_main(node_class, args=None):
    """Use one executor and let both stop signals unwind backend cleanup."""
    import signal
    import sys
    import rclpy
    from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions

    class StopRequested(BaseException):
        pass

    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        if not stopping:
            stopping = True
            raise StopRequested()

    node = executor = None
    previous = {}
    result = 0
    try:
        rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, stop)
        node = node_class()
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except (StopRequested, KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception as error:
        print(f'{node_class.__name__} fatal: {error}', file=sys.stderr, flush=True)
        result = 2
    finally:
        # launch and a process-group shutdown can deliver the same stop twice.
        # Do not interrupt resource destruction with a second control exception.
        stopping = True
        if node is not None:
            try:
                node.close()
                simulation = getattr(node, 'sim', None)
                if executor is not None and hasattr(simulation, 'shutdown_pending'):
                    # This is outside callbacks. Bound cancellation even while
                    # /clock is paused; never wait on simulation time at exit.
                    import time
                    deadline = time.monotonic() + 2.0
                    while simulation.shutdown_pending() and time.monotonic() < deadline:
                        executor.spin_once(timeout_sec=0.05)
                    if simulation.shutdown_pending():
                        print('simulation goal cancellation not confirmed before shutdown deadline',
                              file=sys.stderr, flush=True)

            except Exception as error:
                print(f'backend cleanup failed: {error}', file=sys.stderr, flush=True)
                result = 2
        if executor is not None:
            executor.shutdown(timeout_sec=2.0)
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return result
