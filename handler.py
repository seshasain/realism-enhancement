#!/usr/bin/env python3
"""
Simple RunPod handler for realism enhancement
"""

import os
import sys
import json
import base64
import uuid
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Debug: Check what's available
logger.info(f"🔍 Python path: {sys.path[:3]}...")
logger.info(f"🔍 Current working directory: {os.getcwd()}")

# Add ComfyUI to path
comfyui_path = '/runpod-volume/ComfyUI'
if os.path.exists(comfyui_path):
    sys.path.insert(0, comfyui_path)
    # Add venv site-packages
    venv_path = f"{comfyui_path}/venv/lib/python3.10/site-packages"
    if os.path.exists(venv_path):
        sys.path.insert(0, venv_path)
        # List what's in venv
        try:
            venv_contents = os.listdir(venv_path)[:10]  # First 10 items
            logger.info(f"🔍 ComfyUI venv contents: {venv_contents}")
        except:
            logger.info("🔍 Could not list venv contents")
    logger.info(f"✅ Added ComfyUI paths")
else:
    logger.error(f"❌ ComfyUI not found at {comfyui_path}")

# Debug: Check system packages
try:
    import site
    site_packages = site.getsitepackages()
    logger.info(f"🔍 System site-packages: {site_packages}")

    # Check if packages exist in system
    for pkg_path in site_packages:
        if os.path.exists(pkg_path):
            contents = [f for f in os.listdir(pkg_path) if 'pil' in f.lower() or 'torch' in f.lower() or 'numpy' in f.lower()][:5]
            if contents:
                logger.info(f"🔍 Found packages in {pkg_path}: {contents}")
except Exception as e:
    logger.info(f"🔍 Could not check system packages: {e}")

# Import packages with runtime installation fallback
def try_install_and_import(package_name, import_name=None):
    """Try to import a package, install if missing."""
    if import_name is None:
        import_name = package_name

    try:
        if package_name == 'PIL':
            from PIL import Image
            logger.info("✅ PIL imported")
            return Image
        elif package_name == 'torch':
            import torch
            logger.info("✅ PyTorch imported")
            return torch
        elif package_name == 'numpy':
            import numpy as np
            logger.info("✅ NumPy imported")
            return np
        elif package_name == 'requests':
            import requests
            logger.info("✅ Requests imported")
            return requests
    except ImportError:
        logger.error(f"❌ {package_name} import failed, trying to install...")
        try:
            import subprocess
            import sys
            if package_name == 'PIL':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow'])
                from PIL import Image
                logger.info("✅ PIL installed and imported")
                return Image
            elif package_name == 'torch':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'torch', '--index-url', 'https://download.pytorch.org/whl/cu118'])
                import torch
                logger.info("✅ PyTorch installed and imported")
                return torch
            elif package_name == 'numpy':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
                import numpy as np
                logger.info("✅ NumPy installed and imported")
                return np
            elif package_name == 'requests':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
                import requests
                logger.info("✅ Requests installed and imported")
                return requests
        except Exception as e:
            logger.error(f"❌ Failed to install {package_name}: {e}")
            return None

# Try to import/install packages
Image = try_install_and_import('PIL')
torch = try_install_and_import('torch')
np = try_install_and_import('numpy')
requests = try_install_and_import('requests')


def handler(event):
    """Simple handler function."""
    job_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"🚀 [{job_id}] Starting request")
        
        # Check if we have required packages
        if Image is None:
            return {
                "status": "error",
                "job_id": job_id,
                "error_message": "PIL/Pillow not available",
                "solution": "Install Pillow in ComfyUI venv: /runpod-volume/ComfyUI/venv/bin/pip install pillow"
            }
        
        # Validate input
        if 'input' not in event:
            return {
                "status": "error", 
                "job_id": job_id,
                "error_message": "Missing 'input' field"
            }
        
        input_data = event['input']
        input_type = input_data.get('type')
        data = input_data.get('data')
        
        if not input_type or not data:
            return {
                "status": "error",
                "job_id": job_id, 
                "error_message": "Missing input type or data"
            }
        
        # Process input
        temp_dir = f"/tmp/{job_id}"
        os.makedirs(temp_dir, exist_ok=True)
        input_path = f"{temp_dir}/input.jpg"
        
        if input_type == 'base64':
            # Handle base64
            if data.startswith('data:image'):
                data = data.split(',')[1]
            
            # Fix padding
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            
            # Decode and save
            image_bytes = base64.b64decode(data)
            with open(input_path, 'wb') as f:
                f.write(image_bytes)
                
        elif input_type == 'url':
            # Handle URL
            if requests is None:
                return {
                    "status": "error",
                    "job_id": job_id,
                    "error_message": "Requests not available for URL downloads"
                }
            
            response = requests.get(data, timeout=30)
            response.raise_for_status()
            with open(input_path, 'wb') as f:
                f.write(response.content)
        
        # Validate image
        try:
            with Image.open(input_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    img.save(input_path, 'JPEG', quality=95)
                logger.info(f"✅ Image processed: {img.size}")
        except Exception as e:
            return {
                "status": "error",
                "job_id": job_id,
                "error_message": f"Invalid image: {e}"
            }
        
        # Try to import and run workflow
        try:
            from realism import main as realism_workflow
            logger.info("✅ Realism workflow imported")
            
            # Run workflow
            results = realism_workflow(
                input_image_path=os.path.basename(input_path),
                detail_amount=event.get('parameters', {}).get('detail_amount', 0.7),
                upscale_factor=event.get('parameters', {}).get('upscale_factor', 4)
            )
            
            # Convert results to base64
            output_variants = event.get('parameters', {}).get('output_variants', ['final_resized'])
            outputs = {}
            
            for variant_name, tensor_data in results.items():
                if variant_name in output_variants:
                    # Save tensor as image
                    output_path = f"{temp_dir}/{variant_name}.jpg"
                    
                    # Convert tensor to image
                    if hasattr(tensor_data, 'cpu'):
                        if tensor_data.dim() == 4:
                            tensor_data = tensor_data.squeeze(0)
                        numpy_array = tensor_data.cpu().numpy()
                        if numpy_array.max() <= 1.0:
                            numpy_array = (numpy_array * 255).astype('uint8')
                        img = Image.fromarray(numpy_array.astype('uint8'))
                        img.save(output_path, 'JPEG', quality=95)
                        
                        # Convert to base64
                        with open(output_path, 'rb') as f:
                            img_bytes = f.read()
                        base64_data = base64.b64encode(img_bytes).decode('utf-8')
                        outputs[variant_name] = f"data:image/jpeg;base64,{base64_data}"
            
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "job_id": job_id,
                "processing_time": round(processing_time, 2),
                "outputs": outputs
            }
            
        except ImportError as e:
            return {
                "status": "error",
                "job_id": job_id,
                "error_message": f"Cannot import realism workflow: {e}",
                "solution": "Ensure ComfyUI is properly mounted at /runpod-volume/ComfyUI/"
            }
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ [{job_id}] Error: {e}")
        
        return {
            "status": "error",
            "job_id": job_id,
            "error_message": str(e),
            "processing_time": round(processing_time, 2)
        }
    
    finally:
        # Cleanup
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass


if __name__ == "__main__":
    # Test
    test_event = {
        "input": {
            "type": "url",
            "data": "https://via.placeholder.com/512x512.jpg"
        },
        "parameters": {
            "detail_amount": 0.7,
            "output_variants": ["final_resized"]
        }
    }
    
    result = handler(test_event)
    print(json.dumps(result, indent=2))
