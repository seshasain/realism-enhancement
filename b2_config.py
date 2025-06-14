import os
from typing import Dict, Optional

try:
    import boto3
    from botocore.client import Config
except ImportError:
    boto3 = None
    Config = None


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
    return boto3.client(
        's3',
        endpoint_url=f'https://{config["B2_ENDPOINT"]}',
        aws_access_key_id=config["B2_ACCESS_KEY_ID"],
        aws_secret_access_key=config["B2_SECRET_ACCESS_KEY"],
        config=Config(signature_version='s3v4'),
        region_name='us-east-1',  # B2 S3 endpoint is usually us-east-005
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
    s3_client = get_b2_s3_client()
    s3_client.upload_file(file_path, bucket_name, object_name)
    # Construct the object URL
    endpoint = config["B2_ENDPOINT"]
    url = f"https://{endpoint}/{bucket_name}/{object_name}"
    return url


def download_file_from_b2(object_name: str, destination_path: str) -> None:
    """
    Downloads a file from the configured B2 bucket to a local path.

    Args:
        object_name (str): S3 object name (key) in the bucket.
        destination_path (str): Local path to save the downloaded file.
    """
    config = get_b2_config()
    bucket_name = config["B2_IMAGE_BUCKET_NAME"]
    s3_client = get_b2_s3_client()
    s3_client.download_file(bucket_name, object_name, destination_path) 