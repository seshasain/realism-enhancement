FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Enable unbuffered Python output for better logging
ENV PYTHONUNBUFFERED=1

# Set working directory to persistent volume
WORKDIR /runpod-volume

# Clone ComfyUI to the persistent volume location
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    echo "ComfyUI cloned successfully"

# Create necessary directories
RUN mkdir -p /runpod-volume/image_cache && \
    mkdir -p /runpod-volume/outputs && \
    chmod -R 777 /runpod-volume

# Install Python dependencies for our application
RUN pip install --upgrade pip && \
    pip install boto3>=1.28.0 && \
    pip install pillow>=9.0.0 && \
    pip install requests>=2.28.0 && \
    pip install numpy>=1.22.0 && \
    pip install tqdm>=4.64.0 && \
    pip install runpod>=1.5.0 && \
    echo "RunPod SDK installed successfully"

# Set ComfyUI as working directory
WORKDIR /runpod-volume/ComfyUI

# Install ComfyUI dependencies
RUN pip install -r requirements.txt

# Verify RunPod SDK installation
RUN python -c "import runpod; print('✅ RunPod SDK version:', runpod.__version__)" && \
    python -c "import runpod.serverless; print('✅ RunPod serverless module available')"

# Copy application files from git repo to ComfyUI directory
# RunPod clones your repo to the container, then we copy files to the right location
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Set handler environment variables
ENV RUNPOD_HANDLER_PATH="/runpod-volume/ComfyUI/realism.py"
ENV RUNPOD_HANDLER_NAME="runpod_handler"

# Test the setup and verify handler exists
RUN python -c "import sys; sys.path.append('/runpod-volume/ComfyUI'); print('Python path:', sys.path); import torch; print('CUDA available:', torch.cuda.is_available()); print('Testing imports...'); import boto3; print('Boto3 imported successfully')"

# Comprehensive path and file verification
RUN echo "=== RUNPOD DEPLOYMENT VERIFICATION ===" && \
    echo "1. Directory structure:" && \
    ls -la /runpod-volume/ && \
    echo "" && \
    echo "2. ComfyUI directory contents:" && \
    ls -la /runpod-volume/ComfyUI/ && \
    echo "" && \
    echo "3. Application files verification:" && \
    ls -la /runpod-volume/ComfyUI/realism.py && \
    ls -la /runpod-volume/ComfyUI/b2_config.py && \
    echo "" && \
    echo "4. Environment variables:" && \
    echo "RUNPOD_HANDLER_PATH=$RUNPOD_HANDLER_PATH" && \
    echo "RUNPOD_HANDLER_NAME=$RUNPOD_HANDLER_NAME" && \
    echo "" && \
    echo "5. Python import test:" && \
    python -c "import sys; sys.path.append('/runpod-volume/ComfyUI'); import realism; print('✅ realism.py imported successfully'); print('✅ Handler function exists:', hasattr(realism, 'runpod_handler'))" && \
    echo "" && \
    echo "6. ComfyUI models directory:" && \
    ls -la /runpod-volume/ComfyUI/models/ || echo "⚠️ Models directory not found (will be created at runtime)" && \
    echo "" && \
    echo "7. Working directory verification:" && \
    pwd && \
    echo "=== VERIFICATION COMPLETE ==="

# Create startup script with comprehensive logging
RUN echo '#!/bin/bash' > /start_handler.sh && \
    echo 'echo "=== RUNPOD CONTAINER STARTUP ==="' >> /start_handler.sh && \
    echo 'echo "Current time: $(date)"' >> /start_handler.sh && \
    echo 'echo "Working directory: $(pwd)"' >> /start_handler.sh && \
    echo 'echo "Environment variables:"' >> /start_handler.sh && \
    echo 'echo "  RUNPOD_HANDLER_PATH=$RUNPOD_HANDLER_PATH"' >> /start_handler.sh && \
    echo 'echo "  RUNPOD_HANDLER_NAME=$RUNPOD_HANDLER_NAME"' >> /start_handler.sh && \
    echo 'echo "Directory structure:"' >> /start_handler.sh && \
    echo 'ls -la /runpod-volume/ComfyUI/' >> /start_handler.sh && \
    echo 'echo "Handler file verification:"' >> /start_handler.sh && \
    echo 'ls -la /runpod-volume/ComfyUI/realism.py' >> /start_handler.sh && \
    echo 'echo "Python import test:"' >> /start_handler.sh && \
    echo 'cd /runpod-volume/ComfyUI && python -c "import realism; print(\"✅ Handler imported:\", hasattr(realism, \"runpod_handler\"))"' >> /start_handler.sh && \
    echo 'echo "=== STARTING RUNPOD SERVERLESS ==="' >> /start_handler.sh && \
    echo 'cd /runpod-volume/ComfyUI' >> /start_handler.sh && \
    echo 'echo "Verifying RunPod SDK..."' >> /start_handler.sh && \
    echo 'python -c "import runpod; print(\"RunPod version:\", runpod.__version__)"' >> /start_handler.sh && \
    echo 'echo "Starting serverless handler..."' >> /start_handler.sh && \
    echo 'python -m runpod.serverless.start --rp_handler_name runpod_handler --rp_handler_file /runpod-volume/ComfyUI/realism.py' >> /start_handler.sh && \
    chmod +x /start_handler.sh

# Start with comprehensive logging
CMD ["/start_handler.sh"]