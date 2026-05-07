from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.cursor import decode_cursor, encode_cursor
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class IngestArticleRequest(BaseModel):
    publisher_id: str
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    category: str = Field(min_length=1)
    publisher_url: str = Field(min_length=1)
    published_at: datetime | None = None


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def article_payload(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "publisherId": row["publisher_id"],
        "publisherName": row["publisher_name"],
        "title": row["title"],
        "summary": row["summary"],
        "category": row["category"],
        "publishedAt": row["published_at"].isoformat(),
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


app = FastAPI(title="News Aggregator Prototype", lifespan=lifespan)


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


@app.post("/ingest/articles", status_code=201)
async def ingest_article(payload: IngestArticleRequest, state: Annotated[AppState, Depends(get_state)]):
    article_id = uuid.uuid4()
    published_at = payload.published_at or datetime.now(UTC)
    try:
        await state.db.execute(
            """
            INSERT INTO articles (id, publisher_id, title, summary, category, publisher_url, published_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            article_id,
            payload.publisher_id,
            payload.title,
            payload.summary,
            payload.category,
            payload.publisher_url,
            published_at,
        )
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(status_code=404, detail="publisher not found") from exc
    await state.redis.flushdb()
    return {"articleId": str(article_id), "status": "ingested"}


@app.get("/feed")
async def get_feed(
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=2, ge=1, le=20),
    cursor: str | None = None,
    category: str | None = None,
):
    cache_key = f"feed:{category or 'all'}:{limit}:{cursor or 'first'}"
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    cursor_time = None
    cursor_id = None
    if cursor:
        cursor_time, cursor_id = decode_cursor(cursor)

    rows = await state.db.fetch(
        """
        SELECT a.*, p.name AS publisher_name
        FROM articles a
        JOIN publishers p ON p.id = a.publisher_id
        WHERE ($1::text IS NULL OR a.category = $1)
          AND (
            $2::timestamptz IS NULL
            OR (a.published_at, a.id) < ($2::timestamptz, $3::uuid)
          )
        ORDER BY a.published_at DESC, a.id DESC
        LIMIT $4
        """,
        category,
        cursor_time,
        cursor_id,
        limit,
    )
    articles = [article_payload(row) for row in rows]
    next_cursor = encode_cursor(rows[-1]["published_at"], str(rows[-1]["id"])) if rows else None
    payload = {"articles": articles, "nextCursor": next_cursor}
    await state.redis.set(cache_key, json.dumps(payload), ex=config.feed_cache_ttl_seconds)
    payload["cache"] = "MISS"
    return payload


@app.get("/articles/{article_id}/redirect")
async def redirect_article(article_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    row = await state.db.fetchrow("SELECT publisher_url FROM articles WHERE id = $1", article_id)
    if row is None:
        raise HTTPException(status_code=404, detail="article not found")
    return RedirectResponse(row["publisher_url"], status_code=302)
