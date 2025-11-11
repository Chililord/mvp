FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

RUN curl -fsSL https://code-server.dev/install.sh | sh

WORKDIR /app

COPY requirements.txt .
COPY start.sh .

COPY assets/ .
COPY component.py .
COPY callbacks.py .
COPY app_fastapi.py .
COPY app_dash.py .
COPY processor.py .

RUN pip install --ignore-installed -r requirements.txt

EXPOSE 11434 7777

CMD ["./start.sh"]