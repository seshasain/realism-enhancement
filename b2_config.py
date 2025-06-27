import os
import time
import logging
from typing import Dict, Optional

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    Config = None
    ClientError = Exception

# Set up logging
logger = logging.getLogger(__name__)

def get_b2_config() -> Dict[str, str]:
    """
    Returns a dictionary with B2 configuration loaded from hardcoded values.
    """
    return {
        "B2_ACCESS_KEY_ID": "005f4d8d41e8f820000000006",
        "B2_SECRET_ACCESS_KEY": "K005DxzrqL8fABsGzLNsKVQEn+p8TfM",
        "B2_ENDPOINT": "s3.us-east-005.backblazeb2.com",
        "B2_IMAGE_BUCKET_NAME": "shortshive",
        "B2_IMAGE_BUCKET_ID": "7f34cd981dd4016e986f0812",
        "VITE_B2_IMAGE_BUCKET_NAME": "shortshive",
        "VITE_B2_IMAGE_BUCKET_ID": "7f34cd981dd4016e986f0812",
    }


def get_b2_s3_client():
    """
    Returns a boto3 S3 client configured for Backblaze B2, or raises ImportError if boto3 is not installed.
    """
    if boto3 is None or Config is None:
        raise ImportError("boto3 is required to use get_b2_s3_client(). Please install it with 'pip install boto3'.")
    config = get_b2_config()

    # Create a B2-compatible configuration that disables checksum features
    # that Backblaze B2 doesn't support
    client_config = Config(
        signature_version='s3v4',
        s3={
            'addressing_style': 'path',
            'payload_signing_enabled': False,
            'use_accelerate_endpoint': False,
            'use_dualstack_endpoint': False
        },
        # Disable checksum features that B2 doesn't support
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        parameter_validation=False,
        retries={'max_attempts': 3}
    )

    return boto3.client(
        's3',
        endpoint_url=f'https://{config["B2_ENDPOINT"]}',
        aws_access_key_id=config["B2_ACCESS_KEY_ID"],
        aws_secret_access_key=config["B2_SECRET_ACCESS_KEY"],
        config=client_config,
        region_name='us-east-005',  # Match the endpoint region
    )


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
    
    # Use the proper S3 client with checksum features disabled
    s3_client = get_b2_s3_client()
    
    try:
        logger.info(f"Uploading {file_path} to {bucket_name}/{object_name}")
        s3_client.upload_file(file_path, bucket_name, object_name)
        logger.info(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
        
        # Construct the object URL
        endpoint = config["B2_ENDPOINT"]
        url = f"https://{endpoint}/{bucket_name}/{object_name}"
        return url
    except Exception as e:
        error_msg = f"Failed to upload {file_path} to {bucket_name}/{object_name}: {e}"
        logger.error(error_msg)
        raise Exception(error_msg)


def download_file_from_b2(object_name: str, destination_path: str, max_retries: int = 3, retry_delay: int = 2) -> None:
    """
    Downloads a file from the configured B2 bucket to a local path with retry mechanism.

    Args:
        object_name (str): S3 object name (key) in the bucket.
        destination_path (str): Local path to save the downloaded file.
        max_retries (int): Maximum number of retry attempts.
        retry_delay (int): Delay between retries in seconds.
    """
    config = get_b2_config()
    bucket_name = config["B2_IMAGE_BUCKET_NAME"]
    
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count} for downloading {object_name}")
            
            logger.info(f"Downloading {object_name} from B2 bucket {bucket_name} to {destination_path}")
            
            # Create a fresh client for each attempt
            s3_client = get_b2_s3_client()
            
            # Check if the object exists before downloading
            try:
                s3_client.head_object(Bucket=bucket_name, Key=object_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    error_msg = f"Object {object_name} does not exist in bucket {bucket_name}"
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
                else:
                    raise
            
            # Use download_file which handles streaming
            s3_client.download_file(
                Bucket=bucket_name,
                Key=object_name,
                Filename=destination_path
            )
            
            # Verify the file was downloaded successfully
            if os.path.exists(destination_path) and os.path.getsize(destination_path) > 0:
                logger.info(f"Successfully downloaded {object_name} to {destination_path} ({os.path.getsize(destination_path)} bytes)")
                return
            else:
                raise Exception(f"Downloaded file is empty or does not exist: {destination_path}")
                
        except Exception as e:
            last_exception = e
            retry_count += 1
            
            if isinstance(e, FileNotFoundError):
                logger.error(f"File not found error: {e}")
                # Don't retry if the file doesn't exist
                break
                
            logger.warning(f"Download attempt {retry_count} failed: {str(e)}")
            
            if retry_count < max_retries:
                sleep_time = retry_delay * retry_count  # Exponential backoff
                logger.info(f"Waiting {sleep_time} seconds before retry...")
                time.sleep(sleep_time)
            else:
                logger.error(f"All {max_retries} download attempts failed for {object_name}")
    
    # If we get here, all retries failed
    error_msg = f"Failed to download {object_name} after {max_retries} attempts. Last error: {str(last_exception)}"
    logger.error(error_msg)
    raise Exception(error_msg)