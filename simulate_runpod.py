#!/usr/bin/env python
import os
import sys
import shutil
import logging
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RunPodSimulator")

def create_runpod_environment():
    """
    Create a simulated RunPod environment structure
    """
    logger.info("Creating simulated RunPod environment...")
    
    # Create /runpod-volume directory structure
    runpod_volume = "/tmp/runpod-volume"
    if os.path.exists(runpod_volume):
        logger.info(f"Removing existing {runpod_volume}")
        shutil.rmtree(runpod_volume)
    
    # Create directories
    dirs_to_create = [
        runpod_volume,
        f"{runpod_volume}/ComfyUI",
        f"{runpod_volume}/ComfyUI/input",
        f"{runpod_volume}/ComfyUI/output",
        f"{runpod_volume}/logs",
    ]
    
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    
    # Create symlinks to simulate RunPod environment
    current_dir = os.getcwd()
    
    # Create symlinks for key directories
    symlinks = [
        ("input", f"{runpod_volume}/ComfyUI/input"),
        ("output", f"{runpod_volume}/ComfyUI/output"),
        ("logs", f"{runpod_volume}/logs"),
    ]
    
    for link_name, target in symlinks:
        link_path = os.path.join(current_dir, link_name)
        if os.path.exists(link_path):
            if os.path.islink(link_path):
                os.unlink(link_path)
            else:
                logger.warning(f"{link_path} exists and is not a symlink. Skipping.")
                continue
        
        os.symlink(target, link_path)
        logger.info(f"Created symlink: {link_path} -> {target}")
    
    # Set environment variables
    os.environ["RUNPOD_VOLUME"] = runpod_volume
    os.environ["RUNPOD_INPUT_PATH"] = f"{runpod_volume}/ComfyUI/input"
    os.environ["RUNPOD_OUTPUT_PATH"] = f"{runpod_volume}/ComfyUI/output"
    os.environ["RUNPOD_LOG_PATH"] = f"{runpod_volume}/logs"
    
    logger.info("RunPod environment simulation complete")
    return runpod_volume

def cleanup_runpod_environment(runpod_volume):
    """
    Clean up the simulated RunPod environment
    """
    logger.info("Cleaning up simulated RunPod environment...")
    
    # Remove symlinks
    symlinks = ["input", "output", "logs"]
    for link in symlinks:
        link_path = os.path.join(os.getcwd(), link)
        if os.path.islink(link_path):
            os.unlink(link_path)
            logger.info(f"Removed symlink: {link_path}")
    
    # Remove environment variables
    for var in ["RUNPOD_VOLUME", "RUNPOD_INPUT_PATH", "RUNPOD_OUTPUT_PATH", "RUNPOD_LOG_PATH"]:
        if var in os.environ:
            del os.environ[var]
    
    # Keep the runpod_volume directory for inspection
    logger.info(f"Simulation files remain at {runpod_volume} for inspection")
    logger.info("Cleanup complete")

if __name__ == "__main__":
    logger.info("=== Starting RunPod Environment Simulation ===")
    
    try:
        runpod_volume = create_runpod_environment()
        
        # Run test script if provided
        if len(sys.argv) > 1:
            test_script = sys.argv[1]
            if os.path.exists(test_script):
                logger.info(f"Running test script: {test_script}")
                os.system(f"python {test_script}")
            else:
                logger.error(f"Test script not found: {test_script}")
        
        # Keep environment unless --cleanup flag is provided
        if "--cleanup" in sys.argv:
            cleanup_runpod_environment(runpod_volume)
        else:
            logger.info(f"RunPod simulation environment remains at {runpod_volume}")
            logger.info(f"Run with --cleanup to remove the environment")
    
    except Exception as e:
        logger.error(f"Error in RunPod simulation: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("=== RunPod Environment Simulation Complete ===") 