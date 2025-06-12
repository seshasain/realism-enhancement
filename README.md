# Realism Enhancement - RunPod Serverless

AI-powered realistic skin enhancement service deployed on RunPod Serverless with base64 input/output.

## Features

- **Realistic skin enhancement** using multiple AI models
- **Face detection and enhancement** with specialized models
- **Multi-stage upscaling** (2x then 2x = 4x total)
- **Base64 input/output** for easy API integration
- **Multiple output variants** (comparison, resized, high-res)
- **Configurable enhancement levels**

## Quick Start

### 1. Prerequisites

- Docker installed
- RunPod account with API access
- Your ComfyUI setup with models in `/workspace/ComfyUI/`

### 2. GitHub Repository Deployment (Recommended)

```bash
# 1. Create GitHub repository
git clone https://github.com/username/realism-enhancement.git
cd realism-enhancement

# 2. Copy your files
cp -r /path/to/ComfyUI ./
cp handler.py realism.py Dockerfile requirements.txt ./

# 3. Commit and push
git add .
git commit -m "Initial deployment"
git push origin main
```

### 3. RunPod Configuration

1. Go to [RunPod Console](https://runpod.io/console/serverless)
2. Create a new template:
   - **Repository**: `https://github.com/username/realism-enhancement`
   - **Branch**: `main`
   - **Dockerfile Path**: `Dockerfile`
   - **Memory**: 16GB+ recommended
   - **GPU**: RTX 4090 or A100
   - **Timeout**: 300 seconds
3. Create endpoint using the template

📖 **Detailed Instructions**: See [GITHUB_DEPLOYMENT.md](GITHUB_DEPLOYMENT.md)

### 4. Test Your Deployment

```bash
# Test locally first
python test_handler.py

# Test on RunPod
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "input": {
      "type": "base64",
      "data": "data:image/jpeg;base64,YOUR_BASE64_IMAGE"
    },
    "parameters": {
      "detail_amount": 0.7,
      "upscale_factor": 4,
      "output_variants": ["final_resized"]
    }
  }'
```

## API Reference

### Request Format

```json
{
  "input": {
    "type": "base64|url",
    "data": "base64_image_data_or_url"
  },
  "parameters": {
    "detail_amount": 0.7,
    "upscale_factor": 4,
    "output_variants": ["final_resized"]
  }
}
```

### Parameters

- **detail_amount** (0.1-2.0): Enhancement intensity (default: 0.7)
- **upscale_factor** (2|4): Final upscaling factor (default: 4)
- **output_variants**: Array of desired outputs
  - `"comparison"`: Before/after comparison
  - `"final_resized"`: Enhanced image at original size
  - `"final_hires"`: Enhanced high-resolution image
  - `"first_hires"`: First upscaling stage result

### Response Format

#### Success Response
```json
{
  "status": "success",
  "job_id": "uuid-here",
  "processing_time": 180.5,
  "outputs": {
    "final_resized": "data:image/jpeg;base64,..."
  },
  "metadata": {
    "detail_amount": 0.7,
    "upscale_factor": 4,
    "variants_generated": ["final_resized"]
  }
}
```

#### Error Response
```json
{
  "status": "error",
  "job_id": "uuid-here",
  "error_code": "ValueError",
  "error_message": "Image too small: 128x128. Minimum 256x256",
  "processing_time": 5.2
}
```

## Input Requirements

- **Image formats**: JPG, PNG, WebP
- **Size limits**: 256x256 to 4096x4096 pixels
- **Base64 size**: ~8MB max (API gateway limits)
- **URL timeout**: 30 seconds for downloads

## Performance

- **Cold start**: ~30-60 seconds (model loading)
- **Warm processing**: 2-5 minutes per image
- **Memory usage**: ~12-16GB VRAM
- **Output size**: 2-50MB per variant (depends on resolution)

## Troubleshooting

### Common Issues

1. **"Image too large" error**
   - Resize input image to max 4096x4096
   - Use URL input for very large images

2. **"Timeout" error**
   - Increase RunPod timeout setting
   - Reduce upscale_factor to 2

3. **"Out of memory" error**
   - Use GPU with more VRAM (A100 recommended)
   - Process smaller images

4. **"Model not found" error**
   - Ensure all models are in `/workspace/ComfyUI/models/`
   - Check model file names in `realism.py`

### Debugging

```bash
# Check logs in RunPod console
# Test locally with:
python test_handler.py

# Validate Docker image:
docker run -it your-image:latest /bin/bash
```

## Cost Optimization

- **Use warm pools**: Keep minimum instances running
- **Batch processing**: Process multiple images when possible
- **Optimize models**: Use quantized models if available
- **Cache results**: Implement result caching for identical inputs

## Security

- **Input validation**: All inputs are validated
- **Temporary files**: Auto-cleanup after processing
- **No persistent storage**: Stateless processing
- **Rate limiting**: Implement client-side rate limiting

## Support

For issues and questions:
1. Check RunPod documentation
2. Review error messages in logs
3. Test locally with `test_handler.py`
4. Verify model files and paths
