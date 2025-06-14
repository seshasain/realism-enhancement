# Realism Enhancement - RunPod Serverless

This repository contains a RunPod serverless implementation of the realism image enhancement module.

## 🚀 **Serverless Deployment**

This repository is configured for RunPod serverless deployment using GitHub integration.

### **Repository Structure**
```
├── handler.py          # RunPod serverless handler
├── realism.py          # Main image processing module  
├── b2_config.py        # B2 storage configuration
├── requirements.txt    # Python dependencies
├── runpod.toml         # RunPod configuration
└── README.md          # This file
```

### **Deployment URL**
- **Repository**: `https://github.com/seshasain/realism-enhancement`
- **Branch**: `main`

### **Configuration**
- **Handler**: `handler.handler`
- **Runtime**: Python 3.10 with PyTorch 2.1.0
- **GPU**: RTX 3080 Ti, RTX 3090, RTX A6000
- **Network Volume**: Required for ComfyUI models and data

### **API Usage**

**Input Format:**
```json
{
  "input": {
    "image_id": "3XYW7936QW7G6EKG1YAH4EK930.jpeg"
  }
}
```

**Output Format:**
```json
{
  "status": "success",
  "image_id": "3XYW7936QW7G6EKG1YAH4EK930.jpeg",
  "output_images": [
    {
      "filename": "processed_image.jpg",
      "url": "https://s3.us-east-005.backblazeb2.com/shortshive/processed_image.jpg",
      "size": 1234567
    }
  ],
  "total_outputs": 1
}
```

### **Environment Variables**
- `PYTHONPATH=/runpod-volume/ComfyUI`
- `PYTHONUNBUFFERED=1`

### **Network Volume**
- **Name**: "Netwrok Storage"
- **Mount Path**: `/runpod-volume`
- **Contains**: ComfyUI installation, models, and training data

## 🧪 **Testing**

Use the test script to validate deployment:
```bash
python test_serverless.py YOUR_ENDPOINT_ID --image-id "3XYW7936QW7G6EKG1YAH4EK930.jpeg"
```

## 📋 **Features**

- ✅ Serverless image enhancement processing
- ✅ B2 storage integration for outputs
- ✅ Network volume support for models/data
- ✅ Auto-scaling based on demand
- ✅ RESTful API interface
- ✅ Error handling and logging

## 🔧 **Local Development**

For local testing:
```bash
python handler.py
```

## 📊 **Performance**
- **Cold Start**: 10-30 seconds (model loading)
- **Processing**: 30-120 seconds per image
- **Cost**: ~$0.001-0.005 per image processed
