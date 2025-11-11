#!/bin/bash
echo "--- Running initial setup configuration ---"


git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

mkdir -p /root/.ssh/
cp -r /workspace/.ssh/* /root/.ssh/
chmod 600 /root/.ssh/*

echo "--- Configuration complete ---"

