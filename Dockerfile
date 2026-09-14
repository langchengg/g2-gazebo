ARG ROS_BASE=ros:humble-ros-base-jammy@sha256:75dd3aba34a3838dadbb31a9f7bef769bdfa8713e6cec686fc868db2981b0987
FROM ${ROS_BASE} AS dependencies
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions python3-pytest python3-setuptools \
    ros-humble-rclpy ros-humble-ament-index-python \
    ros-humble-rcl-interfaces ros-humble-sensor-msgs ros-humble-std-msgs \
    ros-humble-std-srvs ros-humble-launch-ros \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/demo

FROM dependencies AS runtime
COPY src/ src/
COPY docker/ docker/
COPY scripts/ scripts/
COPY model_sources/ model_sources/
COPY Dockerfile Dockerfile.sim compose.sim.yaml compose.yaml Makefile .dockerignore ./
RUN python3 scripts/source_manifest.py --root /opt/demo --scope runtime --output /opt/demo/source-manifest.json && \
    source /opt/ros/humble/setup.bash && \
    colcon build --packages-skip agibot_g2_visual_tools --event-handlers console_direct+ && \
    source install/setup.bash && \
    python3 scripts/check_install.py
RUN chmod +x docker/entrypoint.sh scripts/*.sh
ENV ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=42 PYTHONUNBUFFERED=1
STOPSIGNAL SIGINT
ENTRYPOINT ["/opt/demo/docker/entrypoint.sh"]
CMD ["ros2", "launch", "agibot_g2_demo", "demo.launch.py"]
