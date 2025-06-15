# RunPod Serverless Deployment - Realism Enhancement Application

This guide explains how to deploy the Realism Enhancement application to RunPod Serverless.

## Overview

The application processes images through a ComfyUI pipeline to enhance realism, including:
- Face detection and enhancement
- Skin texture improvement
- High-resolution upscaling
- Multiple output variants

## Prerequisites

- Docker installed and running
- RunPod account with API access
- Container registry access (Docker Hub, etc.)

## Quick Deployment

1. **Build and test locally:**
   ```bash
   chmod +x deploy_runpod.sh
   ./deploy_runpod.sh
   ```

2. **Push to registry:**
   ```bash
   docker tag realism-enhancement:latest your-registry/realism-enhancement:latest
   docker push your-registry/realism-enhancement:latest
   ```

3. **Create RunPod endpoint** with the image above

## Detailed Setup

### 1. Container Configuration

**Recommended Settings:**
- **Container Image:** `your-registry/realism-enhancement:latest`
- **Container Disk:** 25GB+ (for ComfyUI models)
- **GPU:** RTX 4090 or A100 (recommended)
- **CPU:** 8+ cores
- **RAM:** 32GB+

**Environment Variables:**
```
RUNPOD_HANDLER_PATH=/runpod-volume/ComfyUI/realism.py
RUNPOD_HANDLER_NAME=runpod_handler
PYTHONUNBUFFERED=1
```

### 2. Required Models

The application requires these models in `/runpod-volume/ComfyUI/models/`:

**Checkpoints:**
- `epicrealism_naturalSinRC1VAE.safetensors`
- `STOIQOAfroditexl_XL31.safetensors`

**LoRA Models:**
- `more_details (1).safetensors`
- `SD1.5_epiCRealismHelper (1).safetensors`
- `more_details.safetensors`

**CLIP Models:**
- `clip_l.safetensors`
- `t5xxl_fp8_e4m3fn.safetensors`

**UNet Models:**
- `flux1-dev-Q5_0.gguf`

**VAE Models:**
- `flux-fill-vae.safetensors`

**Upscale Models:**
- `4x_NMKD-Siax_200k.pth`

**Detection Models:**
- `segm/face_yolov8m-seg_60.pt`

### 3. API Usage

**Endpoint URL:**
```
https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run
```

**Request Format:**
```json
{
  "input": {
    "image_id": "your-image-filename.jpg"
  }
}
```

**Response Format:**
```json
{
  "status": "success",
  "message": "Successfully processed image: your-image.jpg",
  "outputs": {
    "comparison_image": "/path/to/comparison.png",
    "final_resized": "/path/to/final_resized.png",
    "final_hires": "/path/to/final_hires.png",
    "first_hires": "/path/to/first_hires.png"
  }
}
```

### 4. Example Usage

**cURL:**
```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"input": {"image_id": "portrait.jpg"}}'
```

**Python:**
```python
import requests

url = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_KEY"
}
data = {
    "input": {
        "image_id": "portrait.jpg"
    }
}

response = requests.post(url, json=data, headers=headers)
result = response.json()
print(result)
```

## Storage Configuration

The application uses Backblaze B2 for image storage. Configuration is in `b2_config.py`:

- **Input images** are downloaded from B2 bucket
- **Output images** are saved to ComfyUI's output directory
- **Temporary files** are cleaned up automatically

## Troubleshooting

### Common Issues

1. **Model Loading Errors:**
   - Ensure all required models are uploaded to the correct paths
   - Check model file permissions and sizes

2. **Memory Issues:**
   - Increase container RAM allocation
   - Use smaller batch sizes for processing

3. **CUDA Errors:**
   - Verify GPU compatibility
   - Check CUDA driver versions

### Logs and Debugging

Enable detailed logging by setting:
```
PYTHONUNBUFFERED=1
```

Check RunPod logs for detailed error messages and processing status.

## Performance Optimization

- **Cold Start:** ~30-60 seconds (model loading)
- **Processing Time:** 2-5 minutes per image (depending on resolution)
- **Concurrent Requests:** Limited by GPU memory

## Cost Estimation

Typical costs on RunPod (RTX 4090):
- **Cold start:** ~$0.10-0.20
- **Processing:** ~$0.50-1.00 per image
- **Storage:** Minimal (temporary files)

## Support

For issues specific to:
- **RunPod platform:** Contact RunPod support
- **Application logic:** Check the application logs
- **Model issues:** Verify model files and versions
