#!/usr/bin/env python3
"""
Test script to verify B2 download functionality with the provided image ID.
"""

import os
import tempfile
import argparse
from b2_config import get_b2_config, download_file_from_b2


def load_image_from_config(image_id: str) -> str:
    """
    Load an image based on the provided image ID using B2 configuration.
    
    Args:
        image_id (str): The image identifier/filename to load
        
    Returns:
        str: Local path to the downloaded image
    """
    # Create a temporary directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    local_image_path = os.path.join(temp_dir, image_id)
    
    print(f"Attempting to download image: {image_id}")
    print(f"Target local path: {local_image_path}")
    
    try:
        # Download the image from B2 using the configuration
        download_file_from_b2(image_id, local_image_path)
        print(f"✅ Successfully downloaded image: {image_id} to {local_image_path}")
        
        # Check if file exists and get its size
        if os.path.exists(local_image_path):
            file_size = os.path.getsize(local_image_path)
            print(f"📁 File size: {file_size} bytes")
            return local_image_path
        else:
            raise FileNotFoundError(f"Downloaded file not found at {local_image_path}")
            
    except Exception as e:
        print(f"❌ Failed to download image {image_id}: {e}")
        # Fallback to local file if it exists
        if os.path.exists(image_id):
            print(f"🔄 Using local file: {image_id}")
            return image_id
        else:
            raise FileNotFoundError(f"Could not find image {image_id} locally or in B2 storage")


def test_b2_config():
    """Test B2 configuration."""
    print("🔧 Testing B2 configuration...")
    try:
        config = get_b2_config()
        print(f"✅ B2 Config loaded successfully:")
        print(f"   - Endpoint: {config['B2_ENDPOINT']}")
        print(f"   - Bucket: {config['B2_IMAGE_BUCKET_NAME']}")
        print(f"   - Access Key ID: {config['B2_ACCESS_KEY_ID'][:10]}...")

        # Test connection by trying to list bucket contents
        print("🔗 Testing B2 connection...")
        from b2_config import get_b2_s3_client
        s3_client = get_b2_s3_client()
        bucket_name = config['B2_IMAGE_BUCKET_NAME']

        # Try to list first few objects
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        if 'Contents' in response:
            print(f"✅ Connection successful! Found {len(response['Contents'])} objects in bucket")
            for obj in response['Contents'][:3]:  # Show first 3 objects
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("✅ Connection successful! Bucket is empty or no objects found")

        return True
    except Exception as e:
        print(f"❌ Failed to connect to B2: {e}")
        return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test B2 image download functionality')
    parser.add_argument('--image-id', type=str, default="3XYW7936QW7G6EKG1YAH4EK930.jpeg",
                       help='Image ID/filename to test download (default: 3XYW7936QW7G6EKG1YAH4EK930.jpeg)')
    args = parser.parse_args()
    
    print("🚀 Starting B2 download test...")
    print(f"📷 Image ID: {args.image_id}")
    print("-" * 50)
    
    # Test B2 configuration first
    if not test_b2_config():
        return 1
    
    print("-" * 50)
    
    # Test image download
    try:
        local_path = load_image_from_config(args.image_id)
        print(f"🎉 Test completed successfully!")
        print(f"📁 Image available at: {local_path}")
        return 0
    except Exception as e:
        print(f"💥 Test failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
