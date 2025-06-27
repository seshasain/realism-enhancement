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
    mkdir -p /runpod-volume/logs && \
    chmod -R 777 /runpod-volume

# Install Python dependencies for our application
RUN pip install --upgrade pip && \
    pip install boto3>=1.28.0 && \
    pip install pillow>=9.0.0 && \
    pip install requests>=2.28.0 && \
    # Install specific NumPy version that works with PyTorch 2.1.0
    pip install numpy==1.24.1 --force-reinstall && \
    pip install tqdm>=4.64.0 && \
    pip install runpod>=1.5.0 && \
    pip install python-json-logger>=2.0.0 && \
    echo "RunPod SDK installed successfully"

# Set ComfyUI as working directory
WORKDIR /runpod-volume/ComfyUI

# Cache bust to force fresh installation - Update this timestamp to force rebuild
RUN echo "Build timestamp: 2025-06-29-10:00:00-PYTORCH-2.1.0-NUMPY-1.24.1-FIX"

# Use existing venv if available, otherwise install ComfyUI dependencies
RUN if [ -d "venv" ]; then \
        echo "✅ Using existing venv with pre-installed requirements"; \
        echo "Installing RunPod SDK and boto3 in venv..."; \
        venv/bin/pip install --no-cache-dir runpod>=1.5.0 boto3>=1.28.0 numpy==1.24.1 python-json-logger>=2.0.0; \
        echo "✅ RunPod SDK installation completed"; \
    else \
        echo "Installing ComfyUI dependencies"; \
        pip install --no-cache-dir -r requirements.txt runpod>=1.5.0 boto3>=1.28.0 numpy==1.24.1 python-json-logger>=2.0.0; \
    fi

# Verify RunPod SDK installation (using venv if available)
RUN if [ -d "venv" ]; then \
        echo "Verifying RunPod SDK in venv..."; \
        venv/bin/python -c "import runpod; print('✅ RunPod SDK version:', runpod.__version__)" && \
        venv/bin/python -c "import runpod.serverless; print('✅ RunPod serverless module available')"; \
    else \
        echo "Verifying RunPod SDK in system Python..."; \
        python -c "import runpod; print('✅ RunPod SDK version:', runpod.__version__)" && \
        python -c "import runpod.serverless; print('✅ RunPod serverless module available')"; \
    fi

# Create fallback images directory
RUN mkdir -p /runpod-volume/ComfyUI/fallback_images

# Copy application files from git repo to ComfyUI directory
# RunPod clones your repo to the container, then we copy files to the right location
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Clean up any old handler files that might conflict AFTER copying our files
RUN rm -f /runpod-volume/ComfyUI/handler.py /runpod-volume/ComfyUI/__pycache__/handler.* || true

# Ensure realism.py is used as the handler by creating a symlink
RUN ln -sf /runpod-volume/ComfyUI/realism.py /runpod-volume/ComfyUI/handler.py

# Set handler environment variables
ENV RUNPOD_HANDLER_PATH="/runpod-volume/ComfyUI/realism.py"
ENV RUNPOD_HANDLER_NAME="runpod_handler"
ENV RUNPOD_LOG_LEVEL="DEBUG"

# Test the setup and verify handler exists
RUN python -c "import sys; sys.path.append('/runpod-volume/ComfyUI'); print('Python path:', sys.path); import torch; print('CUDA available:', torch.cuda.is_available()); print('Testing imports...'); import boto3; print('Boto3 imported successfully'); import numpy; print('NumPy version:', numpy.__version__)"

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
    echo "RUNPOD_LOG_LEVEL=$RUNPOD_LOG_LEVEL" && \
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

# Install logrotate
RUN apt-get update && apt-get install -y logrotate && \
    echo "/runpod-volume/logs/*.log {\n  rotate 5\n  daily\n  compress\n  missingok\n  notifempty\n  create 0644 root root\n}" > /etc/logrotate.d/runpod-logs && \
    chmod 644 /etc/logrotate.d/runpod-logs

# Create startup script with comprehensive logging
RUN echo '#!/bin/bash' > /start_handler.sh && \
    echo 'echo "=== RUNPOD CONTAINER STARTUP ==="' >> /start_handler.sh && \
    echo 'echo "Current time: $(date)"' >> /start_handler.sh && \
    echo 'echo "Working directory: $(pwd)"' >> /start_handler.sh && \
    echo 'echo "Environment variables:"' >> /start_handler.sh && \
    echo 'echo "  RUNPOD_HANDLER_PATH=$RUNPOD_HANDLER_PATH"' >> /start_handler.sh && \
    echo 'echo "  RUNPOD_HANDLER_NAME=$RUNPOD_HANDLER_NAME"' >> /start_handler.sh && \
    echo 'echo "  RUNPOD_LOG_LEVEL=$RUNPOD_LOG_LEVEL"' >> /start_handler.sh && \
    echo 'echo "Directory structure:"' >> /start_handler.sh && \
    echo 'ls -la /runpod-volume/ComfyUI/' >> /start_handler.sh && \
    echo 'echo "Handler file verification:"' >> /start_handler.sh && \
    echo 'ls -la /runpod-volume/ComfyUI/realism.py' >> /start_handler.sh && \
    echo 'echo "Python import test:"' >> /start_handler.sh && \
    echo 'cd /runpod-volume/ComfyUI && python -c "import realism; print(\"✅ Handler imported:\", hasattr(realism, \"runpod_handler\"))"' >> /start_handler.sh && \
    echo 'echo "NumPy version check:"' >> /start_handler.sh && \
    echo 'python -c "import numpy; print(\"NumPy version:\", numpy.__version__)"' >> /start_handler.sh && \
    echo 'echo "Torch version check:"' >> /start_handler.sh && \
    echo 'python -c "import torch; print(\"Torch version:\", torch.__version__); print(\"CUDA available:\", torch.cuda.is_available())"' >> /start_handler.sh && \
    echo 'echo "Setting up log directory:"' >> /start_handler.sh && \
    echo 'mkdir -p /runpod-volume/logs' >> /start_handler.sh && \
    echo 'LOG_FILE="/runpod-volume/logs/runpod-$(date +%Y%m%d-%H%M%S).log"' >> /start_handler.sh && \
    echo 'echo "Logs will be written to $LOG_FILE"' >> /start_handler.sh && \
    echo 'echo "=== STARTING RUNPOD SERVERLESS ==="' >> /start_handler.sh && \
    echo 'cd /runpod-volume/ComfyUI' >> /start_handler.sh && \
    echo 'if [ -d "venv" ]; then' >> /start_handler.sh && \
    echo '  echo "✅ Activating existing venv"' >> /start_handler.sh && \
    echo '  source venv/bin/activate' >> /start_handler.sh && \
    echo '  PYTHON_CMD="venv/bin/python"' >> /start_handler.sh && \
    echo 'else' >> /start_handler.sh && \
    echo '  echo "⚠️ No venv found, using system Python"' >> /start_handler.sh && \
    echo '  PYTHON_CMD="python"' >> /start_handler.sh && \
    echo 'fi' >> /start_handler.sh && \
    echo 'echo "Verifying RunPod SDK..."' >> /start_handler.sh && \
    echo '$PYTHON_CMD -c "import runpod; print(\"RunPod version:\", runpod.__version__)"' >> /start_handler.sh && \
    echo 'echo "Starting serverless handler with direct import..."' >> /start_handler.sh && \
    echo '$PYTHON_CMD -c "import sys; sys.path.append(\"/runpod-volume/ComfyUI\"); import runpod; from realism import runpod_handler; print(\"Handler imported successfully\"); runpod.serverless.start({\"handler\": runpod_handler})" 2>&1 | tee -a $LOG_FILE' >> /start_handler.sh && \
    chmod +x /start_handler.sh

# Start with comprehensive logging
CMD ["/start_handler.sh"]