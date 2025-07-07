#!/usr/bin/env python3
"""
RunPod Diagnostics Script
This script collects diagnostic information about the RunPod environment
and logs it to both console and a file for debugging.
"""

import os
import sys
import json
import time
import traceback
import logging
import platform
import tempfile
import glob
from datetime import datetime

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("RunPodDiagnostics")

# Add file handler
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"runpod_diagnostics_{timestamp}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(file_handler)

def log_system_info():
    """Log basic system information"""
    logger.info("=== System Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Current user: {os.getuid()}:{os.getgid()}")
    
    # Environment variables
    logger.info("=== Environment Variables ===")
    for key, value in sorted(os.environ.items()):
        if 'KEY' in key.upper() or 'SECRET' in key.upper() or 'TOKEN' in key.upper() or 'PASSWORD' in key.upper():
            logger.info(f"{key}=***REDACTED***")
        else:
            logger.info(f"{key}={value}")

def log_directory_structure():
    """Log directory structure"""
    logger.info("=== Directory Structure ===")
    
    dirs_to_check = [
        ".",
        "input",
        "output",
        "logs",
        "custom_nodes",
        "ComfyUI",
        "/runpod-volume",
        "/runpod-volume/ComfyUI",
        "/runpod-volume/ComfyUI/input",
        "/runpod-volume/ComfyUI/output",
        "/runpod-volume/logs",
    ]
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path):
            logger.info(f"Directory {dir_path}: exists")
            try:
                contents = os.listdir(dir_path)
                logger.info(f"  Contents ({len(contents)} items): {contents[:10]}{'...' if len(contents) > 10 else ''}")
                
                # If it's a key directory, check permissions
                if dir_path in ["input", "output", "logs", "/runpod-volume/ComfyUI/input", "/runpod-volume/ComfyUI/output"]:
                    try:
                        test_file = os.path.join(dir_path, f"test_write_{timestamp}.txt")
                        with open(test_file, 'w') as f:
                            f.write("Test write access")
                        logger.info(f"  Write test: SUCCESS - Created {test_file}")
                        os.remove(test_file)
                        logger.info(f"  Delete test: SUCCESS - Removed {test_file}")
                    except Exception as e:
                        logger.error(f"  Permission test failed: {e}")
            except Exception as e:
                logger.error(f"  Error listing directory: {e}")
        else:
            logger.info(f"Directory {dir_path}: does not exist")

def check_python_modules():
    """Check for required Python modules"""
    logger.info("=== Python Module Check ===")
    
    modules_to_check = [
        "numpy",
        "torch",
        "boto3",
        "PIL",
        "asyncio",
        "gc",
        "tempfile",
        "shutil",
        "json",
        "logging",
        "traceback",
    ]
    
    for module_name in modules_to_check:
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "unknown version")
            logger.info(f"{module_name}: OK - {version}")
            
            # Additional info for key modules
            if module_name == "torch":
                logger.info(f"  CUDA available: {module.cuda.is_available()}")
                if module.cuda.is_available():
                    logger.info(f"  CUDA device: {module.cuda.get_device_name(0)}")
                    logger.info(f"  CUDA version: {module.version.cuda}")
            elif module_name == "numpy":
                logger.info(f"  NumPy config: {module.__config__.split()}")
            
        except ImportError:
            logger.error(f"{module_name}: MISSING")
        except Exception as e:
            logger.error(f"{module_name}: ERROR - {e}")

def check_b2_config():
    """Check B2 configuration"""
    logger.info("=== B2 Configuration Check ===")
    
    try:
        # Check if b2_config.py exists
        if not os.path.exists("b2_config.py"):
            logger.error("b2_config.py: MISSING")
            return
            
        logger.info("b2_config.py: EXISTS")
        
        # Try to import and use functions
        try:
            from b2_config import get_b2_config
            config = get_b2_config()
            logger.info(f"get_b2_config(): OK - Keys: {list(config.keys())}")
            
            # Check if we can create an S3 client
            try:
                from b2_config import get_b2_s3_client
                client = get_b2_s3_client()
                logger.info("get_b2_s3_client(): OK")
                
                # Try to list objects
                try:
                    bucket_name = config["B2_IMAGE_BUCKET_NAME"]
                    response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=3)
                    
                    if 'Contents' in response:
                        objects = [obj['Key'] for obj in response['Contents']]
                        logger.info(f"list_objects_v2(): OK - Found {len(objects)} objects")
                        logger.info(f"  Sample objects: {objects[:3]}")
                    else:
                        logger.warning(f"list_objects_v2(): WARNING - Bucket appears empty")
                        
                except Exception as e:
                    logger.error(f"list_objects_v2(): ERROR - {e}")
                    
            except Exception as e:
                logger.error(f"get_b2_s3_client(): ERROR - {e}")
                
        except Exception as e:
            logger.error(f"get_b2_config(): ERROR - {e}")
            
    except Exception as e:
        logger.error(f"B2 config check failed: {e}")

def check_image_loading():
    """Check image loading functionality"""
    logger.info("=== Image Loading Check ===")
    
    try:
        # Check if realism.py exists
        if not os.path.exists("realism.py"):
            logger.error("realism.py: MISSING")
            return
            
        logger.info("realism.py: EXISTS")
        
        # Try to import and use functions
        try:
            from realism import load_image_from_config
            
            # Try with default test image
            test_image = "1023_mark.jpg"
            logger.info(f"Testing load_image_from_config() with image: {test_image}")
            
            try:
                result = load_image_from_config(test_image)
                logger.info(f"load_image_from_config(): OK - Result: {result}")
                
                # Check if the result exists in the input directory
                input_dir = os.path.join(os.getcwd(), "input")
                if os.path.exists(input_dir):
                    if isinstance(result, str):
                        image_path = os.path.join(input_dir, result)
                        if os.path.exists(image_path):
                            logger.info(f"Image exists at: {image_path} ({os.path.getsize(image_path)} bytes)")
                        else:
                            logger.error(f"Image does not exist at: {image_path}")
                    else:
                        logger.warning(f"Unexpected result type: {type(result)}")
                
            except Exception as e:
                logger.error(f"load_image_from_config(): ERROR - {e}")
                logger.error(traceback.format_exc())
                
        except Exception as e:
            logger.error(f"Import load_image_from_config: ERROR - {e}")
            
    except Exception as e:
        logger.error(f"Image loading check failed: {e}")

def check_custom_nodes():
    """Check custom nodes functionality"""
    logger.info("=== Custom Nodes Check ===")
    
    try:
        # Check if realism.py exists
        if not os.path.exists("realism.py"):
            logger.error("realism.py: MISSING")
            return
            
        logger.info("realism.py: EXISTS")
        
        # Try to import and use functions
        try:
            from realism import import_custom_nodes, NODE_CLASS_MAPPINGS
            
            logger.info(f"Before import: {len(NODE_CLASS_MAPPINGS)} nodes available")
            
            try:
                import_custom_nodes()
                logger.info(f"After import: {len(NODE_CLASS_MAPPINGS)} nodes available")
                
                # List some node names
                node_names = list(NODE_CLASS_MAPPINGS.keys())
                sample_nodes = node_names[:min(10, len(node_names))]
                logger.info(f"Sample nodes: {sample_nodes}")
                
            except Exception as e:
                logger.error(f"import_custom_nodes(): ERROR - {e}")
                logger.error(traceback.format_exc())
                
        except Exception as e:
            logger.error(f"Import custom nodes: ERROR - {e}")
            
    except Exception as e:
        logger.error(f"Custom nodes check failed: {e}")

def main():
    """Run all diagnostic checks"""
    logger.info(f"=== RunPod Diagnostics Started at {datetime.now().isoformat()} ===")
    
    checks = [
        log_system_info,
        log_directory_structure,
        check_python_modules,
        check_b2_config,
        check_image_loading,
        check_custom_nodes
    ]
    
    for check in checks:
        try:
            check()
        except Exception as e:
            logger.error(f"Check {check.__name__} failed with error: {e}")
            logger.error(traceback.format_exc())
    
    logger.info(f"=== RunPod Diagnostics Completed at {datetime.now().isoformat()} ===")
    logger.info(f"Log file: {os.path.abspath(log_file)}")

if __name__ == "__main__":
    main() 