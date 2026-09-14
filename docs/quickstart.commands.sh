# Command checklist, not an unattended demo. Run one line at a time.
# Working directory is the extracted g2-gazebo folder.
sudo make doctor
sudo make fetch-model ACCEPT_MODEL_LICENSE=yes
sudo make prepare-model
sudo make build-sim
sudo make verify-sim

# Optional visible desktop mode
sudo make sim-doctor
sudo --preserve-env=DISPLAY,XAUTHORITY,XDG_SESSION_TYPE make demo-visual
sudo make ui-info
# Look at the Ubuntu desktop first; startup has not sent any motion.
sudo make sim-hello
sudo make telemetry
sudo make check-visual
# Wait for this run_id to reach SUCCEEDED before recording another explicit motion.
sudo make record-visual
sudo make ui-down
