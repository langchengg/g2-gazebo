#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /opt/sim_vendor/install/setup.bash
source /opt/demo/install/setup.bash
set -u
exec "$@"
