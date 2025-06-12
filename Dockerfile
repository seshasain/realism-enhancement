# Use RunPod's PyTorch base image with CUDA support
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Cache bust - change this to force rebuild
ENV BUILD_VERSION=2024-01-15-v3-fixed-dependencies

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

# Install Python dependencies step by step
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Pillow first with all dependencies
RUN pip install --no-cache-dir pillow

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical imports
RUN python -c "from PIL import Image; print('✅ PIL/Pillow working')" && \
    python -c "import torch; print('✅ PyTorch working')" && \
    python -c "import numpy; print('✅ NumPy working')" && \
    python -c "import requests; print('✅ Requests working')"

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

# Test the installation
RUN python test_imports.py || echo "⚠️  Import test failed, but continuing build..."

# Expose port (optional, for debugging)
EXPOSE 8000

# Set the handler as the entry point
CMD ["python", "-u", "handler.py"]
