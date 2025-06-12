# GitHub Repository Deployment Guide

Deploy your Realism Enhancement service to RunPod Serverless using GitHub repository.

## 🚀 Quick Start

### 1. Create GitHub Repository

```bash
# Create new repo on GitHub (e.g., username/realism-enhancement)
# Then clone and setup locally:

git clone https://github.com/username/realism-enhancement.git
cd realism-enhancement

# Copy your files to the repo
cp -r /path/to/your/ComfyUI ./
cp handler.py realism.py Dockerfile requirements.txt ./

# Add and commit
git add .
git commit -m "Initial commit: Realism enhancement serverless"
git push origin main
```

### 2. RunPod Template Configuration

1. **Go to RunPod Console**: https://runpod.io/console/serverless
2. **Create New Template**:
   - **Template Name**: `realism-enhancement`
   - **Container Image**: Leave empty (will use GitHub)
   - **Container Registry Credentials**: Not needed
   - **Repository**: `https://github.com/username/realism-enhancement`
   - **Repository Branch**: `main`
   - **Docker Build Context**: `/` (root)
   - **Dockerfile Path**: `Dockerfile`

3. **Advanced Settings**:
   - **Environment Variables**: (optional)
   - **Volume Mount Path**: Not needed for this setup
   - **HTTP Port**: `8000` (optional)

4. **Resource Configuration**:
   - **Memory**: `16384 MB` (16GB)
   - **Disk**: `20 GB`
   - **GPU**: `RTX 4090` or `A100`

### 3. Create Serverless Endpoint

1. **New Endpoint**:
   - **Endpoint Name**: `realism-enhancement-api`
   - **Select Template**: Choose your created template
   - **Min Workers**: `0`
   - **Max Workers**: `3`
   - **Idle Timeout**: `5` seconds
   - **Execution Timeout**: `300` seconds (5 minutes)
   - **GPU Type**: Same as template

2. **Deploy**: Click "Deploy" and wait for build

## 📋 Repository Structure

Your GitHub repo should look like this:

```
realism-enhancement/
├── README.md                    # Project documentation
├── GITHUB_DEPLOYMENT.md         # This file
├── Dockerfile                   # Container configuration
├── requirements.txt             # Python dependencies
├── handler.py                   # RunPod serverless handler
├── realism.py                   # Your workflow logic
├── test_handler.py              # Local testing
├── api_example.py               # API usage examples
├── .gitignore                   # Git ignore file
├── .github/                     # GitHub workflows (optional)
│   └── workflows/
│       └── test.yml
└── ComfyUI/                     # Your existing setup
    ├── models/                  # Pre-trained models
    │   ├── checkpoints/
    │   ├── loras/
    │   ├── upscale_models/
    │   └── ...
    ├── venv/                    # Python virtual environment
    ├── custom_nodes/            # Custom ComfyUI nodes
    └── ...
```

## 🔧 Environment Variables (Optional)

You can set these in RunPod template if needed:

```bash
# Model paths (if different from defaults)
COMFYUI_MODEL_PATH=/workspace/ComfyUI/models
COMFYUI_OUTPUT_PATH=/tmp/outputs

# Performance settings
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Logging
LOG_LEVEL=INFO
```

## 🧪 Testing Your Deployment

### Local Testing
```bash
# Test locally before pushing
python test_handler.py
```

### GitHub Actions (Optional)
Create `.github/workflows/test.yml`:

```yaml
name: Test Handler
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python test_handler.py
```

### RunPod API Testing
```bash
# Get your endpoint URL and API key from RunPod console
export RUNPOD_ENDPOINT="https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run"
export RUNPOD_API_KEY="your-api-key"

# Test with curl
curl -X POST $RUNPOD_ENDPOINT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{
    "input": {
      "type": "base64",
      "data": "data:image/jpeg;base64,YOUR_BASE64_IMAGE"
    },
    "parameters": {
      "detail_amount": 0.7,
      "output_variants": ["final_resized"]
    }
  }'
```

## 🔄 Updates and Versioning

### Making Updates
```bash
# Make changes to your code
git add .
git commit -m "Update: improved enhancement algorithm"
git push origin main

# RunPod will automatically rebuild on next cold start
# Or manually rebuild in RunPod console
```

### Version Tags
```bash
# Create version tags for releases
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Use specific tag in RunPod template if needed
# Repository Branch: v1.0.0
```

## 🐛 Troubleshooting

### Build Failures
1. **Check Dockerfile syntax**
2. **Verify all files are committed**
3. **Check RunPod build logs**
4. **Test Docker build locally**:
   ```bash
   docker build -t test-image .
   docker run test-image
   ```

### Runtime Errors
1. **Check RunPod execution logs**
2. **Verify model file paths**
3. **Test handler locally**
4. **Check memory/GPU requirements**

### Common Issues

**Issue**: "No such file or directory: ComfyUI"
**Solution**: Ensure ComfyUI folder is committed to git

**Issue**: "Module not found"
**Solution**: Check requirements.txt and virtual environment

**Issue**: "CUDA out of memory"
**Solution**: Use larger GPU or reduce batch size

## 💡 Best Practices

### Repository Management
- ✅ Use `.gitignore` for large files
- ✅ Keep models in Git LFS if very large
- ✅ Use meaningful commit messages
- ✅ Tag stable releases

### Performance
- ✅ Pre-load models in container
- ✅ Use efficient Docker layers
- ✅ Minimize cold start time
- ✅ Optimize memory usage

### Security
- ✅ Don't commit API keys
- ✅ Use environment variables
- ✅ Validate all inputs
- ✅ Keep dependencies updated

## 📞 Support

- **RunPod Docs**: https://docs.runpod.io/
- **GitHub Issues**: Use your repo's issue tracker
- **RunPod Discord**: https://discord.gg/runpod
