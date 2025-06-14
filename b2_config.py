import os
from typing import Dict, Optional

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None
    Config = None

# Define RunPod environment constant
RUNPOD_SERVERLESS = os.environ.get("RUNPOD_SERVERLESS", "false").lower() == "true"
RUNPOD_VOLUME_PATH = "/runpod-volume" if RUNPOD_SERVERLESS else os.getcwd()


def get_b2_config() -> Dict[str, str]:
    """
    Returns a dictionary with B2 configuration loaded from hardcoded values.
    """
    # Allow environment variable overrides, useful for serverless environments
    return {
        "B2_ACCESS_KEY_ID": os.environ.get("B2_ACCESS_KEY_ID", "005f4d8d41e8f820000000006"),
        "B2_SECRET_ACCESS_KEY": os.environ.get("B2_SECRET_ACCESS_KEY", "K005DxzrqL8fABsGzLNsKVQEn+p8TfM"),
        "B2_ENDPOINT": os.environ.get("B2_ENDPOINT", "s3.us-east-005.backblazeb2.com"),
        "B2_IMAGE_BUCKET_NAME": os.environ.get("B2_IMAGE_BUCKET_NAME", "shortshive"),
        "B2_IMAGE_BUCKET_ID": os.environ.get("B2_IMAGE_BUCKET_ID", "7f34cd981dd4016e986f0812"),
        "VITE_B2_IMAGE_BUCKET_NAME": os.environ.get("VITE_B2_IMAGE_BUCKET_NAME", "shortshive"),
        "VITE_B2_IMAGE_BUCKET_ID": os.environ.get("VITE_B2_IMAGE_BUCKET_ID", "7f34cd981dd4016e986f0812"),
    }


def get_b2_s3_client():
    """
    Returns a boto3 S3 client configured for Backblaze B2, or raises ImportError if boto3 is not installed.
    """
    if boto3 is None or Config is None:
        raise ImportError("boto3 is required to use get_b2_s3_client(). Please install it with 'pip install boto3'.")
    config = get_b2_config()
    return boto3.client(
        's3',
        endpoint_url=f'https://{config["B2_ENDPOINT"]}',
        aws_access_key_id=config["B2_ACCESS_KEY_ID"],
        aws_secret_access_key=config["B2_SECRET_ACCESS_KEY"],
        config=Config(signature_version='s3v4'),
        region_name='us-east-1',  # B2 S3 endpoint is usually us-east-005
    )


def download_file_from_b2(object_name: str, destination_path: str) -> None:
    """
    Downloads a file from the configured B2 bucket to a local path.
    
    If the file already exists in the local cache directory in serverless mode,
    it will use that file instead of downloading it again.

    Args:
        object_name (str): S3 object name (key) in the bucket.
        destination_path (str): Local path to save the downloaded file.
    """
    # Check if the file already exists in RunPod and if we're in serverless mode
    if RUNPOD_SERVERLESS:
        cache_dir = os.path.join(RUNPOD_VOLUME_PATH, "b2_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, object_name)
        
        if os.path.exists(cache_path):
            print(f"Using cached file: {cache_path}")
            # If destination is different from cache, copy the file
            if cache_path != destination_path:
                import shutil
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                shutil.copy2(cache_path, destination_path)
            return
    
    # If not cached or not in serverless, download from B2
    config = get_b2_config()
    bucket_name = config["B2_IMAGE_BUCKET_NAME"]
    s3_client = get_b2_s3_client()
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    # Download the file
    print(f"Downloading {object_name} from B2 to {destination_path}")
    s3_client.download_file(bucket_name, object_name, destination_path) 
    
    # Cache the file in serverless mode
    if RUNPOD_SERVERLESS and destination_path != cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        import shutil
        shutil.copy2(destination_path, cache_path)


def upload_file_to_b2(file_path: str, object_name: Optional[str] = None) -> str:
    """
    Uploads a file to the configured B2 bucket.

    Args:
        file_path (str): Local path to the file to upload.
        object_name (Optional[str]): S3 object name. If not specified, file name is used.

    Returns:
        str: The URL of the uploaded object.
    """
    config = get_b2_config()
    bucket_name = config["B2_IMAGE_BUCKET_NAME"]
    if object_name is None:
        object_name = os.path.basename(file_path)
    s3_client = get_b2_s3_client()
    s3_client.upload_file(file_path, bucket_name, object_name)
    
    # Construct the object URL
    endpoint = config["B2_ENDPOINT"]
    url = f"https://{endpoint}/{bucket_name}/{object_name}"
    return url 