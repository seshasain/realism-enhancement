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
RUN echo "Build timestamp: 2025-06-29-11:00:00-PYTORCH-2.1.0-NUMPY-1.24.1-DEBUG"

# Modified installation approach to avoid dependency conflicts
RUN if [ -d "venv" ]; then \
        echo "✅ Using existing venv with pre-installed requirements"; \
        echo "Installing RunPod SDK and boto3 in venv..."; \
        venv/bin/pip install --no-cache-dir runpod>=1.5.0 boto3>=1.28.0 python-json-logger>=2.0.0; \
        venv/bin/pip install --no-cache-dir numpy==1.24.1 --force-reinstall; \
        echo "✅ RunPod SDK installation completed"; \
    else \
        echo "Installing ComfyUI dependencies"; \
        # First install requirements without the numpy constraint to avoid conflicts
        pip install --no-cache-dir -r requirements.txt; \
        # Then force reinstall our specific numpy version
        pip install --no-cache-dir numpy==1.24.1 --force-reinstall; \
        # Install additional dependencies
        pip install --no-cache-dir runpod>=1.5.0 boto3>=1.28.0 python-json-logger>=2.0.0; \
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

# Copy application files from git repo to ComfyUI directory
# RunPod clones your repo to the container, then we copy files to the right location
COPY realism.py /runpod-volume/ComfyUI/
COPY b2_config.py /runpod-volume/ComfyUI/

# Create fallback images directory and default image
RUN mkdir -p /runpod-volume/ComfyUI/fallback_images && \
    apt-get update && apt-get install -y imagemagick && \
    convert -size 512x512 xc:white -font Arial -pointsize 20 -fill black -gravity center \
    -draw "text 0,0 'Default Fallback Image'" \
    /runpod-volume/ComfyUI/fallback_images/default_fallback.jpg && \
    echo "Created default fallback image" && \
    # Also create a copy in the input directory
    mkdir -p /runpod-volume/ComfyUI/input && \
    cp /runpod-volume/ComfyUI/fallback_images/default_fallback.jpg /runpod-volume/ComfyUI/input/1023_mark.jpg && \
    echo "Copied default image as 1023_mark.jpg to input directory"

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
    echo '' >> /start_handler.sh && \
    echo '# Disable ComfyUI-Manager to avoid startup issues' >> /start_handler.sh && \
    echo 'if [ -d "/runpod-volume/ComfyUI/custom_nodes/ComfyUI-Manager" ]; then' >> /start_handler.sh && \
    echo '  echo "⚠️ Disabling ComfyUI-Manager to prevent startup issues"' >> /start_handler.sh && \
    echo '  mv /runpod-volume/ComfyUI/custom_nodes/ComfyUI-Manager /runpod-volume/ComfyUI/custom_nodes/ComfyUI-Manager.disabled || true' >> /start_handler.sh && \
    echo 'fi' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Create debug patch for B2 config to add more logging' >> /start_handler.sh && \
    echo 'cat > /runpod-volume/ComfyUI/b2_debug_patch.py << "EOF"' >> /start_handler.sh && \
    echo 'import logging' >> /start_handler.sh && \
    echo 'import sys' >> /start_handler.sh && \
    echo 'import os' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Set up detailed logging' >> /start_handler.sh && \
    echo 'logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")' >> /start_handler.sh && \
    echo 'logger = logging.getLogger("B2_DEBUG")' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Add file handler to log to a separate file' >> /start_handler.sh && \
    echo 'log_dir = "/runpod-volume/logs"' >> /start_handler.sh && \
    echo 'os.makedirs(log_dir, exist_ok=True)' >> /start_handler.sh && \
    echo 'file_handler = logging.FileHandler(f"{log_dir}/b2_debug.log")' >> /start_handler.sh && \
    echo 'file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))' >> /start_handler.sh && \
    echo 'logger.addHandler(file_handler)' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Monkey patch the b2_config.py functions to add more logging' >> /start_handler.sh && \
    echo 'import b2_config' >> /start_handler.sh && \
    echo 'original_download = b2_config.download_file_from_b2' >> /start_handler.sh && \
    echo 'original_get_config = b2_config.get_b2_config' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo 'def patched_download_file_from_b2(object_name, destination_path, max_retries=3, retry_delay=2):' >> /start_handler.sh && \
    echo '    logger.debug(f"DEBUG: Attempting to download {object_name} to {destination_path}")' >> /start_handler.sh && \
    echo '    try:' >> /start_handler.sh && \
    echo '        config = b2_config.get_b2_config()' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Using B2 config: {config}")' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Creating S3 client with endpoint {config[\"B2_ENDPOINT\"]}")' >> /start_handler.sh && \
    echo '        result = original_download(object_name, destination_path, max_retries, retry_delay)' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Download successful, file exists: {os.path.exists(destination_path)}, size: {os.path.getsize(destination_path) if os.path.exists(destination_path) else 0} bytes")' >> /start_handler.sh && \
    echo '        return result' >> /start_handler.sh && \
    echo '    except Exception as e:' >> /start_handler.sh && \
    echo '        logger.error(f"DEBUG: Download failed with error: {str(e)}", exc_info=True)' >> /start_handler.sh && \
    echo '        raise' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo 'def patched_get_b2_config():' >> /start_handler.sh && \
    echo '    config = original_get_config()' >> /start_handler.sh && \
    echo '    # Mask sensitive values for logging' >> /start_handler.sh && \
    echo '    masked_config = {k: (v[:5] + "***" if k == "B2_SECRET_ACCESS_KEY" else v) for k, v in config.items()}' >> /start_handler.sh && \
    echo '    logger.debug(f"DEBUG: B2 config retrieved: {masked_config}")' >> /start_handler.sh && \
    echo '    return config' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Apply the patches' >> /start_handler.sh && \
    echo 'b2_config.download_file_from_b2 = patched_download_file_from_b2' >> /start_handler.sh && \
    echo 'b2_config.get_b2_config = patched_get_b2_config' >> /start_handler.sh && \
    echo 'logger.debug("B2 config functions patched for debugging")' >> /start_handler.sh && \
    echo 'EOF' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Create debug patch for the runpod_handler function' >> /start_handler.sh && \
    echo 'cat > /runpod-volume/ComfyUI/handler_debug_patch.py << "EOF"' >> /start_handler.sh && \
    echo 'import logging' >> /start_handler.sh && \
    echo 'import sys' >> /start_handler.sh && \
    echo 'import os' >> /start_handler.sh && \
    echo 'import json' >> /start_handler.sh && \
    echo 'import traceback' >> /start_handler.sh && \
    echo 'import realism' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Set up detailed logging' >> /start_handler.sh && \
    echo 'logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")' >> /start_handler.sh && \
    echo 'logger = logging.getLogger("HANDLER_DEBUG")' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Add file handler to log to a separate file' >> /start_handler.sh && \
    echo 'log_dir = "/runpod-volume/logs"' >> /start_handler.sh && \
    echo 'os.makedirs(log_dir, exist_ok=True)' >> /start_handler.sh && \
    echo 'file_handler = logging.FileHandler(f"{log_dir}/handler_debug.log")' >> /start_handler.sh && \
    echo 'file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))' >> /start_handler.sh && \
    echo 'logger.addHandler(file_handler)' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Save the original handler' >> /start_handler.sh && \
    echo 'original_handler = realism.runpod_handler' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Create a wrapped handler with detailed logging' >> /start_handler.sh && \
    echo 'def debug_handler(job):' >> /start_handler.sh && \
    echo '    try:' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Handler received job: {json.dumps(job)}")' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Current directory: {os.getcwd()}")' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Directory contents: {os.listdir()}")' >> /start_handler.sh && \
    echo '        input_dir = "/runpod-volume/ComfyUI/input" if os.path.exists("/runpod-volume") else "input"' >> /start_handler.sh && \
    echo '        if os.path.exists(input_dir):' >> /start_handler.sh && \
    echo '            logger.debug(f"DEBUG: Input directory contents: {os.listdir(input_dir)}")' >> /start_handler.sh && \
    echo '        else:' >> /start_handler.sh && \
    echo '            logger.debug(f"DEBUG: Input directory {input_dir} does not exist")' >> /start_handler.sh && \
    echo '            os.makedirs(input_dir, exist_ok=True)' >> /start_handler.sh && \
    echo '        ' >> /start_handler.sh && \
    echo '        # Test B2 connectivity' >> /start_handler.sh && \
    echo '        try:' >> /start_handler.sh && \
    echo '            from b2_config import get_b2_s3_client' >> /start_handler.sh && \
    echo '            s3_client = get_b2_s3_client()' >> /start_handler.sh && \
    echo '            logger.debug("DEBUG: Successfully created B2 S3 client")' >> /start_handler.sh && \
    echo '            ' >> /start_handler.sh && \
    echo '            # Test listing bucket contents' >> /start_handler.sh && \
    echo '            from b2_config import get_b2_config' >> /start_handler.sh && \
    echo '            config = get_b2_config()' >> /start_handler.sh && \
    echo '            bucket_name = config["B2_IMAGE_BUCKET_NAME"]' >> /start_handler.sh && \
    echo '            ' >> /start_handler.sh && \
    echo '            try:' >> /start_handler.sh && \
    echo '                response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)' >> /start_handler.sh && \
    echo '                if "Contents" in response:' >> /start_handler.sh && \
    echo '                    objects = [obj["Key"] for obj in response["Contents"]]' >> /start_handler.sh && \
    echo '                    logger.debug(f"DEBUG: Successfully listed bucket contents (first 5): {objects}")' >> /start_handler.sh && \
    echo '                else:' >> /start_handler.sh && \
    echo '                    logger.debug(f"DEBUG: Bucket {bucket_name} is empty or not accessible")' >> /start_handler.sh && \
    echo '            except Exception as e:' >> /start_handler.sh && \
    echo '                logger.error(f"DEBUG: Failed to list bucket contents: {str(e)}")' >> /start_handler.sh && \
    echo '        except Exception as e:' >> /start_handler.sh && \
    echo '            logger.error(f"DEBUG: Failed to create B2 S3 client: {str(e)}")' >> /start_handler.sh && \
    echo '        ' >> /start_handler.sh && \
    echo '        # Call the original handler' >> /start_handler.sh && \
    echo '        logger.debug("DEBUG: Calling original handler")' >> /start_handler.sh && \
    echo '        result = original_handler(job)' >> /start_handler.sh && \
    echo '        logger.debug(f"DEBUG: Handler completed successfully with result: {json.dumps(result)}")' >> /start_handler.sh && \
    echo '        return result' >> /start_handler.sh && \
    echo '    except Exception as e:' >> /start_handler.sh && \
    echo '        logger.error(f"DEBUG: Handler failed with exception: {str(e)}")' >> /start_handler.sh && \
    echo '        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")' >> /start_handler.sh && \
    echo '        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
    echo '# Replace the original handler with our debug version' >> /start_handler.sh && \
    echo 'realism.runpod_handler = debug_handler' >> /start_handler.sh && \
    echo 'logger.debug("Handler function patched for debugging")' >> /start_handler.sh && \
    echo 'EOF' >> /start_handler.sh && \
    echo '' >> /start_handler.sh && \
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
    echo 'echo "Starting serverless handler with debug patches..."' >> /start_handler.sh && \
    echo '$PYTHON_CMD -c "import sys; sys.path.append(\"/runpod-volume/ComfyUI\"); import b2_debug_patch; import handler_debug_patch; import runpod; from realism import runpod_handler; print(\"Handler imported successfully\"); runpod.serverless.start({\"handler\": runpod_handler})" 2>&1 | tee -a $LOG_FILE' >> /start_handler.sh && \
    chmod +x /start_handler.sh

# Start with comprehensive logging
CMD ["/start_handler.sh"]