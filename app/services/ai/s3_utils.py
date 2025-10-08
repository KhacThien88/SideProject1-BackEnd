import boto3
from botocore.exceptions import ClientError


def download_from_s3(bucket_name, s3_key, local_path):
    """
    Download a file from S3 to a local path.

    :param bucket_name: Name of the S3 bucket.
    :param s3_key: Key of the file in the S3 bucket.
    :param local_path: Local path to save the downloaded file.
    """
    s3 = boto3.client('s3')
    try:
        s3.download_file(bucket_name, s3_key, local_path)
        print(f"Downloaded {s3_key} from S3 bucket {bucket_name} to {local_path}")
    except ClientError as e:
        print(f"Error downloading file: {e}")
        raise


def upload_to_s3(local_path, bucket_name, s3_key):
    """
    Upload a local file to S3.

    :param local_path: Path to the local file.
    :param bucket_name: Name of the S3 bucket.
    :param s3_key: Key to assign to the file in the S3 bucket.
    """
    s3 = boto3.client('s3')
    try:
        s3.upload_file(local_path, bucket_name, s3_key)
        print(f"Uploaded {local_path} to S3 bucket {bucket_name} as {s3_key}")
    except ClientError as e:
        print(f"Error uploading file: {e}")
        raise


def file_exists_in_s3(bucket_name, s3_key):
    """
    Check if a file exists in an S3 bucket.

    :param bucket_name: Name of the S3 bucket.
    :param s3_key: Key of the file in the S3 bucket.
    :return: True if the file exists, False otherwise.
    """
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print(f"Error checking file existence: {e}")
            raise