#!/usr/bin/env python
import os
import json
import sys

# Ensure we're using the network volume path
os.environ["RUNPOD_VOLUME_PATH"] = "/runpod-volume"

# Add the current directory to the path so we can import realism
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from realism import runpod_handler

def handler(event):
    """
    RunPod serverless handler function.
    
    Args:
        event: The event object from RunPod
        
    Returns:
        The response object for RunPod
    """
    # Call the handler from realism.py
    return runpod_handler(event)

if __name__ == "__main__":
    # Get the input from environment variable
    if "RUNPOD_INPUT" in os.environ:
        event = json.loads(os.environ["RUNPOD_INPUT"])
        result = handler(event)
        # Print result for RunPod to capture
        print(json.dumps(result))
    else:
        print("Error: RUNPOD_INPUT environment variable not found")
        sys.exit(1) 