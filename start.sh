#!/bin/bash

# Set the RunPod volume path
export RUNPOD_VOLUME_PATH="/runpod-volume"

# Set ComfyUI path to be in the network volume
COMFYUI_PATH="/runpod-volume/ComfyUI"
echo "Using ComfyUI from network storage: $COMFYUI_PATH"

# Change to ComfyUI directory
cd $COMFYUI_PATH
echo "Changed to directory: $(pwd)"

# List files in current directory (for debugging)
echo "Files in ComfyUI directory:"
ls -la

# Run the handler script
echo "Starting handler..."
python handler.py 