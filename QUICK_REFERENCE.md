# RunPod Git Deployment - Quick Reference

## 🚀 3-Step Deployment

### 1. Prepare Repository
```bash
./setup_git_deployment.sh
git add .
git commit -m "Add RunPod serverless deployment"
git push origin main
```

### 2. Create RunPod Endpoint
- **Source:** Git Repository
- **URL:** `https://github.com/your-username/your-repo.git`
- **Dockerfile:** `Dockerfile`
- **Disk:** 25GB+
- **GPU:** RTX 4090/A100

### 3. Environment Variables
```
RUNPOD_HANDLER_PATH=/runpod-volume/ComfyUI/realism.py
RUNPOD_HANDLER_NAME=runpod_handler
PYTHONUNBUFFERED=1
```

## 📡 API Usage

**Endpoint:** `https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run`

**Request:**
```json
{
  "input": {
    "image_id": "your-image.jpg"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "outputs": {
    "comparison_image": "/path/to/comparison.png",
    "final_resized": "/path/to/final_resized.png",
    "final_hires": "/path/to/final_hires.png",
    "first_hires": "/path/to/first_hires.png"
  }
}
```

## 📦 Required Models (~25GB)

Upload to `/runpod-volume/ComfyUI/models/`:

**Critical Models:**
- `checkpoints/epicrealism_naturalSinRC1VAE.safetensors` (6GB)
- `checkpoints/STOIQOAfroditexl_XL31.safetensors` (7GB)
- `unet/flux1-dev-Q5_0.gguf` (10GB)
- `clip/clip_l.safetensors` (1GB)
- `clip/t5xxl_fp8_e4m3fn.safetensors` (5GB)

**See `models_required.json` for complete list**

## 🔧 Testing

**Local Test:**
```bash
python test_runpod_handler.py
```

**API Test:**
```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"input": {"image_id": "test.jpg"}}'
```

## 💰 Costs (RTX 4090)
- **Cold Start:** ~$0.10-0.20 (30-60s)
- **Processing:** ~$0.50-1.00 per image (2-5min)

## 🔄 Updates
```bash
git add .
git commit -m "Update"
git push origin main
# RunPod auto-rebuilds
```

## 📞 Support
- **Docs:** `RUNPOD_GIT_DEPLOYMENT.md`
- **Models:** `models_required.json`
- **Status:** `DEPLOYMENT_SUMMARY.md`
