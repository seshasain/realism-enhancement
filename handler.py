import os
import sys
import json
import base64
import uuid
import time
import traceback
import tempfile
import logging
from typing import Dict, Any, Optional
from PIL import Image
import torch
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add ComfyUI to path (from network volume)
comfyui_path = os.environ.get('COMFYUI_PATH', '/runpod-volume/ComfyUI')
sys.path.append(comfyui_path)

# Workflow will be imported dynamically in handler


def validate_input(event: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and extract input parameters from the event."""
    
    # Check required fields
    if 'input' not in event:
        raise ValueError("Missing 'input' field in request")
    
    input_data = event['input']
    
    # Validate input type and data
    if 'type' not in input_data or 'data' not in input_data:
        raise ValueError("Input must contain 'type' and 'data' fields")
    
    input_type = input_data['type']
    if input_type not in ['base64', 'url']:
        raise ValueError(f"Unsupported input type: {input_type}. Use 'base64' or 'url'")
    
    # Extract parameters with defaults
    parameters = event.get('parameters', {})
    detail_amount = parameters.get('detail_amount', 0.7)
    upscale_factor = parameters.get('upscale_factor', 4)
    output_variants = parameters.get('output_variants', ['final_resized'])
    
    # Validate parameters
    if not 0.1 <= detail_amount <= 2.0:
        raise ValueError("detail_amount must be between 0.1 and 2.0")
    
    if upscale_factor not in [2, 4]:
        raise ValueError("upscale_factor must be 2 or 4")
    
    valid_variants = ['comparison', 'final_resized', 'final_hires', 'first_hires']
    for variant in output_variants:
        if variant not in valid_variants:
            raise ValueError(f"Invalid output variant: {variant}. Valid options: {valid_variants}")
    
    return {
        'input_type': input_type,
        'input_data': input_data['data'],
        'detail_amount': detail_amount,
        'upscale_factor': upscale_factor,
        'output_variants': output_variants
    }


def process_input_image(input_type: str, input_data: str, job_id: str) -> str:
    """Process input image and save to temporary file."""
    
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    input_path = os.path.join(temp_dir, "input.jpg")
    
    try:
        if input_type == 'base64':
            # Handle base64 input
            if input_data.startswith('data:image'):
                # Remove data URL prefix
                base64_data = input_data.split(',')[1]
            else:
                base64_data = input_data
            
            # Decode base64
            image_bytes = base64.b64decode(base64_data)
            
            # Validate and save image
            with open(input_path, 'wb') as f:
                f.write(image_bytes)
            
            # Validate image can be opened
            with Image.open(input_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    img.save(input_path, 'JPEG', quality=95)
                
                # Check image dimensions
                width, height = img.size
                if width < 256 or height < 256:
                    raise ValueError(f"Image too small: {width}x{height}. Minimum 256x256")
                if width > 4096 or height > 4096:
                    raise ValueError(f"Image too large: {width}x{height}. Maximum 4096x4096")
        
        elif input_type == 'url':
            # Handle URL input
            import requests
            response = requests.get(input_data, timeout=30)
            response.raise_for_status()
            
            with open(input_path, 'wb') as f:
                f.write(response.content)
            
            # Validate image
            with Image.open(input_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    img.save(input_path, 'JPEG', quality=95)
        
        return input_path
        
    except Exception as e:
        raise ValueError(f"Failed to process input image: {str(e)}")


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string."""
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"
    
    except Exception as e:
        raise ValueError(f"Failed to encode image to base64: {str(e)}")


def save_tensor_as_image(tensor_data, output_path: str) -> str:
    """Save ComfyUI tensor output as image file."""
    try:
        # Convert tensor to numpy array
        if isinstance(tensor_data, torch.Tensor):
            # ComfyUI tensors are typically in format [batch, height, width, channels]
            if tensor_data.dim() == 4:
                tensor_data = tensor_data.squeeze(0)  # Remove batch dimension
            
            # Convert to numpy and scale to 0-255
            numpy_array = tensor_data.cpu().numpy()
            if numpy_array.max() <= 1.0:
                numpy_array = (numpy_array * 255).astype(np.uint8)
            else:
                numpy_array = numpy_array.astype(np.uint8)
            
            # Create PIL image
            image = Image.fromarray(numpy_array)
            
            # Save as JPEG
            image.save(output_path, 'JPEG', quality=95)
            return output_path
        
        else:
            raise ValueError(f"Unexpected tensor type: {type(tensor_data)}")
    
    except Exception as e:
        raise ValueError(f"Failed to save tensor as image: {str(e)}")


def cleanup_temp_files(job_id: str):
    """Clean up temporary files for the job."""
    try:
        import shutil
        temp_dir = f"/tmp/{job_id}"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Failed to cleanup temp files: {e}")


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """Main RunPod serverless handler function."""

    job_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        logger.info(f"🚀 [{job_id}] Starting image enhancement request")
        logger.info(f"🐍 Python: {sys.version}")
        logger.info(f"📁 Working dir: {os.getcwd()}")
        logger.info(f"🖥️  GPU: {torch.cuda.get_device_name() if torch.cuda.is_available() else 'No GPU'}")

        # Check ComfyUI paths
        comfyui_paths = ['/runpod-volume/ComfyUI', '/workspace/ComfyUI']
        for path in comfyui_paths:
            if os.path.exists(path):
                logger.info(f"✅ Found ComfyUI at: {path}")
            else:
                logger.warning(f"❌ Missing: {path}")

        # Validate input
        validated_input = validate_input(event)
        logger.info(f"✅ [{job_id}] Input validated: {validated_input['input_type']}")

        # Process input image
        input_path = process_input_image(
            validated_input['input_type'],
            validated_input['input_data'],
            job_id
        )
        logger.info(f"✅ [{job_id}] Input image processed: {input_path}")

        # Import and run the realism workflow
        logger.info(f"🎨 [{job_id}] Starting realism workflow...")
        try:
            from realism import main as realism_workflow
            logger.info(f"✅ [{job_id}] Realism workflow imported")
        except ImportError as e:
            logger.error(f"❌ [{job_id}] Failed to import realism: {e}")
            logger.error("💡 SOLUTION: Ensure ComfyUI is mounted at /runpod-volume/ComfyUI/")
            raise ImportError(f"Cannot import realism workflow: {e}")

        workflow_results = realism_workflow(
            input_image_path=os.path.basename(input_path),
            detail_amount=validated_input['detail_amount'],
            upscale_factor=validated_input['upscale_factor']
        )
        logger.info(f"✅ [{job_id}] Workflow completed")

        # Process outputs
        temp_dir = f"/tmp/{job_id}"
        output_images = {}

        for variant_name, tensor_data in workflow_results.items():
            if variant_name in validated_input['output_variants']:
                output_path = os.path.join(temp_dir, f"{variant_name}.jpg")
                save_tensor_as_image(tensor_data, output_path)

                # Convert to base64
                base64_image = image_to_base64(output_path)
                output_images[variant_name] = base64_image
                logger.info(f"✅ [{job_id}] Processed output: {variant_name}")

        processing_time = time.time() - start_time

        # Prepare response
        response = {
            "status": "success",
            "job_id": job_id,
            "processing_time": round(processing_time, 2),
            "outputs": output_images,
            "metadata": {
                "detail_amount": validated_input['detail_amount'],
                "upscale_factor": validated_input['upscale_factor'],
                "variants_generated": list(output_images.keys())
            }
        }

        logger.info(f"🎉 [{job_id}] Request completed successfully in {processing_time:.2f}s")
        return response

    except Exception as e:
        processing_time = time.time() - start_time
        error_message = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"💥 [{job_id}] ERROR: {error_message}")
        logger.error(f"📋 [{job_id}] Traceback: {error_traceback}")

        # Provide specific solutions
        if "PIL" in error_message:
            logger.error("💡 SOLUTION: Install Pillow: pip install pillow")
        elif "ComfyUI" in error_message:
            logger.error("💡 SOLUTION: Ensure ComfyUI is mounted at /runpod-volume/ComfyUI/")
        elif "CUDA" in error_message:
            logger.error("💡 SOLUTION: Check GPU availability and VRAM usage")

        return {
            "status": "error",
            "job_id": job_id,
            "error_code": type(e).__name__,
            "error_message": error_message,
            "processing_time": round(processing_time, 2),
            "debug_info": {
                "comfyui_exists": os.path.exists('/runpod-volume/ComfyUI'),
                "gpu_available": torch.cuda.is_available(),
                "working_dir": os.getcwd()
            }
        }

    finally:
        # Always cleanup temp files
        logger.info(f"🧹 [{job_id}] Cleaning up...")
        cleanup_temp_files(job_id)


# For local testing
if __name__ == "__main__":
    # Test with a sample request
    test_event = {
        "input": {
            "type": "base64",
            "data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."  # Your base64 image
        },
        "parameters": {
            "detail_amount": 0.7,
            "upscale_factor": 4,
            "output_variants": ["final_resized"]
        }
    }
    
    result = handler(test_event)
    print(json.dumps(result, indent=2))
