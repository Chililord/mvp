#!/bin/bash
echo "--- Running initial setup configuration ---"

# So no bytecode when we run uvicorn or dash
source .env

git config --global user.email "noahdouglasgarner@gmail.com"
git config --global user.name "Noah Garner"

mkdir -p /root/.ssh/
cp -r /workspace/.ssh/* /root/.ssh/
chmod 600 /root/.ssh/*


export OLLAMA_HOST=0.0.0.0

# Start ollama
ollama serve &
# --- 2. Health Check Loop: Wait for Ollama to be ready ---
echo "Waiting for Ollama server to become available on port 11434..."

TIMEOUT=30  # Timeout after 30 seconds
until printf "" 2>>/dev/null >>/dev/tcp/localhost/11434; do
  ((TIMEOUT--))
  if [ $TIMEOUT -le 0 ]; then
    echo "Ollama server health check timed out. Exiting."
    exit 1
  fi
  sleep 1 # Wait for 1 second before checking again
done

echo "Ollama server is now available."

# --- 3. Import local GGUF model (Ollama is ready now) ---
GGUF_PATH="/workspace/phi3_quantized_model/Phi-3-mini-4k-instruct-q4.gguf"
MODEL_NAME="local-phi3-quantized"
echo "FROM $GGUF_PATH" > /tmp/Modelfile
ollama create $MODEL_NAME -f /tmp/Modelfile
rm /tmp/Modelfile

pkill ollama


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
