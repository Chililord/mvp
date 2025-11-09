#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

echo "--- Running initial setup configuration ---"

# 1. Configure Git
git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

# 2. Setup SSH keys (ensure your .ssh folder is copied into the image/workspace via your RunPod config)
# NOTE: The user running this script must have permission to write to /root/.ssh/
# If you are using RunPod's standard configuration, the /workspace directory is common.
mkdir -p /root/.ssh/
cp -r .ssh/* /root/.ssh/
chmod 600 /root/.ssh/*
echo "--- Configuration complete ---"

# 3. Keep the container running in an interactive bash session
echo "Starting interactive session. The container will remain active."
# Use 'exec' to replace the current script process with bash
exec /bin/bash
