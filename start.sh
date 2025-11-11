#!/bin/bash
echo "--- Running initial setup configuration ---"


git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

mkdir -p /root/.ssh/
cp -r /workspace/.ssh/* /root/.ssh/
chmod 600 /root/.ssh/*


export OLLAMA_HOST=0.0.0.0

# Start ollama
ollama serve &

# Start fastapi
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload &

# Start the dash app
PYTHONDONTWRITEBYTECODE=1 python3 -m app_dash &

echo "--- Configuration complete ---"

# Start code-server, keep container alive
exec /usr/bin/code-server --bind-addr 0.0.0.0 --port 7777 --auth none .
