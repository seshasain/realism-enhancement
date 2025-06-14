#!/usr/bin/env python3
"""
Simple RunPod Serverless Handler - Just run the working command
"""

import os
import sys
import json
import subprocess
import runpod

print("🚀 Simple RunPod Handler Starting...")

def handler(event):
    """
    Simple handler: Just run the working command in ComfyUI directory
    """
    print("🚀 Handler called")
    print(f"📥 Input: {event}")
    
    try:
        # Get image_id from input
        image_id = event.get("input", {}).get("image_id", "")
        if not image_id:
            return {"error": "No image_id provided"}
        
        print(f"🎯 Processing image: {image_id}")
        
        # Change to ComfyUI directory
        comfyui_dir = "/runpod-volume/ComfyUI"
        if os.path.exists(comfyui_dir):
            os.chdir(comfyui_dir)
            print(f"📁 Changed to: {comfyui_dir}")
        else:
            print(f"⚠️ ComfyUI dir not found, using current: {os.getcwd()}")
        
        # Run the exact working command: python -m realism
        print("🔥 Running: python -m realism")
        result = subprocess.run(
            [sys.executable, "-m", "realism"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        print(f"📤 Command output: {result.stdout}")
        if result.stderr:
            print(f"⚠️ Command errors: {result.stderr}")
        
        if result.returncode == 0:
            return {
                "status": "success",
                "image_id": image_id,
                "output": result.stdout,
                "message": "Image processed successfully"
            }
        else:
            return {
                "status": "error", 
                "image_id": image_id,
                "error": result.stderr,
                "output": result.stdout
            }
            
    except Exception as e:
        print(f"❌ Handler error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Start RunPod serverless
print("🚀 Starting RunPod serverless...")
runpod.serverless.start({"handler": handler})
