FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Clone ComfyUI
RUN mkdir -p /runpod-volume && \
    cd /runpod-volume && \
    git clone https://github.com/comfyanonymous/ComfyUI.git

# Copy your project files
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Install dependencies
RUN pip install boto3

# Set handler location
ENV RUNPOD_HANDLER_PATH="/runpod-volume/ComfyUI/realism.py"
ENV RUNPOD_HANDLER_NAME="runpod_handler"

WORKDIR /runpod-volume/ComfyUI