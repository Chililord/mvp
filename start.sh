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

# --- Configure Code-Server Settings (Dark Mode) ---
CONFIG_DIR="/root/.config/code-server"
SETTINGS_FILE="$CONFIG_DIR/settings.json" 

mkdir -p "$CONFIG_DIR"

# Create/overwrite the settings file with JSON configuration for dark mode and trust
cat <<EOF > "$SETTINGS_FILE"
{
  "workbench.colorTheme": "Default Dark+",
  "security.workspace.trust.startupPrompt": "never",
  "security.workspace.trust.enabled": false
}
EOF

# Run code server
exec /usr/bin/code-server --bind-addr 0.0.0.0 --port 7777 --auth none .
