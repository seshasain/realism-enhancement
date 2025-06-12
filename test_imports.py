#!/usr/bin/env python3
"""
Test script to verify all required imports work in the container
"""

import sys
import os

def test_imports():
    """Test all required imports for the handler."""
    print("🧪 Testing imports for RunPod handler...")
    print("=" * 50)
    
    # Test basic Python modules
    try:
        import json
        import base64
        import uuid
        import time
        import traceback
        import logging
        print("✅ Basic Python modules: OK")
    except ImportError as e:
        print(f"❌ Basic Python modules failed: {e}")
        return False
    
    # Test PIL/Pillow
    try:
        from PIL import Image
        print(f"✅ PIL/Pillow: OK")
        
        # Test basic PIL functionality
        img = Image.new('RGB', (100, 100), color='red')
        print(f"✅ PIL functionality: OK")
    except ImportError as e:
        print(f"❌ PIL/Pillow failed: {e}")
        print("💡 SOLUTION: pip install pillow")
        return False
    except Exception as e:
        print(f"❌ PIL functionality failed: {e}")
        return False
    
    # Test PyTorch
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        
        # Test CUDA availability
        if torch.cuda.is_available():
            print(f"✅ CUDA: {torch.cuda.get_device_name()}")
        else:
            print("⚠️  CUDA: Not available")
    except ImportError as e:
        print(f"❌ PyTorch failed: {e}")
        return False
    
    # Test NumPy
    try:
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")
    except ImportError as e:
        print(f"❌ NumPy failed: {e}")
        return False
    
    # Test requests (for URL downloads)
    try:
        import requests
        print(f"✅ Requests: {requests.__version__}")
    except ImportError as e:
        print(f"❌ Requests failed: {e}")
        print("💡 SOLUTION: pip install requests")
        return False
    
    # Test ComfyUI paths
    print("\n🔍 Checking ComfyUI paths...")
    comfyui_paths = [
        '/runpod-volume/ComfyUI',
        '/workspace/ComfyUI',
        '/runpod-volume/ComfyUI/models',
        '/runpod-volume/ComfyUI/venv'
    ]
    
    for path in comfyui_paths:
        if os.path.exists(path):
            print(f"✅ Found: {path}")
        else:
            print(f"❌ Missing: {path}")
    
    # Test handler import
    print("\n🔍 Testing handler import...")
    try:
        sys.path.append('/workspace')
        import handler
        print("✅ Handler import: OK")
    except ImportError as e:
        print(f"❌ Handler import failed: {e}")
        return False
    
    print("\n🎉 All imports successful!")
    return True

def test_simple_api():
    """Test a simple API call structure."""
    print("\n🧪 Testing API structure...")
    
    try:
        from handler import validate_input
        
        # Test valid input
        test_event = {
            'input': {
                'type': 'base64',
                'data': 'test_data'
            },
            'parameters': {
                'detail_amount': 0.7
            }
        }
        
        result = validate_input(test_event)
        print("✅ Input validation: OK")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 RunPod Container Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test API structure
    if not test_simple_api():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED! Container is ready.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Check the errors above.")
        sys.exit(1)
