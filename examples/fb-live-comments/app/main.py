from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class CommentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def comment_payload(row: asyncpg.Record) -> dict:
    return {
        "commentId": str(row["id"]),
        "liveVideoId": row["live_video_id"],
        "userId": row["user_id"],
        "message": row["message"],
        "createdAt": row["created_at"].isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="FB Live Comments Prototype", lifespan=lifespan)


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


@app.post("/comments/{live_video_id}", status_code=201)
async def create_comment(
    live_video_id: str,
    payload: CommentRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    comment_id = uuid.uuid4()
    row = await state.db.fetchrow(
        """
        INSERT INTO comments (id, live_video_id, user_id, message)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        comment_id,
        live_video_id,
        actor_user_id,
        payload.message,
    )
    await state.redis.xadd(
        f"comments:{live_video_id}",
        {"comment_id": str(comment_id), "user_id": actor_user_id, "message": payload.message},
        maxlen=config.stream_max_len,
        approximate=True,
    )
    return comment_payload(row)


@app.get("/comments/{live_video_id}")
async def list_comments(
    live_video_id: str,
    state: Annotated[AppState, Depends(get_state)],
    cursor: uuid.UUID | None = None,
    page_size: int = Query(default=10, ge=1, le=50),
):
    if cursor:
        cursor_row = await state.db.fetchrow("SELECT created_at FROM comments WHERE id = $1", cursor)
        if cursor_row is None:
            raise HTTPException(status_code=404, detail="cursor comment not found")
        rows = await state.db.fetch(
            """
            SELECT *
            FROM comments
            WHERE live_video_id = $1 AND created_at < $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            live_video_id,
            cursor_row["created_at"],
            page_size,
        )
    else:
        rows = await state.db.fetch(
            """
            SELECT *
            FROM comments
            WHERE live_video_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            live_video_id,
            page_size,
        )
    next_cursor = str(rows[-1]["id"]) if len(rows) == page_size else None
    return {"comments": [comment_payload(row) for row in rows], "nextCursor": next_cursor}


@app.get("/comments/{live_video_id}/stream")
async def stream_comments(
    live_video_id: str,
    state: Annotated[AppState, Depends(get_state)],
    after: str = Query(default="0-0"),
    count: int = Query(default=10, ge=1, le=100),
):
    rows = await state.redis.xrange(f"comments:{live_video_id}", min=f"({after}", max="+", count=count)
    return {
        "events": [
            {
                "streamId": stream_id.decode() if isinstance(stream_id, bytes) else stream_id,
                "commentId": data[b"comment_id"].decode(),
                "userId": data[b"user_id"].decode(),
                "message": data[b"message"].decode(),
            }
            for stream_id, data in rows
        ]
    }
