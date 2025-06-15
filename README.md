# Realism Enhancement - RunPod Serverless

AI-powered image realism enhancement using ComfyUI and RunPod Serverless.

## Features

- Face detection and enhancement
- Skin texture improvement  
- High-resolution upscaling
- Multiple output variants
- Backblaze B2 storage integration

## Deployment

This application is configured for RunPod Serverless deployment using git repository.

See `RUNPOD_GIT_DEPLOYMENT.md` for detailed deployment instructions.

## API Usage

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"input": {"image_id": "your-image.jpg"}}'
```

## Required Models

See `models_required.json` for complete list of required AI models.

Total storage needed: ~25-35GB
