FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Enable unbuffered Python output for better logging
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /runpod-volume

# Clone ComfyUI to the persistent volume location
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    echo "ComfyUI cloned successfully"

# Create necessary directories
RUN mkdir -p /runpod-volume/image_cache && \
    mkdir -p /runpod-volume/outputs && \
    chmod -R 777 /runpod-volume

# Copy requirements first for better Docker layer caching
COPY requirements_runpod.txt /tmp/requirements_runpod.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements_runpod.txt

# Copy application files to ComfyUI directory
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Set ComfyUI as working directory
WORKDIR /runpod-volume/ComfyUI

# Install ComfyUI dependencies
RUN pip install -r requirements.txt

# Set handler environment variables
ENV RUNPOD_HANDLER_PATH="/runpod-volume/ComfyUI/realism.py"
ENV RUNPOD_HANDLER_NAME="runpod_handler"

# Test the setup
RUN python -c "import sys; sys.path.append('/runpod-volume/ComfyUI'); print('Python path:', sys.path); import torch; print('CUDA available:', torch.cuda.is_available()); print('Testing imports...'); import boto3; print('Boto3 imported successfully')"