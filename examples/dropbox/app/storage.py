from __future__ import annotations

import boto3
from botocore.client import Config

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
    buckets = client.list_buckets().get("Buckets", [])
    if any(bucket["Name"] == settings.s3_bucket for bucket in buckets):
        return
    client.create_bucket(Bucket=settings.s3_bucket)


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


def create_multipart_upload(settings: Settings, object_key: str, mime_type: str) -> str:
    client = s3_client(settings.s3_internal_endpoint, settings)
    response = client.create_multipart_upload(
        Bucket=settings.s3_bucket,
        Key=object_key,
        ContentType=mime_type,
    )
    return response["UploadId"]


def presigned_part_url(
    settings: Settings,
    object_key: str,
    upload_id: str,
    part_number: int,
) -> str:
    client = s3_client(settings.s3_public_endpoint, settings)
    return client.generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=settings.presigned_url_ttl_seconds,
    )


def complete_multipart_upload(
    settings: Settings,
    object_key: str,
    upload_id: str,
    parts: list[dict],
) -> None:
    client = s3_client(settings.s3_internal_endpoint, settings)
    client.complete_multipart_upload(
        Bucket=settings.s3_bucket,
        Key=object_key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


def head_object(settings: Settings, object_key: str) -> dict:
    client = s3_client(settings.s3_internal_endpoint, settings)
    return client.head_object(Bucket=settings.s3_bucket, Key=object_key)
