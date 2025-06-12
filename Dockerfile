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

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire ComfyUI setup (models, venv, everything)
COPY ComfyUI/ /workspace/ComfyUI/

# Activate the virtual environment
ENV PATH="/workspace/ComfyUI/venv/bin:$PATH"
ENV VIRTUAL_ENV="/workspace/ComfyUI/venv"

# Copy your application files
COPY realism.py /workspace/
COPY handler.py /workspace/

# Set working directory
WORKDIR /workspace

# Expose port (optional, for debugging)
EXPOSE 8000

# Set the handler as the entry point
CMD ["python", "-u", "handler.py"]
