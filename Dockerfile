FROM nvidia/cuda:12.3.1-runtime-ubuntu22.04

# Install Python and its venv module
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv git && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Code-Server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Set a standard working directory inside the container for your application files
WORKDIR /app

# Copy your local application files into the image during the BUILD phase
# (Assuming requirements.txt and start.sh are in the same local folder as your Dockerfile)
COPY requirements.txt .
COPY start.sh .

# Install your python requirements during the BUILD phase
# Use the correct 'python3' command and path to the venv
RUN python3 -m venv venv
RUN /app/venv/bin/pip install --ignore-installed -r requirements.txt

# Expose ports for Ollama (11434) and Code-Server (7777)
EXPOSE 11434 7777

# Define the command that runs when the container is started
CMD ["./start.sh"]