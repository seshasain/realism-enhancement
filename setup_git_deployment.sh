#!/bin/bash

# Git Repository Setup for RunPod Serverless Deployment
# This script prepares your repository for RunPod git-based deployment

set -e  # Exit on any error

echo "🚀 Setting up Git Repository for RunPod Serverless Deployment"
echo "=============================================================="

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository. Initializing..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Already in a git repository"
fi

# Check if required files exist
echo ""
echo "📋 Checking required files..."

required_files=("Dockerfile" "realism.py" "b2_config.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing required files: ${missing_files[*]}"
    echo "Please ensure all required files are present before deployment."
    exit 1
fi

# Check if runpod_handler function exists in realism.py
if grep -q "def runpod_handler" realism.py; then
    echo "✅ runpod_handler function found in realism.py"
else
    echo "❌ runpod_handler function not found in realism.py"
    echo "Please ensure the RunPod handler function is implemented."
    exit 1
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo ""
    echo "📝 Creating .gitignore file..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
*.tmp
*.temp

# Model files (too large for git)
*.safetensors
*.ckpt
*.pth
*.pt
*.gguf

# Output images
output/
outputs/
temp/
cache/
EOF
    echo "✅ .gitignore created"
else
    echo "✅ .gitignore already exists"
fi

# Create README if it doesn't exist
if [ ! -f "README.md" ]; then
    echo ""
    echo "📝 Creating README.md..."
    cat > README.md << 'EOF'
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
EOF
    echo "✅ README.md created"
else
    echo "✅ README.md already exists"
fi

# Check git status
echo ""
echo "📊 Git Status:"
echo "=============="
git status --porcelain

# Show next steps
echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "1. Review and commit your changes:"
echo "   git add ."
echo "   git commit -m 'Add RunPod serverless deployment'"
echo ""
echo "2. Push to your git repository:"
echo "   git remote add origin https://github.com/your-username/your-repo.git"
echo "   git push -u origin main"
echo ""
echo "3. Create RunPod Serverless endpoint:"
echo "   - Use git repository deployment"
echo "   - Point to your repository URL"
echo "   - Use the provided Dockerfile"
echo ""
echo "4. Upload required models (see models_required.json)"
echo ""
echo "✅ Repository is ready for RunPod deployment!"
echo ""
echo "📖 See RUNPOD_GIT_DEPLOYMENT.md for detailed instructions"
