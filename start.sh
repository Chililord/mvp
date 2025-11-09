#!/bin/bash
set -e

# ... (VRAM/ENV VARS need to be set using 'export' at the very top of your script) ...
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_MAX_VRAM=0 
# ... (etc) ...

# Function to wait for Ollama server readiness (required here)
wait_for_ollama() {
    echo "Waiting for Ollama server to be ready..."
    until curl -s http://localhost:11434 > /dev/null; do
        sleep 0.5
    done
    echo "Ollama server is ready."
}

# --- 4. Ollama Model Import Automation (Persistent to /workspace) ---
# FIX: Use absolute path (start with /)
GGUF_SOURCE_PATH="/workspace/phi3_quantized_model/Phi-3-mini-4k-instruct-q4.gguf" 
MODEL_NAME="local-phi3-quantized"
MODEL_FILE="/tmp/Modelfile_local"

echo "FROM $GGUF_SOURCE_PATH" > "$MODEL_FILE"
echo "Importing GGUF model into Ollama registry..."

# Start temporary server in the background
/usr/local/bin/ollama serve > /var/log/ollama_import.log 2>&1 &
wait_for_ollama

# FIX: Run create command and WAIT for it to complete
ollama create "$MODEL_NAME" -f "$MODEL_FILE"
echo "Model import complete and saved to disk."

# Kill the temporary server process
pkill ollama
sleep 2 # Give it a moment to shut down cleanly

# --- 5. Start Services ---
# ... (Code server startup) ...

echo "Starting final Ollama server in foreground..."
# Start final server. It now knows about 'local-phi3-quantized' from the database.
exec /usr/local/bin/ollama serve
