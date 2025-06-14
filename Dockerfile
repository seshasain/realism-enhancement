FROM runpod/pytorch:3.10-2.0.1-118-runtime

# Set working directory
WORKDIR /workspace

# Install dependencies
RUN pip install boto3 && \
    echo "Installed boto3 successfully"

# Create directories for network storage
RUN mkdir -p /runpod-volume/ComfyUI /runpod-volume/tmp /runpod-volume/outputs && \
    echo "Created directories in /runpod-volume"

# Make scripts executable
RUN chmod +x /runpod-volume/ComfyUI/start.sh /runpod-volume/ComfyUI/handler.py && \
    echo "Made scripts executable"

# List files in the ComfyUI directory for verification
RUN ls -la /runpod-volume/ComfyUI/

# Set the entrypoint
ENTRYPOINT ["bash", "/runpod-volume/ComfyUI/start.sh"] 