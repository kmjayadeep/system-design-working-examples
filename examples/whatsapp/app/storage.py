from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

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
    if any(bucket["Name"] == settings.s3_bucket for bucket in client.list_buckets().get("Buckets", [])):
        return
    try:
        client.create_bucket(Bucket=settings.s3_bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise


def presigned_put_url(settings: Settings, object_key: str) -> str:
    client = s3_client(settings.s3_public_endpoint, settings)
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=settings.presigned_url_ttl_seconds,
    )


def presigned_get_url(settings: Settings, object_key: str) -> str:
    client = s3_client(settings.s3_public_endpoint, settings)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=settings.presigned_url_ttl_seconds,
    )
