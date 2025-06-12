# Use RunPod's PyTorch base image with CUDA support
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Cache bust - change this to force rebuild
ENV BUILD_VERSION=2024-01-15-v10-runtime-install-with-debug

# Install system dependencies including image libraries
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    unzip \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    python3-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Copy requirements first for better Docker layer caching
COPY requirements.txt /workspace/

# Install minimal dependencies in container (fallback only)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir runpod requests

# Install packages that will be used at runtime
RUN pip install --no-cache-dir pillow numpy torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Use ComfyUI from network volume (not copied into container)
# Your existing ComfyUI setup will be mounted at /runpod-volume/ComfyUI/

# Set paths to use network volume
ENV COMFYUI_PATH="/runpod-volume/ComfyUI"
ENV PATH="/runpod-volume/ComfyUI/venv/bin:$PATH"
ENV VIRTUAL_ENV="/runpod-volume/ComfyUI/venv"

# Copy your application files
COPY realism.py /workspace/
COPY handler.py /workspace/
COPY test_imports.py /workspace/

# Set working directory
WORKDIR /workspace

# Note: Import tests will run at runtime when ComfyUI venv is available

# Expose port (optional, for debugging)
EXPOSE 8000

# Set the handler as the entry point
CMD ["python", "-u", "handler.py"]
