FROM python:3.13.7-slim-bookworm AS builder

WORKDIR /workdir/mvp

# Convenience for developer, the actual expose is done through runpod template UI
# ollama, fastapi, code server
EXPOSE 11434, 8000, 7777

RUN curl -fsSL https://ollama.com/install.sh | sh

RUN curl -fsSL https://code-server.dev/install.sh | sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["/bin/bash"]