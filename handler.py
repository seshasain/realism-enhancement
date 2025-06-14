#!/usr/bin/env python3
"""
RunPod Serverless Handler for realism.py module
Wraps the existing working realism module for serverless execution
"""

import os
import sys
import json
import tempfile
import traceback
from pathlib import Path
import runpod


def setup_environment():
    """
    Set up the environment to match the working pod environment.
    This replicates the exact conditions where 'python -m realism' works.
    """
    # Set working directory to ComfyUI location
    comfyui_path = "/runpod-volume/ComfyUI"
    
    if os.path.exists(comfyui_path):
        os.chdir(comfyui_path)
        print(f"✅ Changed working directory to: {comfyui_path}")
    else:
        print(f"⚠️ ComfyUI path not found: {comfyui_path}")
        # Fallback to current directory
        comfyui_path = os.getcwd()
        print(f"📁 Using current directory: {comfyui_path}")
    
    # Add ComfyUI to Python path (replicates the module environment)
    if comfyui_path not in sys.path:
        sys.path.insert(0, comfyui_path)
        print(f"✅ Added to Python path: {comfyui_path}")
    
    # Set environment variables that might be needed
    os.environ['PYTHONPATH'] = f"{comfyui_path}:{os.environ.get('PYTHONPATH', '')}"
    
    return comfyui_path


def validate_environment():
    """
    Validate that the environment is set up correctly.
    """
    print("🔍 Validating environment...")
    
    # Check if realism.py exists
    realism_path = os.path.join(os.getcwd(), "realism.py")
    if os.path.exists(realism_path):
        print(f"✅ Found realism.py at: {realism_path}")
    else:
        print(f"❌ realism.py not found at: {realism_path}")
        return False
    
    # Check if b2_config.py exists
    b2_config_path = os.path.join(os.getcwd(), "b2_config.py")
    if os.path.exists(b2_config_path):
        print(f"✅ Found b2_config.py at: {b2_config_path}")
    else:
        print(f"⚠️ b2_config.py not found at: {b2_config_path}")
    
    # Check for ComfyUI directories
    required_dirs = ["nodes", "models", "custom_nodes"]
    for dir_name in required_dirs:
        dir_path = os.path.join(os.getcwd(), dir_name)
        if os.path.exists(dir_path):
            print(f"✅ Found {dir_name} directory")
        else:
            print(f"⚠️ {dir_name} directory not found")
    
    return True


def load_realism_module():
    """
    Import the realism module dynamically.
    This replicates 'python -m realism' behavior.
    """
    try:
        print("📦 Importing realism module...")
        
        # Import the realism module
        import realism
        print("✅ Successfully imported realism module")
        
        return realism
    
    except ImportError as e:
        print(f"❌ Failed to import realism module: {e}")
        print("📋 Python path:")
        for path in sys.path:
            print(f"  - {path}")
        raise
    
    except Exception as e:
        print(f"❌ Unexpected error importing realism: {e}")
        traceback.print_exc()
        raise


def process_image(image_id, realism_module):
    """
    Process an image using the realism module.
    
    Args:
        image_id (str): The image ID to process
        realism_module: The imported realism module
        
    Returns:
        dict: Processing results
    """
    try:
        print(f"🖼️ Processing image: {image_id}")
        
        # Call the main function from realism module with the image_id
        # This replicates: python -m realism --image-id "image_id"
        result = realism_module.main(image_id=image_id)
        
        print(f"✅ Image processing completed successfully")
        return {
            "status": "success",
            "image_id": image_id,
            "message": "Image processed successfully"
        }
        
    except FileNotFoundError as e:
        print(f"❌ Image not found: {e}")
        return {
            "status": "error",
            "error_type": "image_not_found",
            "message": f"Image '{image_id}' not found in storage",
            "image_id": image_id
        }
    
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "error_type": "processing_error",
            "message": str(e),
            "image_id": image_id
        }


def find_output_images():
    """
    Find the generated output images and return their paths/URLs.
    
    Returns:
        list: List of output image information
    """
    output_images = []
    
    # Common ComfyUI output directories
    output_dirs = [
        "output",
        "outputs", 
        "temp",
        "/tmp"
    ]
    
    # Look for recently created images
    import glob
    from datetime import datetime, timedelta
    
    # Look for images created in the last few minutes
    recent_time = datetime.now() - timedelta(minutes=5)
    
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            # Find recent image files
            for pattern in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                files = glob.glob(os.path.join(output_dir, "**", pattern), recursive=True)
                
                for file_path in files:
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time > recent_time:
                            # This is a recent output file
                            file_size = os.path.getsize(file_path)
                            output_images.append({
                                "path": file_path,
                                "filename": os.path.basename(file_path),
                                "size": file_size,
                                "created": file_time.isoformat()
                            })
                    except Exception as e:
                        print(f"⚠️ Error checking file {file_path}: {e}")
    
    return output_images


def upload_output_to_storage(output_images):
    """
    Upload output images to accessible storage and return URLs.
    
    Args:
        output_images (list): List of output image information
        
    Returns:
        list: List of accessible URLs
    """
    urls = []
    
    try:
        # Import B2 config if available
        import b2_config
        
        for img_info in output_images:
            try:
                # Upload to B2 storage
                file_path = img_info["path"]
                filename = img_info["filename"]
                
                # Upload file and get URL
                url = b2_config.upload_file_to_b2(file_path, filename)
                urls.append({
                    "filename": filename,
                    "url": url,
                    "size": img_info["size"]
                })
                
                print(f"✅ Uploaded {filename} to: {url}")
                
            except Exception as e:
                print(f"❌ Failed to upload {img_info['filename']}: {e}")
    
    except ImportError:
        print("⚠️ B2 config not available, cannot upload outputs")
        # Return local paths as fallback
        for img_info in output_images:
            urls.append({
                "filename": img_info["filename"],
                "url": f"file://{img_info['path']}",
                "size": img_info["size"]
            })
    
    return urls


def handler(event):
    """
    Main serverless handler function.
    
    Args:
        event (dict): Input event containing image_id
        
    Returns:
        dict: Response with processed image URLs
    """
    print("🚀 RunPod Serverless Handler Started")
    print(f"📥 Input event: {json.dumps(event, indent=2)}")
    
    try:
        # Extract image_id from input
        input_data = event.get("input", {})
        image_id = input_data.get("image_id")
        
        if not image_id:
            return {
                "error": "Missing required parameter 'image_id'",
                "status": "error"
            }
        
        print(f"🎯 Processing image ID: {image_id}")
        
        # Set up environment (replicates pod environment)
        comfyui_path = setup_environment()
        
        # Validate environment
        if not validate_environment():
            return {
                "error": "Environment validation failed",
                "status": "error"
            }
        
        # Load realism module
        realism_module = load_realism_module()
        
        # Process the image
        process_result = process_image(image_id, realism_module)
        
        if process_result["status"] == "error":
            return process_result
        
        # Find output images
        output_images = find_output_images()
        print(f"📸 Found {len(output_images)} output images")
        
        # Upload outputs and get URLs
        output_urls = upload_output_to_storage(output_images)
        
        # Return success response
        response = {
            "status": "success",
            "image_id": image_id,
            "output_images": output_urls,
            "processing_info": process_result,
            "total_outputs": len(output_urls)
        }
        
        print(f"✅ Handler completed successfully")
        print(f"📤 Response: {json.dumps(response, indent=2)}")
        
        return response
        
    except Exception as e:
        error_response = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        print(f"❌ Handler failed: {e}")
        print(f"📤 Error response: {json.dumps(error_response, indent=2)}")
        
        return error_response


if __name__ == "__main__":
    # For local testing
    test_event = {
        "input": {
            "image_id": "Asian+Man+1+Before.jpg"
        }
    }
    
    result = handler(test_event)
    print(f"Test result: {json.dumps(result, indent=2)}")


# RunPod serverless wrapper
runpod.serverless.start({"handler": handler})
