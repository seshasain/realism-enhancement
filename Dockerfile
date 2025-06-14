FROM runpod/pytorch:3.10-2.0.1-118-runtime

# Set working directory
WORKDIR /workspace

# Install dependencies
RUN pip install boto3

# Create directories for network storage
RUN mkdir -p /runpod-volume/ComfyUI /runpod-volume/tmp /runpod-volume/outputs

# Copy files to the network volume
COPY --chown=1000:1000 realism.py b2_config.py handler.py start.sh runpod.json /runpod-volume/ComfyUI/

# Make scripts executable
RUN chmod +x /runpod-volume/ComfyUI/start.sh /runpod-volume/ComfyUI/handler.py

# Set the entrypoint
ENTRYPOINT ["bash", "/runpod-volume/ComfyUI/start.sh"] 