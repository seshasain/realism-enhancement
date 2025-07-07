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
    pip install numpy>=1.22.0 && \
    pip install tqdm>=4.64.0 && \
    pip install runpod>=1.5.0 && \
    echo "RunPod SDK installed successfully"

# Set ComfyUI as working directory
WORKDIR /runpod-volume/ComfyUI

# Cache bust to force fresh installation - Update this timestamp to force rebuild
RUN echo "Build timestamp: 2025-07-07-DETAILED-LOGGING"

# Use existing venv if available, otherwise install ComfyUI dependencies
RUN if [ -d "venv" ]; then \
        echo "✅ Using existing venv with pre-installed requirements"; \
        echo "Installing RunPod SDK and boto3 in venv..."; \
        venv/bin/pip install --no-cache-dir runpod>=1.5.0 boto3>=1.28.0; \
        echo "✅ RunPod SDK installation completed"; \
    else \
        echo "Installing ComfyUI dependencies"; \
        pip install --no-cache-dir -r requirements.txt runpod>=1.5.0 boto3>=1.28.0; \
    fi

# Create custom_nodes directory
RUN mkdir -p custom_nodes

# Create input and output directories
RUN mkdir -p input output

# Copy application files
COPY realism.py /runpod-volume/
COPY b2_config.py /runpod-volume/

# Also copy to ComfyUI directory for backward compatibility
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Create fallback images directory
RUN mkdir -p /runpod-volume/fallback_images

# Copy handler and test scripts
COPY handler.py /runpod-volume/handler.py
COPY test_import.py /runpod-volume/test_import.py
RUN chmod +x /runpod-volume/*.py

# Set working directory back to root
WORKDIR /runpod-volume

# Run the import test to verify handler can be imported
RUN python -u test_import.py

# Create a startup script with detailed logging
RUN echo '#!/bin/bash' > /start_handler.sh && \
    echo 'echo "=== RUNPOD CONTAINER STARTUP ===" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'echo "Current time: $(date)" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'echo "Working directory: $(pwd)" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'echo "Directory structure:" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'ls -la /runpod-volume/ | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'echo "Python version:" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'python --version | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'echo "Running import test first:" | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'python -u test_import.py | tee -a /runpod-volume/logs/import_test.log' >> /start_handler.sh && \
    echo 'echo "Starting handler script with full logging..." | tee -a /runpod-volume/logs/startup.log' >> /start_handler.sh && \
    echo 'exec python -u /runpod-volume/handler.py 2>&1 | tee -a /runpod-volume/logs/handler.log' >> /start_handler.sh && \
    chmod +x /start_handler.sh

# Start with comprehensive logging
CMD ["/start_handler.sh"]