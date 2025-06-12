# Use RunPod's PyTorch base image with CUDA support
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    unzip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Copy requirements first for better Docker layer caching
COPY requirements.txt /workspace/

# Install Python dependencies with explicit order
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pillow>=10.0.0 && \
    pip install --no-cache-dir -r requirements.txt

# Use ComfyUI from network volume (not copied into container)
# Your existing ComfyUI setup will be mounted at /runpod-volume/ComfyUI/

# Set paths to use network volume
ENV COMFYUI_PATH="/runpod-volume/ComfyUI"
ENV PATH="/runpod-volume/ComfyUI/venv/bin:$PATH"
ENV VIRTUAL_ENV="/runpod-volume/ComfyUI/venv"

# Copy your application files
COPY realism.py /workspace/
COPY handler.py /workspace/

# Set working directory
WORKDIR /workspace

# Expose port (optional, for debugging)
EXPOSE 8000

# Set the handler as the entry point
CMD ["python", "-u", "handler.py"]
