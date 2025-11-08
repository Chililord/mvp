# Start with a robust NVIDIA PyTorch base image which has CUDA pre-installed.
FROM nvcr.io/nvidia/pytorch:23.10-py3

# Set working directory to /app
WORKDIR /app

# Copy requirements file first to leverage Docker caching
COPY requirements.txt ./

# Install dependencies using pip system-wide
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code and start script
COPY src/ ./src/

# Expose the port your FastAPI app runs on
EXPOSE 8000

# Run the start script as the default 'root' user
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
