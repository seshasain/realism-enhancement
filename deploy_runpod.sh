#!/bin/bash

# RunPod Serverless Deployment Script for Realism Enhancement Application
# This script builds and deploys the Docker image to RunPod

set -e  # Exit on any error

# Configuration
IMAGE_NAME="realism-enhancement"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

echo "🚀 Starting RunPod deployment for Realism Enhancement Application"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build the Docker image
echo "🔨 Building Docker image: ${FULL_IMAGE_NAME}"
docker build -t ${FULL_IMAGE_NAME} .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi

# Test the image locally (optional)
echo "🧪 Testing the Docker image locally..."
docker run --rm ${FULL_IMAGE_NAME} python -c "
import sys
sys.path.append('/runpod-volume/ComfyUI')
print('✅ Python path configured')
import torch
print(f'✅ PyTorch available: {torch.__version__}')
import boto3
print('✅ Boto3 available')
try:
    import runpod
    print('✅ RunPod SDK available')
except ImportError:
    print('❌ RunPod SDK not available')
print('✅ All dependencies verified')
"

echo ""
echo "🎯 Deployment Instructions:"
echo "=================================================="
echo "1. Push the image to a container registry (Docker Hub, etc.):"
echo "   docker tag ${FULL_IMAGE_NAME} your-registry/${IMAGE_NAME}:${TAG}"
echo "   docker push your-registry/${IMAGE_NAME}:${TAG}"
echo ""
echo "2. Create a RunPod Serverless endpoint with:"
echo "   - Container Image: your-registry/${IMAGE_NAME}:${TAG}"
echo "   - Container Disk: 20GB+ (for ComfyUI models)"
echo "   - GPU: RTX 4090 or better (recommended)"
echo "   - Environment Variables:"
echo "     RUNPOD_HANDLER_PATH=/runpod-volume/ComfyUI/realism.py"
echo "     RUNPOD_HANDLER_NAME=runpod_handler"
echo ""
echo "3. Test the endpoint with:"
echo '   curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \'
echo '     -H "Content-Type: application/json" \'
echo '     -H "Authorization: Bearer YOUR_API_KEY" \'
echo '     -d '"'"'{"input": {"image_id": "your-image.jpg"}}'"'"
echo ""
echo "✅ Deployment preparation complete!"
echo "📝 Make sure to upload your AI models to /runpod-volume/ComfyUI/models/ in your RunPod setup"
