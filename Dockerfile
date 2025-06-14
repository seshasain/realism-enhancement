FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Enable unbuffered Python output for better logging
ENV PYTHONUNBUFFERED=1

# Clone ComfyUI
RUN mkdir -p /runpod-volume && \
    cd /runpod-volume && \
    git clone https://github.com/comfyanonymous/ComfyUI.git && \
    echo "ComfyUI cloned successfully"

# List directories to verify
RUN ls -la /runpod-volume && \
    ls -la /runpod-volume/ComfyUI

# Create directories for images and outputs
RUN mkdir -p /runpod-volume/image_cache && \
    mkdir -p /runpod-volume/outputs && \
    chmod -R 777 /runpod-volume

# Copy your project files
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Install dependencies
RUN pip install boto3 && \
    pip install --upgrade pip && \
    pip install requests

# Set handler location
ENV RUNPOD_HANDLER_PATH="/runpod-volume/ComfyUI/realism.py"
ENV RUNPOD_HANDLER_NAME="runpod_handler"

# Set working directory
WORKDIR /runpod-volume/ComfyUI

# Test import to verify setup
RUN python -c "import sys; sys.path.append('/runpod-volume/ComfyUI'); print('Python path:', sys.path); import torch; print('CUDA available:', torch.cuda.is_available()); print('Done testing imports')"