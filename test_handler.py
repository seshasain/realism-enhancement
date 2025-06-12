#!/usr/bin/env python3
"""
Test script for the RunPod serverless handler
"""

import json
import base64
import time
from handler import handler


def create_test_base64_image():
    """Create a simple test image as base64."""
    from PIL import Image
    import io
    
    # Create a simple test image
    img = Image.new('RGB', (512, 512), color='red')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_bytes = buffer.getvalue()
    
    base64_data = base64.b64encode(img_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_data}"


def test_basic_functionality():
    """Test basic handler functionality."""
    print("🧪 Testing basic functionality...")
    
    test_event = {
        "input": {
            "type": "base64",
            "data": create_test_base64_image()
        },
        "parameters": {
            "detail_amount": 0.7,
            "upscale_factor": 4,
            "output_variants": ["final_resized"]
        }
    }
    
    start_time = time.time()
    result = handler(test_event)
    end_time = time.time()
    
    print(f"⏱️  Processing time: {end_time - start_time:.2f} seconds")
    print(f"📊 Result status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'success':
        print("✅ Test passed!")
        print(f"🖼️  Generated {len(result.get('outputs', {}))} output images")
        for variant in result.get('outputs', {}):
            print(f"   - {variant}")
    else:
        print("❌ Test failed!")
        print(f"Error: {result.get('error_message', 'Unknown error')}")
    
    return result


def test_input_validation():
    """Test input validation."""
    print("\n🔍 Testing input validation...")
    
    # Test missing input
    test_cases = [
        {
            "name": "Missing input field",
            "event": {"parameters": {"detail_amount": 0.7}},
            "should_fail": True
        },
        {
            "name": "Invalid input type",
            "event": {
                "input": {"type": "invalid", "data": "test"},
                "parameters": {"detail_amount": 0.7}
            },
            "should_fail": True
        },
        {
            "name": "Invalid detail_amount",
            "event": {
                "input": {"type": "base64", "data": create_test_base64_image()},
                "parameters": {"detail_amount": 5.0}
            },
            "should_fail": True
        },
        {
            "name": "Valid minimal request",
            "event": {
                "input": {"type": "base64", "data": create_test_base64_image()}
            },
            "should_fail": False
        }
    ]
    
    for test_case in test_cases:
        print(f"  Testing: {test_case['name']}")
        result = handler(test_case['event'])
        
        if test_case['should_fail']:
            if result.get('status') == 'error':
                print(f"    ✅ Correctly failed: {result.get('error_message', 'Unknown error')}")
            else:
                print(f"    ❌ Should have failed but didn't")
        else:
            if result.get('status') == 'success':
                print(f"    ✅ Correctly succeeded")
            else:
                print(f"    ❌ Should have succeeded: {result.get('error_message', 'Unknown error')}")


def test_url_input():
    """Test URL input (requires internet connection)."""
    print("\n🌐 Testing URL input...")
    
    # Use a sample image URL (you can replace with your own)
    test_url = "https://via.placeholder.com/512x512.jpg"
    
    test_event = {
        "input": {
            "type": "url",
            "data": test_url
        },
        "parameters": {
            "detail_amount": 0.5,
            "output_variants": ["final_resized"]
        }
    }
    
    try:
        result = handler(test_event)
        if result.get('status') == 'success':
            print("✅ URL input test passed!")
        else:
            print(f"❌ URL input test failed: {result.get('error_message', 'Unknown error')}")
    except Exception as e:
        print(f"⚠️  URL input test skipped (no internet or invalid URL): {e}")


def test_multiple_outputs():
    """Test multiple output variants."""
    print("\n🖼️  Testing multiple output variants...")
    
    test_event = {
        "input": {
            "type": "base64",
            "data": create_test_base64_image()
        },
        "parameters": {
            "detail_amount": 0.7,
            "output_variants": ["comparison", "final_resized", "final_hires"]
        }
    }
    
    result = handler(test_event)
    
    if result.get('status') == 'success':
        outputs = result.get('outputs', {})
        print(f"✅ Generated {len(outputs)} output variants:")
        for variant in outputs:
            print(f"   - {variant}")
    else:
        print(f"❌ Multiple outputs test failed: {result.get('error_message', 'Unknown error')}")


def main():
    """Run all tests."""
    print("🚀 Starting RunPod Handler Tests")
    print("=" * 50)
    
    try:
        # Basic functionality test
        test_basic_functionality()
        
        # Input validation tests
        test_input_validation()
        
        # URL input test
        test_url_input()
        
        # Multiple outputs test
        test_multiple_outputs()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
