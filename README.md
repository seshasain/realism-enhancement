# RealSkin AI

RealSkin AI is a state-of-the-art image enhancement system designed to improve the realism of AI-generated portraits. It uses ComfyUI as a backend and is deployed on RunPod for serverless execution.

## Features

- Enhances AI-generated portraits to improve skin texture and realism
- Supports selective face parsing to target specific facial features
- Provides comparison images showing before/after results
- Deployed as a serverless API on RunPod

## Recent Improvements

### Enhanced Logging and Error Handling

- **Comprehensive Logging**: Added detailed logging throughout the application with timestamps, log levels, and contextual information
- **Log Rotation**: Implemented log rotation to manage log file sizes and retention
- **NumPy Compatibility Fix**: Pinned NumPy to version 1.x to resolve compatibility issues with PyTorch
- **B2 Storage Resilience**: 
  - Added retry mechanism for B2 storage operations
  - Implemented fallback mechanisms when B2 storage operations fail
  - Enhanced error reporting for better debugging
- **Local File Fallback**: Added support for using local files when B2 storage is unavailable
- **Temporary File Management**: Improved cleanup of temporary files

### Deployment Improvements

- Updated Docker container with better logging configuration
- Added environment variable for log level control
- Created dedicated log directory with proper permissions
- Enhanced startup script with detailed system information logging
- Added verification steps for NumPy and PyTorch versions at startup

## API Usage

The API accepts the following parameters:

```json
{
  "input": {
    "image_id": "image_filename.jpg",
    "face_parsing": {
      "background": false,
      "skin": false,
      "nose": true,
      "eye_g": true,
      "r_eye": true,
      "l_eye": true,
      "r_brow": false,
      "l_brow": false,
      "r_ear": false,
      "l_ear": false,
      "mouth": false,
      "u_lip": true,
      "l_lip": true,
      "hair": false,
      "hat": false,
      "ear_r": false,
      "neck_l": false,
      "neck": false,
      "cloth": true
    }
  }
}
```

## Deployment

See `DEPLOYMENT_SUMMARY.md` and `RUNPOD_GIT_DEPLOYMENT.md` for detailed deployment instructions.

## Required Models

See `models_required.json` for complete list of required AI models.

Total storage needed: ~25-35GB
