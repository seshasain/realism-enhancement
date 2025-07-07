#!/usr/bin/env python
import os
import sys
import logging
import traceback
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HandlerTest")

def create_mock_job():
    """Create a mock job for testing the handler"""
    return {
        "id": f"test-job-{int(time.time())}",
        "input": {
            "image_id": "1023_mark.jpg",
            "face_parsing": {
                'background': False, 'skin': False, 'nose': True, 'eye_g': True,
                'r_eye': True, 'l_eye': True, 'r_brow': False, 'l_brow': False,
                'r_ear': False, 'l_ear': False, 'mouth': False, 'u_lip': True,
                'l_lip': True, 'hair': False, 'hat': False, 'ear_r': False,
                'neck_l': False, 'neck': False, 'cloth': True
            }
        }
    }

def test_handler():
    """Test the RunPod handler function"""
    try:
        from realism import runpod_handler
        
        logger.info("Creating mock job...")
        mock_job = create_mock_job()
        logger.info(f"Mock job created: {mock_job}")
        
        logger.info("Calling handler function...")
        start_time = time.time()
        result = runpod_handler(mock_job)
        elapsed = time.time() - start_time
        
        logger.info(f"Handler completed in {elapsed:.2f} seconds")
        logger.info(f"Result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Handler test failed: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("=== Starting Handler Test ===")
    result = test_handler()
    logger.info("=== Handler Test Complete ===")
    print(json.dumps(result, indent=2)) 