from __future__ import annotations

import re
import json
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


TOKEN_RE = re.compile(r"[a-z0-9]+")


class AppState:
    db: asyncpg.Pool
    redis: Redis


class PostRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class LikeRequest(BaseModel):
    post_id: uuid.UUID = Field(alias="postId")


def tokenize(text: str) -> list[str]:
    return sorted(set(TOKEN_RE.findall(text.lower())))


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
        "userId": row["user_id"],
        "content": row["content"],
        "likeCount": row["like_count"],
        "createdAt": row["created_at"].isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="FB Post Search Prototype", lifespan=lifespan)


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


@app.post("/posts", status_code=201)
async def create_post(
    payload: PostRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    post_id = uuid.uuid4()
    tokens = tokenize(payload.content)
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO posts (id, user_id, content)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                post_id,
                actor_user_id,
                payload.content,
            )
            await conn.executemany(
                """
                INSERT INTO post_terms (term, post_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                [(term, post_id) for term in tokens],
            )
    async for key in state.redis.scan_iter("search:*"):
        await state.redis.delete(key)
    await state.redis.xadd(
        "post-index-events",
        {"post_id": str(post_id), "terms": ",".join(tokens)},
        maxlen=config.index_event_max_len,
        approximate=True,
    )
    return {**post_payload(row), "indexedTerms": tokens}


@app.post("/likes", status_code=201)
async def like_post(
    payload: LikeRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval("SELECT 1 FROM posts WHERE id = $1", payload.post_id)
            if not exists:
                raise HTTPException(status_code=404, detail="post not found")
            inserted = await conn.fetchval(
                """
                INSERT INTO likes (post_id, user_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                RETURNING 1
                """,
                payload.post_id,
                actor_user_id,
            )
            if inserted:
                await conn.execute("UPDATE posts SET like_count = like_count + 1 WHERE id = $1", payload.post_id)
            row = await conn.fetchrow("SELECT * FROM posts WHERE id = $1", payload.post_id)
    async for key in state.redis.scan_iter("search:*"):
        await state.redis.delete(key)
    return {"liked": bool(inserted), "post": post_payload(row)}


@app.get("/search")
async def search_posts(
    state: Annotated[AppState, Depends(get_state)],
    q: str = Query(min_length=1),
    sort: str = Query(default="recency", pattern="^(recency|likes)$"),
    limit: int = Query(default=10, ge=1, le=50),
):
    terms = tokenize(q)
    if not terms:
        return {"query": q, "terms": [], "sort": sort, "cached": False, "results": []}

    cache_key = f"search:{' '.join(terms)}:{sort}:{limit}"
    cached = await state.redis.get(cache_key)
    if cached:
        return {"query": q, "terms": terms, "sort": sort, "cached": True, "results": json.loads(cached)}

    order_by = "p.like_count DESC, p.created_at DESC" if sort == "likes" else "p.created_at DESC"
    rows = await state.db.fetch(
        f"""
        SELECT p.*
        FROM posts p
        JOIN post_terms pt ON pt.post_id = p.id
        WHERE pt.term = ANY($1::text[])
        GROUP BY p.id
        HAVING COUNT(DISTINCT pt.term) = $2
        ORDER BY {order_by}
        LIMIT $3
        """,
        terms,
        len(terms),
        limit,
    )
    results = [post_payload(row) for row in rows]
    await state.redis.setex(cache_key, settings.search_cache_ttl_seconds, json.dumps(results))
    return {"query": q, "terms": terms, "sort": sort, "cached": False, "results": results}
