#!/usr/bin/env python3
"""
Startup script with comprehensive logging for debugging
"""

import os
import sys
import subprocess
import traceback
from datetime import datetime

def log_system_info():
    """Log comprehensive system information"""
    print("=" * 80)
    print(f"🚀 RUNPOD SERVERLESS STARTUP - {datetime.now()}")
    print("=" * 80)
    
    print(f"📍 Current working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Python path: {sys.path}")
    
    print("\n🌍 Environment variables:")
    for key, value in sorted(os.environ.items()):
        if any(keyword in key for keyword in ['PYTHON', 'RUNPOD', 'CUDA', 'DEBUG', 'VERBOSE']):
            print(f"   {key}={value}")
    
    print("\n📂 Files in current directory:")
    try:
        for item in sorted(os.listdir('.')):
            print(f"   - {item}")
    except Exception as e:
        print(f"   ❌ Error listing directory: {e}")
    
    print("\n🔍 Checking for key files:")
    key_files = ['handler.py', 'realism.py', 'b2_config.py', 'requirements.txt', 'runpod.toml']
    for file in key_files:
        exists = os.path.exists(file)
        if exists:
            try:
                size = os.path.getsize(file)
                print(f"   {file}: ✅ ({size} bytes)")
            except:
                print(f"   {file}: ✅")
        else:
            print(f"   {file}: ❌")
    
    print("\n🔧 System information:")
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True)
        print(f"   Python: {result.stdout.strip()}")
    except:
        print("   Python: Error getting version")
    
    try:
        result = subprocess.run(['pip', '--version'], capture_output=True, text=True)
        print(f"   Pip: {result.stdout.strip()}")
    except:
        print("   Pip: Error getting version")
    
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   GPU: {result.stdout.strip()}")
        else:
            print("   GPU: nvidia-smi not available")
    except:
        print("   GPU: Error checking GPU")
    
    print("\n📦 Checking RunPod installation:")
    try:
        import runpod
        version = getattr(runpod, '__version__', 'unknown')
        print(f"   ✅ RunPod imported successfully (version: {version})")
    except Exception as e:
        print(f"   ❌ Failed to import runpod: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
    
    print("\n🔍 Network volume check:")
    volume_path = "/runpod-volume"
    comfyui_path = "/runpod-volume/ComfyUI"
    
    if os.path.exists(volume_path):
        print(f"   ✅ Network volume exists: {volume_path}")
        try:
            items = os.listdir(volume_path)
            print(f"   📂 Contents: {items}")
        except Exception as e:
            print(f"   ⚠️ Error listing volume contents: {e}")
    else:
        print(f"   ❌ Network volume not found: {volume_path}")
    
    if os.path.exists(comfyui_path):
        print(f"   ✅ ComfyUI directory exists: {comfyui_path}")
        try:
            items = os.listdir(comfyui_path)[:10]  # First 10 items
            print(f"   📂 ComfyUI contents (first 10): {items}")
        except Exception as e:
            print(f"   ⚠️ Error listing ComfyUI contents: {e}")
    else:
        print(f"   ❌ ComfyUI directory not found: {comfyui_path}")
    
    print("=" * 80)

def main():
    """Main startup function"""
    try:
        # Log system information
        log_system_info()

        # Import the handler function
        print("🚀 Importing handler...")
        from handler import handler
        print("✅ Handler function imported successfully")

        # Return the handler function for RunPod to use
        return handler

    except Exception as e:
        print(f"❌ Startup failed: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise

# For RunPod serverless
def handler_wrapper(event):
    """Wrapper that logs and calls the actual handler"""
    print("🎯 Handler wrapper called")
    print(f"📥 Event: {event}")

    try:
        from handler import handler
        return handler(event)
    except Exception as e:
        print(f"❌ Handler failed: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    # Log system info when run directly
    log_system_info()

    # Start RunPod serverless
    try:
        import runpod
        print("🚀 Starting RunPod serverless with wrapper...")
        runpod.serverless.start({"handler": handler_wrapper})
    except Exception as e:
        print(f"❌ Failed to start RunPod serverless: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise
