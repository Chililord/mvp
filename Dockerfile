FROM python:3.13.7-slim-bookworm AS builder

WORKDIR /workspace

RUN apt-get update && apt-get install -y git curl openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Convenience for developer, the actual expose is done through runpod template UI
# ollama, fastapi, code server
EXPOSE 11434, 8000, 7777

RUN curl -fsSL https://ollama.com/install.sh | sh

RUN curl -fsSL https://code-server.dev/install.sh | sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the start script and make it executable
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
