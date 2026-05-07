from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import Settings, settings
from app.storage import ensure_bucket, head_object, presigned_get_url, presigned_put_url
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool


class MediaUploadRequest(BaseModel):
    media_type: Literal["photo", "video"] = Field(alias="mediaType")


class PublishPostRequest(BaseModel):
    post_id: uuid.UUID = Field(alias="postId")
    caption: str = Field(default="", max_length=2200)


class FollowRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)


def media_object_key(owner_id: str, post_id: str, media_type: str) -> str:
    return f"{owner_id}/{post_id}/{media_type}"


def get_settings() -> Settings:
    return settings


def get_state(request: Request) -> AppState:
    return request.app.state.services


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def post_payload(row: asyncpg.Record, config: Settings) -> dict:
    return {
        "postId": str(row["id"]),
        "userId": row["user_id"],
        "caption": row["caption"],
        "mediaType": row["media_type"],
        "status": row["status"],
        "mediaUrl": presigned_get_url(config, row["object_key"]) if row["status"] == "published" else None,
        "createdAt": row["created_at"].isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    ensure_bucket(settings)
    app.state.services = state
    try:
        yield
    finally:
        await state.db.close()


app = FastAPI(title="Instagram Prototype", lifespan=lifespan)


@app.get("/")
async def ui():
    return ui_response()


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.post("/media/uploads", status_code=201)
async def create_media_upload(
    payload: MediaUploadRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    post_id = uuid.uuid4()
    object_key = media_object_key(actor_user_id, str(post_id), payload.media_type)
    await state.db.execute(
        """
        INSERT INTO posts (id, user_id, caption, media_type, object_key, status)
        VALUES ($1, $2, '', $3, $4, 'pending')
        """,
        post_id,
        actor_user_id,
        payload.media_type,
        object_key,
    )
    return {
        "postId": str(post_id),
        "uploadUrl": presigned_put_url(config, object_key),
        "method": "PUT",
        "status": "pending",
        "expiresInSeconds": config.presigned_url_ttl_seconds,
    }


@app.post("/posts", status_code=201)
async def publish_post(
    payload: PublishPostRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    row = await state.db.fetchrow("SELECT * FROM posts WHERE id = $1 AND user_id = $2", payload.post_id, actor_user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="pending post not found")
    try:
        head_object(config, row["object_key"])
    except Exception as exc:
        raise HTTPException(status_code=409, detail="media has not been uploaded yet") from exc
    row = await state.db.fetchrow(
        """
        UPDATE posts
        SET caption = $1, status = 'published'
        WHERE id = $2
        RETURNING *
        """,
        payload.caption,
        payload.post_id,
    )
    return post_payload(row, config)


@app.post("/follows", status_code=201)
async def follow_user(
    payload: FollowRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    if payload.user_id == actor_user_id:
        raise HTTPException(status_code=400, detail="cannot follow yourself")
    await state.db.execute(
        """
        INSERT INTO follows (follower_id, followee_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        actor_user_id,
        payload.user_id,
    )
    return {"followerId": actor_user_id, "followeeId": payload.user_id}


@app.get("/feed")
async def feed(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=20, ge=1, le=50),
):
    rows = await state.db.fetch(
        """
        SELECT p.*
        FROM posts p
        JOIN follows f ON f.followee_id = p.user_id
        WHERE f.follower_id = $1 AND p.status = 'published'
        ORDER BY p.created_at DESC
        LIMIT $2
        """,
        actor_user_id,
        limit,
    )
    return {"posts": [post_payload(row, config) for row in rows]}


@app.get("/users/{target_user_id}/posts")
async def user_posts(
    target_user_id: str,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    rows = await state.db.fetch(
        "SELECT * FROM posts WHERE user_id = $1 AND status = 'published' ORDER BY created_at DESC",
        target_user_id,
    )
    return {"posts": [post_payload(row, config) for row in rows]}
