#!/bin/bash

# Enable verbose logging
set -x

echo "[$(date)] ===== STARTING REALISM ENHANCER SERVICE ====="

# Set the RunPod volume path
export RUNPOD_VOLUME_PATH="/runpod-volume"
echo "[$(date)] Set RUNPOD_VOLUME_PATH to $RUNPOD_VOLUME_PATH"

# Set ComfyUI path to be in the network volume
COMFYUI_PATH="/runpod-volume/ComfyUI"
echo "[$(date)] Using ComfyUI from network storage: $COMFYUI_PATH"

# Check if the directory exists
if [ -d "$COMFYUI_PATH" ]; then
    echo "[$(date)] ComfyUI directory exists"
else
    echo "[$(date)] ERROR: ComfyUI directory does not exist at $COMFYUI_PATH"
    # Create the directory if it doesn't exist
    mkdir -p $COMFYUI_PATH
    echo "[$(date)] Created ComfyUI directory"
fi

# Check for required files
echo "[$(date)] Checking for required files:"
for file in realism.py b2_config.py handler.py; do
    if [ -f "$COMFYUI_PATH/$file" ]; then
        echo "[$(date)] ✅ $file exists"
    else
        echo "[$(date)] ❌ ERROR: $file does not exist at $COMFYUI_PATH/$file"
    fi
done

# Check Python environment
echo "[$(date)] Python version:"
python --version
echo "[$(date)] Pip version:"
pip --version
echo "[$(date)] Installed packages:"
pip list

# Change to ComfyUI directory
cd $COMFYUI_PATH
echo "[$(date)] Changed to directory: $(pwd)"

# List files in current directory
echo "[$(date)] Files in ComfyUI directory:"
ls -la

# Check if handler.py exists and is executable
if [ -f "handler.py" ]; then
    echo "[$(date)] handler.py exists"
    chmod +x handler.py
    echo "[$(date)] Made handler.py executable"
else
    echo "[$(date)] ERROR: handler.py does not exist"
fi

# Run the handler script
echo "[$(date)] Starting handler..."
python handler.py 