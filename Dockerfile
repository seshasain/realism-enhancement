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

# Install base dependencies first
RUN pip install --upgrade pip && \
    pip install boto3>=1.28.0 && \
    pip install pillow>=9.0.0 && \
    pip install requests>=2.28.0 && \
    pip install tqdm>=4.64.0 && \
    pip install runpod>=1.5.0 && \
    echo "RunPod SDK installed successfully"

# Set ComfyUI as working directory
WORKDIR /runpod-volume/ComfyUI

# Add a build timestamp for versioning
RUN echo "Build timestamp: 2025-07-07-FIXED-NUMPY-DEPENDENCY"

# Use existing venv if available, otherwise install ComfyUI dependencies
RUN if [ -d "venv" ]; then \
        echo "✅ Using existing venv with pre-installed requirements"; \
        echo "Installing RunPod SDK and boto3 in venv..."; \
        venv/bin/pip install --no-cache-dir runpod>=1.5.0 boto3>=1.28.0; \
        venv/bin/pip install --no-cache-dir numpy==1.24.0 --force-reinstall; \
        echo "✅ RunPod SDK installation completed"; \
    else \
        echo "Installing ComfyUI dependencies"; \
        # First install everything except numpy from requirements.txt
        grep -v "numpy" requirements.txt > requirements_no_numpy.txt; \
        pip install --no-cache-dir -r requirements_no_numpy.txt; \
        # Then force install numpy 1.24.0
        pip install --no-cache-dir numpy==1.24.0 --force-reinstall; \
    fi

# Verify numpy version
RUN python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"

# Create custom_nodes directory
RUN mkdir -p custom_nodes

# Create input and output directories
RUN mkdir -p input output

# Copy handler script
COPY realism.py /runpod-volume/realism.py

# Copy B2 config
COPY b2_config.py /runpod-volume/b2_config.py

# Create fallback images directory
RUN mkdir -p /runpod-volume/fallback_images

# Copy test scripts
COPY test_worker.py /runpod-volume/test_worker.py
COPY test_handler.py /runpod-volume/test_handler.py
COPY runpod_diagnostics.py /runpod-volume/runpod_diagnostics.py

# Make scripts executable
RUN chmod +x /runpod-volume/*.py

# Setup entrypoint
COPY handler.py /runpod-volume/handler.py
RUN chmod +x /runpod-volume/handler.py

# Set working directory
WORKDIR /runpod-volume

# Add logging to the handler script to debug startup issues
RUN echo 'import os\nimport sys\nimport time\nimport logging\nlogging.basicConfig(level=logging.INFO)\nlogger = logging.getLogger("RunpodHandler")\n\nlogger.info("Starting Serverless Worker")\nlogger.info(f"Python version: {sys.version}")\nlogger.info(f"Current directory: {os.getcwd()}")\nlogger.info(f"Directory contents: {os.listdir()}")\n\ntry:\n    import numpy\n    logger.info(f"NumPy version: {numpy.__version__}")\nexcept Exception as e:\n    logger.error(f"Failed to import NumPy: {e}")\n\ntry:\n    import torch\n    logger.info(f"PyTorch version: {torch.__version__}")\n    logger.info(f"CUDA available: {torch.cuda.is_available()}")\nexcept Exception as e:\n    logger.error(f"Failed to import torch: {e}")\n\ntry:\n    from realism import runpod_handler\n    logger.info("Successfully imported handler")\nexcept Exception as e:\n    logger.error(f"Failed to import handler: {e}")\n    import traceback\n    logger.error(traceback.format_exc())\n\nimport runpod\nlogger.info("Starting runpod.serverless.start with handler")\nrunpod.serverless.start({"handler": runpod_handler})' > /runpod-volume/handler.py

# Set the entrypoint
ENTRYPOINT ["python", "-u", "/runpod-volume/handler.py"]