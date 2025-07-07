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
logger = logging.getLogger("WorkerTest")

def test_imports():
    """Test importing critical modules"""
    logger.info("Testing critical imports...")
    
    try:
        import numpy
        logger.info(f"NumPy version: {numpy.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import NumPy: {e}")
    except Exception as e:
        logger.error(f"Error with NumPy: {e}")
        
    try:
        import torch
        logger.info(f"PyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
    except ImportError as e:
        logger.error(f"Failed to import PyTorch: {e}")
    except Exception as e:
        logger.error(f"Error with PyTorch: {e}")
        
    try:
        import boto3
        logger.info(f"boto3 version: {boto3.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import boto3: {e}")
    except Exception as e:
        logger.error(f"Error with boto3: {e}")

def test_b2_config():
    """Test B2 configuration"""
    logger.info("Testing B2 configuration...")
    
    try:
        from b2_config import get_b2_config, get_b2_s3_client
        
        config = get_b2_config()
        logger.info(f"B2 config loaded: {config.keys()}")
        
        client = get_b2_s3_client()
        logger.info(f"B2 client created successfully")
        
        # List objects in bucket
        bucket_name = config["B2_IMAGE_BUCKET_NAME"]
        response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        
        if 'Contents' in response:
            logger.info(f"Successfully listed objects in bucket {bucket_name}")
            logger.info(f"First few objects: {[obj['Key'] for obj in response['Contents'][:3]]}")
        else:
            logger.warning(f"Bucket {bucket_name} appears to be empty")
            
    except ImportError as e:
        logger.error(f"Failed to import B2 config: {e}")
    except Exception as e:
        logger.error(f"Error with B2 config: {e}")
        logger.error(traceback.format_exc())

def test_directories():
    """Test critical directories"""
    logger.info("Testing critical directories...")
    
    dirs_to_check = [
        ".",
        "input",
        "output",
        "custom_nodes",
        "ComfyUI",
        "/runpod-volume",
        "/runpod-volume/ComfyUI",
        "/runpod-volume/ComfyUI/input",
        "/runpod-volume/ComfyUI/output",
    ]
    
    for dir_path in dirs_to_check:
        exists = os.path.exists(dir_path)
        logger.info(f"Directory {dir_path}: {'exists' if exists else 'does not exist'}")
        
        if exists:
            try:
                contents = os.listdir(dir_path)
                logger.info(f"  Contents ({len(contents)} items): {contents[:5]}{'...' if len(contents) > 5 else ''}")
            except Exception as e:
                logger.error(f"  Error listing directory: {e}")

def test_download_image():
    """Test downloading an image from B2"""
    logger.info("Testing image download from B2...")
    
    try:
        from b2_config import download_file_from_b2
        import tempfile
        
        temp_dir = tempfile.mkdtemp()
        test_image = "1023_mark.jpg"  # Use the default test image
        local_path = os.path.join(temp_dir, test_image)
        
        logger.info(f"Downloading {test_image} to {local_path}")
        download_file_from_b2(test_image, local_path)
        
        if os.path.exists(local_path):
            size = os.path.getsize(local_path)
            logger.info(f"Download successful. File size: {size} bytes")
            
            # Try to copy to ComfyUI input directory
            input_dir = os.path.join(os.getcwd(), "input")
            os.makedirs(input_dir, exist_ok=True)
            
            import shutil
            comfyui_path = os.path.join(input_dir, test_image)
            shutil.copy2(local_path, comfyui_path)
            
            if os.path.exists(comfyui_path):
                logger.info(f"Successfully copied to ComfyUI input: {comfyui_path}")
            else:
                logger.error(f"Failed to copy to ComfyUI input")
        else:
            logger.error(f"Download failed. File does not exist.")
            
    except Exception as e:
        logger.error(f"Error in download test: {e}")
        logger.error(traceback.format_exc())

def test_custom_nodes_import():
    """Test importing custom nodes"""
    logger.info("Testing custom nodes import...")
    
    try:
        # First check if we're in the right directory
        if not os.path.exists("realism.py"):
            logger.error("realism.py not found in current directory")
            return
            
        # Import the function
        from realism import import_custom_nodes, NODE_CLASS_MAPPINGS
        
        # Try importing nodes
        logger.info(f"Before import: {len(NODE_CLASS_MAPPINGS)} nodes available")
        import_custom_nodes()
        logger.info(f"After import: {len(NODE_CLASS_MAPPINGS)} nodes available")
        
        # List some node names
        node_names = list(NODE_CLASS_MAPPINGS.keys())
        sample_nodes = node_names[:min(10, len(node_names))]
        logger.info(f"Sample nodes: {sample_nodes}")
        
    except Exception as e:
        logger.error(f"Error importing custom nodes: {e}")
        logger.error(traceback.format_exc())

def test_environment():
    """Test environment variables and system info"""
    logger.info("Testing environment...")
    
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"User: {os.getenv('USER')}")
    logger.info(f"HOME: {os.getenv('HOME')}")
    logger.info(f"PATH: {os.getenv('PATH')}")
    
    # Check for RunPod-specific environment variables
    runpod_vars = {k: v for k, v in os.environ.items() if 'RUNPOD' in k.upper()}
    logger.info(f"RunPod environment variables: {runpod_vars}")

def main():
    """Run all tests"""
    logger.info("=== Starting Worker Diagnostics ===")
    
    tests = [
        test_environment,
        test_imports,
        test_directories,
        test_b2_config,
        test_download_image,
        test_custom_nodes_import
    ]
    
    for test in tests:
        try:
            logger.info(f"\n{'='*50}\nRunning test: {test.__name__}\n{'='*50}")
            test()
        except Exception as e:
            logger.error(f"Test {test.__name__} failed with error: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("=== Worker Diagnostics Complete ===")

if __name__ == "__main__":
    main() 