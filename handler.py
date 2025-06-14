#!/usr/bin/env python
import os
import json
import sys
import traceback
import datetime

def log(message):
    """Print a timestamped log message"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

log("Handler script starting")

# Ensure we're using the network volume path
os.environ["RUNPOD_VOLUME_PATH"] = "/runpod-volume"
log(f"Set RUNPOD_VOLUME_PATH to {os.environ['RUNPOD_VOLUME_PATH']}")

# Add the current directory to the path so we can import realism
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
log(f"Added {current_dir} to Python path")

# Check directory contents
log(f"Files in current directory ({current_dir}):")
try:
    for file in os.listdir(current_dir):
        log(f"  - {file}")
except Exception as e:
    log(f"Error listing directory: {e}")

# Check if realism.py exists
realism_path = os.path.join(current_dir, "realism.py")
if os.path.exists(realism_path):
    log(f"realism.py found at {realism_path}")
else:
    log(f"ERROR: realism.py not found at {realism_path}")

# Try to import realism
try:
    log("Importing realism module...")
    from realism import runpod_handler
    log("Successfully imported realism module")
except ImportError as e:
    log(f"ERROR importing realism module: {e}")
    log(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

def handler(event):
    """
    RunPod serverless handler function.
    
    Args:
        event: The event object from RunPod
        
    Returns:
        The response object for RunPod
    """
    log(f"Handler received event: {json.dumps(event)}")
    
    try:
        # Call the handler from realism.py
        log("Calling runpod_handler from realism.py")
        result = runpod_handler(event)
        log(f"Handler completed successfully, returning result")
        return result
    except Exception as e:
        log(f"ERROR in handler: {e}")
        log(f"Traceback: {traceback.format_exc()}")
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    log("Script running in main mode")
    
    # Get the input from environment variable
    if "RUNPOD_INPUT" in os.environ:
        log("Found RUNPOD_INPUT environment variable")
        try:
            event = json.loads(os.environ["RUNPOD_INPUT"])
            log(f"Parsed input: {json.dumps(event)}")
            
            result = handler(event)
            
            # Print result for RunPod to capture
            log("Handler execution complete, printing result")
            print(json.dumps(result))
        except json.JSONDecodeError as e:
            log(f"ERROR: Failed to parse RUNPOD_INPUT as JSON: {e}")
            sys.exit(1)
        except Exception as e:
            log(f"Unexpected error: {e}")
            log(f"Traceback: {traceback.format_exc()}")
            sys.exit(1)
    else:
        log("ERROR: RUNPOD_INPUT environment variable not found")
        sys.exit(1)
        
    log("Handler script completed") 