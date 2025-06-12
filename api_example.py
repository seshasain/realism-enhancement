#!/usr/bin/env python3
"""
Example API client for the RunPod Realism Enhancement service
"""

import requests
import base64
import json
import time
from PIL import Image
import io


class RealismEnhancementClient:
    """Client for the RunPod Realism Enhancement API."""
    
    def __init__(self, endpoint_url: str, api_key: str):
        """
        Initialize the client.
        
        Args:
            endpoint_url: RunPod endpoint URL (e.g., https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run)
            api_key: Your RunPod API key
        """
        self.endpoint_url = endpoint_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
    
    def image_to_base64(self, image_path: str) -> str:
        """Convert local image file to base64 string."""
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"
    
    def base64_to_image(self, base64_data: str, output_path: str):
        """Save base64 image data to file."""
        # Remove data URL prefix if present
        if base64_data.startswith('data:image'):
            base64_data = base64_data.split(',')[1]
        
        image_bytes = base64.b64decode(base64_data)
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
    
    def enhance_image(self, 
                     image_path: str = None,
                     image_url: str = None,
                     base64_data: str = None,
                     detail_amount: float = 0.7,
                     upscale_factor: int = 4,
                     output_variants: list = None) -> dict:
        """
        Enhance an image using the RunPod service.
        
        Args:
            image_path: Path to local image file
            image_url: URL to image
            base64_data: Base64 encoded image data
            detail_amount: Enhancement intensity (0.1-2.0)
            upscale_factor: Upscaling factor (2 or 4)
            output_variants: List of desired output variants
        
        Returns:
            API response dictionary
        """
        if output_variants is None:
            output_variants = ["final_resized"]
        
        # Prepare input data
        if image_path:
            input_data = {
                "type": "base64",
                "data": self.image_to_base64(image_path)
            }
        elif image_url:
            input_data = {
                "type": "url",
                "data": image_url
            }
        elif base64_data:
            input_data = {
                "type": "base64",
                "data": base64_data
            }
        else:
            raise ValueError("Must provide either image_path, image_url, or base64_data")
        
        # Prepare request payload
        payload = {
            "input": input_data,
            "parameters": {
                "detail_amount": detail_amount,
                "upscale_factor": upscale_factor,
                "output_variants": output_variants
            }
        }
        
        # Make API request
        print(f"🚀 Sending request to RunPod...")
        start_time = time.time()
        
        response = requests.post(
            self.endpoint_url,
            headers=self.headers,
            json=payload,
            timeout=600  # 10 minutes timeout
        )
        
        end_time = time.time()
        print(f"⏱️  Request completed in {end_time - start_time:.2f} seconds")
        
        response.raise_for_status()
        return response.json()
    
    def save_outputs(self, api_response: dict, output_dir: str = "outputs"):
        """Save API response outputs to files."""
        import os
        
        if api_response.get('status') != 'success':
            print(f"❌ API request failed: {api_response.get('error_message', 'Unknown error')}")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        outputs = api_response.get('outputs', {})
        job_id = api_response.get('job_id', 'unknown')
        
        for variant_name, base64_data in outputs.items():
            output_path = os.path.join(output_dir, f"{job_id}_{variant_name}.jpg")
            self.base64_to_image(base64_data, output_path)
            print(f"💾 Saved {variant_name}: {output_path}")


def example_usage():
    """Example usage of the client."""
    
    # Configuration (replace with your actual values)
    ENDPOINT_URL = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run"
    API_KEY = "your-runpod-api-key"
    
    # Initialize client
    client = RealismEnhancementClient(ENDPOINT_URL, API_KEY)
    
    # Example 1: Enhance local image
    print("📸 Example 1: Enhancing local image...")
    try:
        result = client.enhance_image(
            image_path="path/to/your/image.jpg",
            detail_amount=0.7,
            upscale_factor=4,
            output_variants=["final_resized", "comparison"]
        )
        
        print(f"✅ Enhancement completed!")
        print(f"   Job ID: {result.get('job_id')}")
        print(f"   Processing time: {result.get('processing_time')}s")
        print(f"   Outputs: {list(result.get('outputs', {}).keys())}")
        
        # Save outputs
        client.save_outputs(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 2: Enhance image from URL
    print("\n🌐 Example 2: Enhancing image from URL...")
    try:
        result = client.enhance_image(
            image_url="https://example.com/portrait.jpg",
            detail_amount=0.5,
            output_variants=["final_resized"]
        )
        
        print(f"✅ Enhancement completed!")
        client.save_outputs(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 3: Batch processing
    print("\n📦 Example 3: Batch processing...")
    image_files = ["image1.jpg", "image2.jpg", "image3.jpg"]
    
    for i, image_file in enumerate(image_files):
        try:
            print(f"Processing {i+1}/{len(image_files)}: {image_file}")
            
            result = client.enhance_image(
                image_path=image_file,
                detail_amount=0.7,
                output_variants=["final_resized"]
            )
            
            client.save_outputs(result, output_dir=f"batch_outputs")
            print(f"✅ Completed {image_file}")
            
        except Exception as e:
            print(f"❌ Failed {image_file}: {e}")
        
        # Add delay between requests to avoid rate limiting
        time.sleep(2)


def create_test_image():
    """Create a test image for demonstration."""
    img = Image.new('RGB', (512, 512), color='lightblue')
    img.save('test_image.jpg', 'JPEG')
    print("📷 Created test_image.jpg for testing")


if __name__ == "__main__":
    print("🎨 RunPod Realism Enhancement API Client")
    print("=" * 50)
    
    # Create test image
    create_test_image()
    
    # Run examples (uncomment when you have valid credentials)
    # example_usage()
    
    print("\n📋 To use this client:")
    print("1. Replace ENDPOINT_URL with your RunPod endpoint")
    print("2. Replace API_KEY with your RunPod API key")
    print("3. Uncomment example_usage() call")
    print("4. Run: python api_example.py")
