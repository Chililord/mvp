FROM nvidia/cuda:12.3.1-runtime-ubuntu22.04


RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /workspace/mvp

COPY requirements.txt .
COPY start.sh .

# Install your python requirements during the BUILD phase
RUN python -m venv venv
RUN /app/venv/bin/pip install --ignore-installed -r requirements.txt

CMD ["./start.sh"]