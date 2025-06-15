# RunPod Serverless - Git Repository Deployment

This guide shows how to deploy the Realism Enhancement application to RunPod Serverless using git repository deployment (recommended method).

## 🎯 Overview

RunPod will:
1. Clone your git repository
2. Build the Docker image using your Dockerfile
3. Copy your application files (`realism.py`, `b2_config.py`) to `/runpod-volume/ComfyUI/`
4. Set up the serverless handler

## 📋 Prerequisites

- Git repository (GitHub, GitLab, etc.) containing your code
- RunPod account with serverless access
- Required AI models uploaded to persistent storage

## 🚀 Quick Setup Steps

### 1. Prepare Your Git Repository

Ensure your repository contains these files:
```
your-repo/
├── Dockerfile                    # ✅ Ready
├── realism.py                   # ✅ Ready (with runpod_handler)
├── b2_config.py                 # ✅ Ready
├── requirements_runpod.txt      # ✅ Ready (optional, deps in Dockerfile)
└── README.md                    # Optional
```

### 2. Commit and Push to Git

```bash
git add .
git commit -m "Add RunPod serverless deployment"
git push origin main
```

### 3. Create RunPod Serverless Endpoint

1. **Go to RunPod Console** → Serverless → Create Endpoint

2. **Select "Git Repository" as source**

3. **Configure Repository:**
   - **Repository URL:** `https://github.com/your-username/your-repo.git`
   - **Branch:** `main` (or your preferred branch)
   - **Dockerfile Path:** `Dockerfile` (default)

4. **Configure Container:**
   - **Container Disk:** 25GB+ (for ComfyUI models)
   - **GPU:** RTX 4090 or A100 (recommended)
   - **CPU:** 8+ cores
   - **Memory:** 32GB+

5. **Environment Variables:**
   ```
   RUNPOD_HANDLER_PATH=/runpod-volume/ComfyUI/realism.py
   RUNPOD_HANDLER_NAME=runpod_handler
   PYTHONUNBUFFERED=1
   ```

6. **Advanced Settings:**
   - **Max Workers:** 1-3 (depending on your needs)
   - **Idle Timeout:** 5 seconds
   - **Max Job Timeout:** 600 seconds (10 minutes)

### 4. Upload Required Models

Upload these models to your RunPod persistent storage at `/runpod-volume/ComfyUI/models/`:

**Critical Models (see `models_required.json` for complete list):**
- `checkpoints/epicrealism_naturalSinRC1VAE.safetensors`
- `checkpoints/STOIQOAfroditexl_XL31.safetensors`
- `unet/flux1-dev-Q5_0.gguf`
- `clip/clip_l.safetensors`
- `clip/t5xxl_fp8_e4m3fn.safetensors`
- `vae/flux-fill-vae.safetensors`
- `loras/more_details (1).safetensors`
- `loras/SD1.5_epiCRealismHelper (1).safetensors`
- `loras/more_details.safetensors`
- `upscale_models/4x_NMKD-Siax_200k.pth`
- `ultralytics/segm/face_yolov8m-seg_60.pt`

## 🧪 Testing Your Deployment

### Test API Call

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": {
      "image_id": "your-test-image.jpg"
    }
  }'
```

### Expected Response

```json
{
  "status": "success",
  "message": "Successfully processed image: your-test-image.jpg",
  "outputs": {
    "comparison_image": "/runpod-volume/ComfyUI/output/RealSkin_AI_Lite_Comparer_Original_Vs_Final_00001_.png",
    "final_resized": "/runpod-volume/ComfyUI/output/RealSkin_AI_Light_Final_Resized_to_Original_Scale_00001_.png",
    "final_hires": "/runpod-volume/ComfyUI/output/RealSkin_AI_Light_Final_Hi-Rez_Output_00001_.png",
    "first_hires": "/runpod-volume/ComfyUI/output/RealSkin_AI_Light_First_Hi-Rez_Output_00001_.png"
  }
}
```

## 🔄 Updating Your Deployment

To update your deployment:

1. **Make changes** to your code
2. **Commit and push** to git:
   ```bash
   git add .
   git commit -m "Update realism processing"
   git push origin main
   ```
3. **Rebuild in RunPod** (automatic or manual trigger depending on settings)

## 📁 File Structure in RunPod

After deployment, your files will be organized as:

```
/runpod-volume/
├── ComfyUI/                     # Cloned from ComfyUI repo
│   ├── main.py
│   ├── nodes.py
│   ├── requirements.txt
│   ├── models/                  # Your uploaded models
│   ├── custom_nodes/           # Custom nodes (auto-installed)
│   ├── output/                 # Generated images
│   ├── realism.py              # Your app (copied from git)
│   └── b2_config.py           # Your config (copied from git)
├── image_cache/               # Temporary image storage
└── outputs/                   # Additional outputs
```

## 🔧 Advantages of Git Deployment

✅ **Version Control:** Track all changes  
✅ **Easy Updates:** Just push to git  
✅ **No Registry Needed:** No Docker Hub/registry required  
✅ **Automatic Builds:** RunPod builds from source  
✅ **Rollback Support:** Easy to revert to previous versions  
✅ **Team Collaboration:** Multiple developers can contribute  

## 🐛 Troubleshooting

### Common Issues

1. **Build Failures:**
   - Check Dockerfile syntax
   - Verify all dependencies are available
   - Check RunPod build logs

2. **Handler Not Found:**
   - Verify `RUNPOD_HANDLER_PATH` points to correct file
   - Ensure `runpod_handler` function exists in `realism.py`

3. **Model Loading Errors:**
   - Verify all models are uploaded to correct paths
   - Check model file permissions
   - Ensure sufficient disk space (25GB+)

4. **Memory Issues:**
   - Increase container memory allocation
   - Use smaller batch sizes
   - Consider model quantization

### Debugging Tips

- **Check Logs:** RunPod console shows detailed build and runtime logs
- **Test Locally:** Use `test_runpod_handler.py` for local testing
- **Verify Models:** Ensure all required models from `models_required.json` are present

## 💰 Cost Optimization

- **Use Spot Instances:** Lower cost for non-critical workloads
- **Optimize Idle Timeout:** Reduce cold starts
- **Model Caching:** Keep frequently used models in memory
- **Batch Processing:** Process multiple images when possible

## 📞 Support

- **RunPod Documentation:** [docs.runpod.io](https://docs.runpod.io)
- **RunPod Discord:** Community support and help
- **Application Issues:** Check logs and verify model requirements

---

**Ready for deployment!** 🚀  
Your git repository is configured for RunPod Serverless deployment.
