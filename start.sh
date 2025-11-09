#!/bin/bash
echo "--- Running initial setup configuration ---"

curl -fsSL https://ollama.com/install.sh | sh

pkill ollama

git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

mkdir -p /root/.ssh/
cp -r /workspace/.ssh/* /root/.ssh/
chmod 600 /root/.ssh/*

python -m ensurepip --upgrade

pip install -r requirements.txt

echo "--- Configuration complete ---"
