from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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


class CreatePostRequest(BaseModel):
    content: dict = Field(default_factory=dict)


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def post_payload(row: asyncpg.Record) -> dict:
    return {
        "postId": str(row["id"]),
        "authorId": row["author_id"],
        "content": json.loads(row["content"]),
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


app = FastAPI(title="FB News Feed Prototype", lifespan=lifespan)


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


@app.put("/users/{followed_user_id}/follow")
async def follow_user(
    followed_user_id: str,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    if followed_user_id == actor_user_id:
        raise HTTPException(status_code=409, detail="cannot follow yourself")
    await state.db.execute(
        """
        INSERT INTO follows (follower_id, followed_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        actor_user_id,
        followed_user_id,
    )
    return {"status": "following", "followerId": actor_user_id, "followedId": followed_user_id}


@app.post("/posts", status_code=201)
async def create_post(
    payload: CreatePostRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    post_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    await state.db.execute(
        """
        INSERT INTO posts (id, author_id, content, created_at)
        VALUES ($1, $2, $3::jsonb, $4)
        """,
        post_id,
        actor_user_id,
        json.dumps(payload.content),
        created_at,
    )
    await state.redis.rpush("fanout-jobs", json.dumps({"postId": str(post_id), "authorId": actor_user_id}))
    return {"postId": str(post_id), "status": "queued_for_fanout", "createdAt": created_at.isoformat()}


@app.post("/workers/fanout/tick")
async def fanout_tick(
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    limit: int = 100,
):
    jobs = 0
    feed_writes = 0
    for _ in range(limit):
        raw = await state.redis.lpop("fanout-jobs")
        if raw is None:
            break
        jobs += 1
        job = json.loads(raw)
        post = await state.db.fetchrow("SELECT * FROM posts WHERE id = $1", uuid.UUID(job["postId"]))
        if post is None:
            continue
        followers = await state.db.fetch("SELECT follower_id FROM follows WHERE followed_id = $1", job["authorId"])
        rows = [(row["follower_id"], post["id"], post["created_at"]) for row in followers]
        rows.append((job["authorId"], post["id"], post["created_at"]))
        await state.db.executemany(
            """
            INSERT INTO feed_items (user_id, post_id, created_at)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            rows,
        )
        for follower_id, _, _ in rows:
            await state.db.execute(
                """
                DELETE FROM feed_items
                WHERE user_id = $1
                  AND post_id NOT IN (
                    SELECT post_id FROM feed_items
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                  )
                """,
                follower_id,
                config.feed_limit,
            )
        feed_writes += len(rows)
    return {"jobsProcessed": jobs, "feedWrites": feed_writes}


@app.get("/feed")
async def get_feed(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    page_size: int = Query(default=5, ge=1, le=50),
    cursor: datetime | None = None,
):
    rows = await state.db.fetch(
        """
        SELECT p.*
        FROM feed_items f
        JOIN posts p ON p.id = f.post_id
        WHERE f.user_id = $1
          AND ($2::timestamptz IS NULL OR f.created_at < $2)
        ORDER BY f.created_at DESC
        LIMIT $3
        """,
        actor_user_id,
        cursor,
        page_size,
    )
    posts = [post_payload(row) for row in rows]
    next_cursor = rows[-1]["created_at"].isoformat() if len(rows) == page_size else None
    return {"items": posts, "nextCursor": next_cursor}
