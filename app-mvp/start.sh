#!/bin/bash
set -e

# Function to wait for Ollama server readiness
wait_for_ollama() {
    echo "Waiting for Ollama server to be ready..."
    until curl -s http://localhost:11434 > /dev/null; do
        sleep 0.5
    done
    echo "Ollama server is ready."
}

# --- 1. System Dependencies & Software Installation ---
echo "Installing system dependencies and Code Server..."
apt-get update && apt-get install -y curl bash python3 python3-pip
curl -fsSL https://code-server.dev/install.sh | sh


# --- 2. Python Environment Setup (Persistent to /workspace) ---
VENV_DIR="/workspace/.venv"
# List your required packages directly here or use a requirements.txt file
PYTHON_PACKAGES="fastapi loguru pydantic uvicorn ollama"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Installing dependencies to workspace..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install $PYTHON_PACKAGES --no-cache-dir --break-system-packages
else
    source "$VENV_DIR/bin/activate"
    echo "Virtual environment already exists. Activating it."
fi


# --- 3. SSH Key Setup Automation (Persistent to /workspace) ---
SSH_WORKSPACE_DIR="/workspace/.ssh"
SSH_ROOT_DIR="/root/.ssh"
echo "Setting up SSH keys from workspace to root..."
mkdir -p "$SSH_ROOT_DIR"
chmod 700 "$SSH_ROOT_DIR"
# Copy keys and set restrictive permissions for git access
cp -r "$SSH_WORKSPACE_DIR"/* "$SSH_ROOT_DIR/" 2>/dev/null || true
chmod 600 "$SSH_ROOT_DIR/id_rsa" 2>/dev/null || true
chmod 600 "$SSH_ROOT_DIR/id_ed25519" 2>/dev/null || true


# --- 4. Ollama Model Import Automation (Persistent to /workspace) ---
GGUF_SOURCE_PATH="/workspace/phi3_quantized_model/Phi-3-mini-4k-instruct-q4.gguf"
MODEL_NAME="local-phi3-quantized"
MODEL_FILE="/tmp/Modelfile_local"

# Create a temporary Modelfile that points to the physical GGUF file path
echo "FROM $GGUF_SOURCE_PATH" > "$MODEL_FILE"
echo "Importing GGUF model into Ollama registry..."

# Start the server temporarily in the background to run the 'create' command
/bin/ollama serve > /var/log/ollama_import.log 2>&1 &
wait_for_ollama

# Import the model
ollama create "$MODEL_NAME" -f "$MODEL_FILE"

# Kill the temporary import server process
pkill ollama
echo "Model import complete."


# --- 5. Start Services ---
echo "Starting Code Server in background..."
# Ensure Code Server uses the activated Python environment
code-server --bind-addr 0.0.0.0:8080 --auth none --disable-telemetry > /var/log/code-server.log 2>&1 &

echo "Starting final Ollama server in foreground..."
exec /bin/ollama serve
