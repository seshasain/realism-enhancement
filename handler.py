#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import traceback
import importlib.util
import platform
from datetime import datetime

# Configure logging
LOG_DIR = "/runpod-volume/logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"handler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Set up logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("RunPodHandler")

def log_system_info():
    """Log detailed system information"""
    logger.info("=" * 50)
    logger.info("SYSTEM INFORMATION")
    logger.info("=" * 50)
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Current Working Directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {sys.path}")
    
    # Log environment variables
    logger.info("Environment Variables:")
    for key, value in os.environ.items():
        logger.info(f"  {key}: {value}")
    
    # Log directory structure
    logger.info("Directory Structure:")
    for root_dir in ["/runpod-volume", "/runpod-volume/ComfyUI"]:
        if os.path.exists(root_dir):
            logger.info(f"Contents of {root_dir}:")
            for item in os.listdir(root_dir):
                item_path = os.path.join(root_dir, item)
                item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                logger.info(f"  {item_type}: {item}")

def check_imports():
    """Test importing critical modules"""
    logger.info("=" * 50)
    logger.info("TESTING CRITICAL IMPORTS")
    logger.info("=" * 50)
    
    modules_to_check = [
        "numpy", "torch", "runpod", "boto3", "PIL", 
        "requests", "tqdm", "json", "os", "sys"
    ]
    
    for module_name in modules_to_check:
        try:
            module = __import__(module_name)
            if module_name == "numpy":
                logger.info(f"✅ Successfully imported {module_name} version: {module.__version__}")
            elif module_name == "torch":
                logger.info(f"✅ Successfully imported {module_name} version: {module.__version__}")
                logger.info(f"   CUDA available: {module.cuda.is_available()}")
                if module.cuda.is_available():
                    logger.info(f"   CUDA version: {module.version.cuda}")
                    logger.info(f"   GPU count: {module.cuda.device_count()}")
                    for i in range(module.cuda.device_count()):
                        logger.info(f"   GPU {i}: {module.cuda.get_device_name(i)}")
            else:
                version = getattr(module, "__version__", "unknown")
                logger.info(f"✅ Successfully imported {module_name} version: {version}")
        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error checking {module_name}: {str(e)}")

def import_handler():
    """Attempt to import the runpod_handler function"""
    logger.info("=" * 50)
    logger.info("ATTEMPTING TO IMPORT HANDLER")
    logger.info("=" * 50)
    
    # Paths to try for importing the handler
    paths_to_try = [
        "/runpod-volume",
        "/runpod-volume/ComfyUI",
        "."
    ]
    
    handler_module_names = [
        "realism",
    ]
    
    handler_found = False
    
    for path in paths_to_try:
        if path not in sys.path and os.path.exists(path):
            sys.path.append(path)
            logger.info(f"Added {path} to sys.path")
    
    for module_name in handler_module_names:
        try:
            logger.info(f"Attempting to import {module_name}...")
            
            # Check if the file exists first
            for path in paths_to_try:
                module_path = os.path.join(path, f"{module_name}.py")
                if os.path.exists(module_path):
                    logger.info(f"Found module file at: {module_path}")
                    
                    # Try to import the module
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "runpod_handler"):
                            logger.info(f"✅ Successfully imported runpod_handler from {module_name} at {module_path}")
                            handler_found = True
                            return module.runpod_handler
                        else:
                            logger.warning(f"Module {module_name} found but does not contain runpod_handler function")
            
            if not handler_found:
                # Try direct import
                module = __import__(module_name)
                if hasattr(module, "runpod_handler"):
                    logger.info(f"✅ Successfully imported runpod_handler from {module_name} via direct import")
                    handler_found = True
                    return module.runpod_handler
                else:
                    logger.warning(f"Module {module_name} imported but does not contain runpod_handler function")
                
        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error importing {module_name}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    if not handler_found:
        logger.error("❌ Could not find runpod_handler in any module")
        return None

def check_b2_config():
    """Check if B2 configuration is available and valid"""
    logger.info("=" * 50)
    logger.info("CHECKING B2 CONFIGURATION")
    logger.info("=" * 50)
    
    try:
        # Try to import b2_config
        for path in ["/runpod-volume", "/runpod-volume/ComfyUI", "."]:
            config_path = os.path.join(path, "b2_config.py")
            if os.path.exists(config_path):
                logger.info(f"Found b2_config.py at: {config_path}")
                
                # Try to import the module
                spec = importlib.util.spec_from_file_location("b2_config", config_path)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Check for required attributes
                    required_attrs = ["application_key_id", "application_key", "bucket_name"]
                    missing_attrs = [attr for attr in required_attrs if not hasattr(module, attr)]
                    
                    if not missing_attrs:
                        logger.info("✅ B2 configuration found and contains required attributes")
                        return True
                    else:
                        logger.warning(f"B2 configuration is missing attributes: {', '.join(missing_attrs)}")
                        return False
        
        logger.warning("❌ Could not find b2_config.py")
        return False
    
    except Exception as e:
        logger.error(f"❌ Error checking B2 configuration: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def start_runpod_serverless():
    """Start the RunPod serverless handler"""
    logger.info("=" * 50)
    logger.info("STARTING RUNPOD SERVERLESS")
    logger.info("=" * 50)
    
    handler_func = import_handler()
    
    if handler_func:
        try:
            logger.info("Attempting to import runpod module...")
            import runpod
            logger.info("✅ Successfully imported runpod module")
            
            logger.info("Starting RunPod serverless with handler...")
            runpod.serverless.start({"handler": handler_func})
            logger.info("RunPod serverless started successfully")
        except Exception as e:
            logger.error(f"❌ Error starting RunPod serverless: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.error("❌ Cannot start RunPod serverless: No handler function found")

def main():
    """Main function to run diagnostics and start the handler"""
    try:
        logger.info("=" * 50)
        logger.info("RUNPOD HANDLER DIAGNOSTICS STARTING")
        logger.info("=" * 50)
        
        # Run diagnostics
        log_system_info()
        check_imports()
        check_b2_config()
        
        # Start the RunPod serverless handler
        logger.info("Starting RunPod serverless handler...")
        start_runpod_serverless()
        
    except Exception as e:
        logger.error(f"❌ Unhandled exception in main: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Keep the container alive for debugging
        logger.info("Entering sleep loop to keep container alive for debugging...")
        while True:
            time.sleep(3600)  # Sleep for an hour

if __name__ == "__main__":
    main() 