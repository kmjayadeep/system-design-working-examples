from __future__ import annotations

import json
import math
import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.processing import rendition_payload, split_segments
from app.storage import (
    complete_multipart_upload,
    create_multipart_upload,
    ensure_bucket,
    get_object_bytes,
    presigned_get_url,
    presigned_part_url,
    presigned_put_url,
    put_manifest,
    put_object_bytes,
)
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class VideoMetadataRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    size: int = Field(ge=0)


class PresignedUploadRequest(BaseModel):
    video_metadata: VideoMetadataRequest


class MultipartUploadRequest(BaseModel):
    video_metadata: VideoMetadataRequest
    chunk_size: int = Field(default=5 * 1024 * 1024, ge=5 * 1024 * 1024)


class PartCompleteRequest(BaseModel):
    etag: str = Field(min_length=1)


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def get_state(request: Request) -> AppState:
    return request.app.state.services


def metadata_from_row(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row["description"],
        "uploadedBy": row["uploader_id"],
        "status": row["status"],
        "createdAt": row["created_at"].isoformat(),
    }


async def process_video(db: asyncpg.Pool, config: Settings, video_id: uuid.UUID, original_key: str) -> str:
    original = get_object_bytes(config, original_key)
    manifest_key = f"processed/{video_id}/manifest.json"
    renditions = ["360p", "720p"]
    manifest = {"videoId": str(video_id), "renditions": {}}

    for rendition in renditions:
        manifest["renditions"][rendition] = []
        for index, segment in enumerate(split_segments(original), start=1):
            segment_key = f"processed/{video_id}/{rendition}/segment-{index}.bin"
            put_object_bytes(config, segment_key, rendition_payload(rendition, segment))
            await db.execute(
                """
                INSERT INTO video_segments (video_id, rendition, segment_number, object_key, duration_seconds)
                VALUES ($1, $2, $3, $4, 4)
                """,
                video_id,
                rendition,
                index,
                segment_key,
            )
            manifest["renditions"][rendition].append(
                {"segment": index, "durationSeconds": 4, "objectKey": segment_key}
            )

    put_manifest(config, manifest_key, manifest)
    await db.execute(
        """
        UPDATE videos
        SET status = 'ready', manifest_object_key = $2, updated_at = now()
        WHERE id = $1
        """,
        video_id,
        manifest_key,
    )
    return manifest_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url)
    ensure_bucket(settings)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="YouTube Video Streaming Prototype", lifespan=lifespan)


@app.get("/")
async def ui():
    return ui_response()


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.post("/videos/presigned-url", status_code=201)
async def create_presigned_upload(
    payload: PresignedUploadRequest,
    uploader_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    video_id = uuid.uuid4()
    original_key = f"originals/{uploader_id}/{video_id}.bin"
    await state.db.execute(
        """
        INSERT INTO videos (id, uploader_id, title, description, original_object_key, status)
        VALUES ($1, $2, $3, $4, $5, 'pending_upload')
        """,
        video_id,
        uploader_id,
        payload.video_metadata.title,
        payload.video_metadata.description,
        original_key,
    )
    return {
        "videoId": str(video_id),
        "uploadUrl": presigned_put_url(config, original_key),
        "method": "PUT",
        "status": "pending_upload",
    }


@app.post("/videos/multipart/presigned-url", status_code=201)
async def create_multipart_upload_session(
    payload: MultipartUploadRequest,
    uploader_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    video_id = uuid.uuid4()
    original_key = f"originals/{uploader_id}/{video_id}.bin"
    upload_id = create_multipart_upload(config, original_key)
    part_count = max(1, math.ceil(payload.video_metadata.size / payload.chunk_size))

    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO videos (id, uploader_id, title, description, original_object_key, status, upload_id)
                VALUES ($1, $2, $3, $4, $5, 'uploading', $6)
                """,
                video_id,
                uploader_id,
                payload.video_metadata.title,
                payload.video_metadata.description,
                original_key,
                upload_id,
            )
            for part_number in range(1, part_count + 1):
                remaining = payload.video_metadata.size - ((part_number - 1) * payload.chunk_size)
                await conn.execute(
                    """
                    INSERT INTO video_parts (video_id, part_number, size, status)
                    VALUES ($1, $2, $3, 'pending')
                    """,
                    video_id,
                    part_number,
                    min(payload.chunk_size, remaining),
                )

    return {
        "videoId": str(video_id),
        "uploadId": upload_id,
        "parts": [
            {
                "partNumber": part_number,
                "uploadUrl": presigned_part_url(config, original_key, upload_id, part_number),
                "status": "pending",
            }
            for part_number in range(1, part_count + 1)
        ],
    }


@app.patch("/videos/{video_id}/parts/{part_number}")
async def mark_part_uploaded(
    video_id: uuid.UUID,
    part_number: int,
    payload: PartCompleteRequest,
    state: Annotated[AppState, Depends(get_state)],
):
    result = await state.db.execute(
        """
        UPDATE video_parts
        SET status = 'uploaded', etag = $3, updated_at = now()
        WHERE video_id = $1 AND part_number = $2
        """,
        video_id,
        part_number,
        payload.etag.strip('"'),
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="part not found")
    return {"status": "uploaded"}


@app.get("/videos/{video_id}/parts")
async def list_parts(video_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch(
        """
        SELECT part_number, size, status, etag
        FROM video_parts
        WHERE video_id = $1
        ORDER BY part_number
        """,
        video_id,
    )
    return {"parts": [dict(row) for row in rows]}


@app.post("/videos/{video_id}/complete")
async def complete_upload(
    video_id: uuid.UUID,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await state.db.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    await state.db.execute("UPDATE videos SET status = 'processing' WHERE id = $1", video_id)
    manifest_key = await process_video(state.db, config, video_id, row["original_object_key"])
    await state.redis.delete(f"video:{video_id}")
    return {"status": "ready", "videoId": str(video_id), "manifestObjectKey": manifest_key}


@app.post("/videos/{video_id}/complete-multipart")
async def complete_multipart(
    video_id: uuid.UUID,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await state.db.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    parts = await state.db.fetch(
        "SELECT part_number, etag FROM video_parts WHERE video_id = $1 ORDER BY part_number",
        video_id,
    )
    if not parts or any(part["etag"] is None for part in parts):
        raise HTTPException(status_code=409, detail="not all parts are uploaded")
    complete_multipart_upload(
        config,
        row["original_object_key"],
        row["upload_id"],
        [{"PartNumber": part["part_number"], "ETag": part["etag"]} for part in parts],
    )
    return await complete_upload(video_id, state, config)


@app.get("/videos/{video_id}")
async def get_video(
    video_id: uuid.UUID,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    cache_key = f"video:{video_id}"
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    row = await state.db.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="video not found")
    if row["status"] != "ready":
        raise HTTPException(status_code=409, detail=f"video status is {row['status']}")

    segments = await state.db.fetch(
        """
        SELECT rendition, segment_number, object_key, duration_seconds
        FROM video_segments
        WHERE video_id = $1
        ORDER BY rendition, segment_number
        """,
        video_id,
    )
    payload = {
        "videoMetadata": metadata_from_row(row),
        "manifestUrl": presigned_get_url(config, row["manifest_object_key"]),
        "segments": [
            {
                "rendition": segment["rendition"],
                "segmentNumber": segment["segment_number"],
                "durationSeconds": segment["duration_seconds"],
                "url": presigned_get_url(config, segment["object_key"]),
            }
            for segment in segments
        ],
    }
    await state.redis.set(cache_key, json.dumps(payload), ex=config.video_metadata_cache_ttl_seconds)
    payload["cache"] = "MISS"
    return payload
