#!/bin/bash
echo "--- Running initial setup configuration ---"


git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

mkdir -p /root/.ssh/
cp -r /workspace/.ssh/* /root/.ssh/
chmod 600 /root/.ssh/*


# Keeps container running 2 for 1!
exec code-server --port 7777 --bind-addr 0.0.0.0 --auth none .

echo "--- Configuration complete ---"

