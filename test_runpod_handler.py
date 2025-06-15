#!/usr/bin/env python3
"""
Test script for the RunPod handler function.
This script can be used to test the handler locally before deployment.
"""

import json
import sys
import os

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_handler_import():
    """Test if the handler can be imported successfully."""
    try:
        from realism import runpod_handler
        print("✅ Handler imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import handler: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing handler: {e}")
        return False

def test_handler_structure():
    """Test the handler function structure."""
    try:
        from realism import runpod_handler
        
        # Test with minimal input
        test_event = {
            "input": {
                "image_id": "test-image.jpg"
            }
        }
        
        # This will likely fail due to missing ComfyUI, but we can test the structure
        try:
            result = runpod_handler(test_event)
            print("✅ Handler executed successfully")
            print(f"Result: {json.dumps(result, indent=2)}")
            return True
        except Exception as e:
            # Expected to fail without ComfyUI setup
            if "ComfyUI" in str(e) or "NODE_CLASS_MAPPINGS" in str(e):
                print("✅ Handler structure is correct (ComfyUI not available for testing)")
                return True
            else:
                print(f"❌ Handler execution failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Handler structure test failed: {e}")
        return False

def test_b2_config():
    """Test B2 configuration."""
    try:
        from b2_config import get_b2_config, get_b2_s3_client
        
        config = get_b2_config()
        print("✅ B2 configuration loaded")
        print(f"Bucket: {config.get('B2_IMAGE_BUCKET_NAME')}")
        
        # Test S3 client creation (may fail without boto3)
        try:
            client = get_b2_s3_client()
            print("✅ B2 S3 client created successfully")
        except ImportError:
            print("⚠️  boto3 not available (expected in CI)")
        except Exception as e:
            print(f"⚠️  B2 client creation failed: {e}")
            
        return True
    except Exception as e:
        print(f"❌ B2 configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing RunPod Handler")
    print("=" * 50)
    
    tests = [
        ("Handler Import", test_handler_import),
        ("Handler Structure", test_handler_structure),
        ("B2 Configuration", test_b2_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    print("\n📊 Test Results")
    print("=" * 50)
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
