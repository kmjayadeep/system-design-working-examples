from __future__ import annotations

import math
import json
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import Settings, settings
from app.storage import (
    complete_multipart_upload,
    create_multipart_upload,
    ensure_bucket,
    head_object,
    presigned_get_url,
    presigned_part_url,
    presigned_put_url,
)


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    upload_id TEXT NULL,
    fingerprint TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_files_owner_id ON files (owner_id);
CREATE TABLE IF NOT EXISTS file_parts (
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    part_number INTEGER NOT NULL,
    size BIGINT NOT NULL,
    status TEXT NOT NULL,
    etag TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (file_id, part_number)
);
CREATE TABLE IF NOT EXISTS file_shares (
    user_id TEXT NOT NULL,
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    shared_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, file_id)
);
CREATE INDEX IF NOT EXISTS idx_file_shares_file_id ON file_shares (file_id);
CREATE TABLE IF NOT EXISTS change_events (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    file_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_change_events_user_id_id ON change_events (user_id, id);
"""


class AppState:
    db: asyncpg.Pool


class FileMetadataRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0)
    mime_type: str = Field(default="application/octet-stream", max_length=255)
    fingerprint: str | None = Field(default=None, max_length=128)


class PresignedUploadRequest(BaseModel):
    file_metadata: FileMetadataRequest


class PresignedUploadResponse(BaseModel):
    file_id: uuid.UUID
    upload_url: str
    method: str = "PUT"
    expires_in_seconds: int
    status: str


class MultipartUploadRequest(BaseModel):
    file_metadata: FileMetadataRequest
    chunk_size: int = Field(default=8 * 1024 * 1024, ge=5 * 1024 * 1024)


class MultipartPartUrl(BaseModel):
    part_number: int
    upload_url: str
    size: int
    status: str


class MultipartUploadResponse(BaseModel):
    file_id: uuid.UUID
    upload_id: str
    chunk_size: int
    parts: list[MultipartPartUrl]
    status: str


class PartCompleteRequest(BaseModel):
    etag: str = Field(min_length=1)


class ShareRequest(BaseModel):
    users: list[str] = Field(min_length=1)


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def metadata_from_row(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "uploadedAt": row["created_at"].isoformat(),
        "uploadedBy": row["owner_id"],
        "size": row["size"],
        "mimeType": row["mime_type"],
        "status": row["status"],
        "fingerprint": row["fingerprint"],
    }


async def record_change(
    db: asyncpg.Pool,
    target_user_id: str,
    file_id: uuid.UUID,
    event_type: str,
    metadata: dict,
) -> None:
    await db.execute(
        """
        INSERT INTO change_events (user_id, file_id, event_type, metadata)
        VALUES ($1, $2, $3, $4::jsonb)
        """,
        target_user_id,
        file_id,
        event_type,
        json.dumps(metadata),
    )


async def fetch_accessible_file(
    db: asyncpg.Pool,
    file_id: uuid.UUID,
    actor_user_id: str,
) -> asyncpg.Record:
    row = await db.fetchrow(
        """
        SELECT f.*
        FROM files f
        LEFT JOIN file_shares s ON s.file_id = f.id AND s.user_id = $2
        WHERE f.id = $1 AND (f.owner_id = $2 OR s.user_id IS NOT NULL)
        """,
        file_id,
        actor_user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    return row


async def fetch_owned_file(
    db: asyncpg.Pool,
    file_id: uuid.UUID,
    actor_user_id: str,
) -> asyncpg.Record:
    row = await db.fetchrow(
        "SELECT * FROM files WHERE id = $1 AND owner_id = $2",
        file_id,
        actor_user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    return row


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    async with state.db.acquire() as conn:
        await conn.execute(CREATE_SCHEMA_SQL)
    ensure_bucket(settings)
    app.state.services = state
    try:
        yield
    finally:
        await state.db.close()


app = FastAPI(title="Dropbox System Design Prototype", lifespan=lifespan)


def get_state(request: Request) -> AppState:
    return request.app.state.services


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.post("/files/presigned-url", response_model=PresignedUploadResponse, status_code=201)
async def create_presigned_upload(
    payload: PresignedUploadRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    file_id = uuid.uuid4()
    object_key = f"{actor_user_id}/{file_id}/{payload.file_metadata.name}"
    await state.db.execute(
        """
        INSERT INTO files (id, owner_id, name, size, mime_type, object_key, status, fingerprint)
        VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7)
        """,
        file_id,
        actor_user_id,
        payload.file_metadata.name,
        payload.file_metadata.size,
        payload.file_metadata.mime_type,
        object_key,
        payload.file_metadata.fingerprint,
    )
    return PresignedUploadResponse(
        file_id=file_id,
        upload_url=presigned_put_url(config, object_key),
        expires_in_seconds=config.presigned_url_ttl_seconds,
        status="pending",
    )


@app.post("/files/multipart/presigned-url", response_model=MultipartUploadResponse, status_code=201)
async def create_multipart_presigned_upload(
    payload: MultipartUploadRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    file_id = uuid.uuid4()
    object_key = f"{actor_user_id}/{file_id}/{payload.file_metadata.name}"
    upload_id = create_multipart_upload(config, object_key, payload.file_metadata.mime_type)
    part_count = max(1, math.ceil(payload.file_metadata.size / payload.chunk_size))

    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO files (id, owner_id, name, size, mime_type, object_key, status, upload_id, fingerprint)
                VALUES ($1, $2, $3, $4, $5, $6, 'uploading', $7, $8)
                """,
                file_id,
                actor_user_id,
                payload.file_metadata.name,
                payload.file_metadata.size,
                payload.file_metadata.mime_type,
                object_key,
                upload_id,
                payload.file_metadata.fingerprint,
            )
            for part_number in range(1, part_count + 1):
                remaining = payload.file_metadata.size - ((part_number - 1) * payload.chunk_size)
                part_size = min(payload.chunk_size, remaining)
                await conn.execute(
                    """
                    INSERT INTO file_parts (file_id, part_number, size, status)
                    VALUES ($1, $2, $3, 'pending')
                    """,
                    file_id,
                    part_number,
                    part_size,
                )

    parts = [
        MultipartPartUrl(
            part_number=part_number,
            upload_url=presigned_part_url(config, object_key, upload_id, part_number),
            size=min(
                payload.chunk_size,
                payload.file_metadata.size - ((part_number - 1) * payload.chunk_size),
            ),
            status="pending",
        )
        for part_number in range(1, part_count + 1)
    ]
    return MultipartUploadResponse(
        file_id=file_id,
        upload_id=upload_id,
        chunk_size=payload.chunk_size,
        parts=parts,
        status="uploading",
    )


@app.patch("/files/{file_id}/parts/{part_number}")
async def mark_part_uploaded(
    file_id: uuid.UUID,
    part_number: int,
    payload: PartCompleteRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    await fetch_owned_file(state.db, file_id, actor_user_id)
    result = await state.db.execute(
        """
        UPDATE file_parts
        SET status = 'uploaded', etag = $3, updated_at = now()
        WHERE file_id = $1 AND part_number = $2
        """,
        file_id,
        part_number,
        payload.etag.strip('"'),
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="part not found")
    return {"status": "uploaded"}


@app.get("/files/{file_id}/parts")
async def list_parts(
    file_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    await fetch_owned_file(state.db, file_id, actor_user_id)
    rows = await state.db.fetch(
        """
        SELECT part_number, size, status, etag
        FROM file_parts
        WHERE file_id = $1
        ORDER BY part_number
        """,
        file_id,
    )
    return {
        "parts": [
            {
                "part_number": row["part_number"],
                "size": row["size"],
                "status": row["status"],
                "etag": row["etag"],
            }
            for row in rows
        ]
    }


@app.post("/files/{file_id}/complete")
async def complete_upload(
    file_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await fetch_owned_file(state.db, file_id, actor_user_id)
    try:
        head_object(config, row["object_key"])
    except ClientError as exc:
        raise HTTPException(status_code=409, detail="object has not been uploaded yet") from exc

    updated = await state.db.fetchrow(
        """
        UPDATE files
        SET status = 'uploaded', updated_at = now()
        WHERE id = $1
        RETURNING *
        """,
        file_id,
    )
    metadata = metadata_from_row(updated)
    await record_change(state.db, actor_user_id, file_id, "created", metadata)
    return {"status": "uploaded", "fileMetadata": metadata}


@app.post("/files/{file_id}/complete-multipart")
async def complete_multipart(
    file_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await fetch_owned_file(state.db, file_id, actor_user_id)
    if not row["upload_id"]:
        raise HTTPException(status_code=409, detail="file is not a multipart upload")

    parts = await state.db.fetch(
        """
        SELECT part_number, etag
        FROM file_parts
        WHERE file_id = $1
        ORDER BY part_number
        """,
        file_id,
    )
    if not parts or any(part["etag"] is None for part in parts):
        raise HTTPException(status_code=409, detail="not all parts are uploaded")

    complete_multipart_upload(
        config,
        row["object_key"],
        row["upload_id"],
        [
            {"PartNumber": part["part_number"], "ETag": part["etag"]}
            for part in parts
        ],
    )
    updated = await state.db.fetchrow(
        """
        UPDATE files
        SET status = 'uploaded', updated_at = now()
        WHERE id = $1
        RETURNING *
        """,
        file_id,
    )
    metadata = metadata_from_row(updated)
    await record_change(state.db, actor_user_id, file_id, "created", metadata)
    return {"status": "uploaded", "fileMetadata": metadata}


@app.get("/files/changes")
async def get_changes(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    since: int = 0,
):
    rows = await state.db.fetch(
        """
        SELECT id, file_id, event_type, metadata, created_at
        FROM change_events
        WHERE user_id = $1 AND id > $2
        ORDER BY id
        """,
        actor_user_id,
        since,
    )
    return {
        "changes": [
            {
                "id": row["id"],
                "fileId": str(row["file_id"]),
                "type": row["event_type"],
                "fileMetadata": row["metadata"],
                "createdAt": row["created_at"].isoformat(),
            }
            for row in rows
        ],
        "nextSince": rows[-1]["id"] if rows else since,
    }


@app.post("/files/{file_id}/share")
async def share_file(
    file_id: uuid.UUID,
    payload: ShareRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    row = await fetch_owned_file(state.db, file_id, actor_user_id)
    metadata = metadata_from_row(row)
    for shared_user_id in sorted(set(payload.users)):
        if shared_user_id == actor_user_id:
            continue
        await state.db.execute(
            """
            INSERT INTO file_shares (user_id, file_id, shared_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, file_id) DO NOTHING
            """,
            shared_user_id,
            file_id,
            actor_user_id,
        )
        await record_change(state.db, shared_user_id, file_id, "shared", metadata)
    return {"status": "shared", "users": sorted(set(payload.users))}


@app.get("/files/{file_id}")
async def get_file(
    file_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await fetch_accessible_file(state.db, file_id, actor_user_id)
    if row["status"] != "uploaded":
        raise HTTPException(status_code=409, detail=f"file status is {row['status']}")
    return {
        "fileMetadata": metadata_from_row(row),
        "downloadUrl": presigned_get_url(config, row["object_key"]),
        "downloadUrlTtlSeconds": config.presigned_url_ttl_seconds,
    }
