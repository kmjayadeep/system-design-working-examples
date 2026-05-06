from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

from app.config import Settings


def s3_client(endpoint_url: str, settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def ensure_bucket(settings: Settings) -> None:
    client = s3_client(settings.s3_internal_endpoint, settings)
    try:
        client.create_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise


def put_bytes(settings: Settings, key: str, body: bytes, content_type: str) -> None:
    client = s3_client(settings.s3_internal_endpoint, settings)
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=body, ContentType=content_type)
