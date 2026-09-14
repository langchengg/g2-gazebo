#!/usr/bin/env bash
set -eo pipefail
# ROS setup scripts reference unset variables; enable nounset after sourcing.
source /opt/ros/humble/setup.bash
source /opt/demo/install/setup.bash
set -u
exec "$@"
