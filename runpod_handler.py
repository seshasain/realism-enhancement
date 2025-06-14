import os
import sys
import shutil
from typing import Dict, Any
import json

# Set serverless mode flag
os.environ["RUNPOD_SERVERLESS"] = "true"

# Import after setting flag
import realism


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod serverless handler function
    
    Args:
        event (Dict): The event object containing the request data
            The expected format is:
            {
                "input": {
                    "image_id": "image_name.jpg"  # Image ID/name in B2 bucket
                }
            }
    
    Returns:
        Dict[str, Any]: Response object with processed image URLs
    """
    try:
        # Get input parameters
        input_data = event.get("input", {})
        image_id = input_data.get("image_id", "Asian+Man+1+Before.jpg")
        
        # Set up output directory in the volume
        output_dir = os.path.join("/runpod-volume", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process the image
        realism.main(image_id=image_id)
        
        # Collect output files
        output_files = []
        output_prefixes = [
            "RealSkin AI Lite Comparer Original Vs Final",
            "RealSkin AI Light Final Resized to Original Scale",
            "RealSkin AI Light Final Hi-Rez Output",
            "RealSkin AI Light First Hi-Rez Output"
        ]
        
        # Find the latest generated files in ComfyUI/output directory
        comfyui_output = os.path.join("/runpod-volume", "ComfyUI", "output")
        if os.path.exists(comfyui_output):
            for dirpath, dirnames, filenames in os.walk(comfyui_output):
                for filename in filenames:
                    for prefix in output_prefixes:
                        if filename.startswith(prefix):
                            src_path = os.path.join(dirpath, filename)
                            dst_path = os.path.join(output_dir, filename)
                            shutil.copy2(src_path, dst_path)
                            output_files.append({
                                "filename": filename,
                                "path": dst_path
                            })
        
        # Return results
        return {
            "output": {
                "status": "success",
                "message": f"Successfully processed image {image_id}",
                "output_files": output_files
            }
        }
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return {
            "output": {
                "status": "error",
                "message": str(e),
                "traceback": error_trace
            }
        }


# Test locally when run directly
if __name__ == "__main__":
    # Sample event for testing
    test_event = {
        "input": {
            "image_id": "Asian+Man+1+Before.jpg"
        }
    }
    
    result = handler(test_event)
    print(json.dumps(result, indent=2)) 