FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && curl -fsSL https://code-server.dev/install.sh | sh

WORKDIR /workspace/mvp

COPY requirements.txt .

RUN python3 -m venv .venv

ENV PATH="/workspace/mvp/.venv/bin:$PATH"

RUN pip install --ignore-installed -r requirements.txt

EXPOSE 11434 7777 8050 8000

CMD ["./start.sh"]