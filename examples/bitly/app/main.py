from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlparse

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis

from app.config import Settings, settings
from app.shortener import generated_code, generated_counter_value, validate_custom_alias


class ShortenRequest(BaseModel):
    long_url: str = Field(min_length=1, max_length=4096)
    custom_alias: str | None = None
    expiration_date: datetime | None = None

    @field_validator("long_url")
    @classmethod
    def long_url_must_be_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("long_url must be an absolute http(s) URL")
        return value

    @field_validator("custom_alias")
    @classmethod
    def custom_alias_must_be_valid(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                validate_custom_alias(value)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        return value

    @field_validator("expiration_date")
    @classmethod
    def expiration_date_must_be_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if value <= datetime.now(UTC):
            raise ValueError("expiration_date must be in the future")
        return value


class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    expires_at: datetime | None


class AppState:
    db: asyncpg.Pool
    redis: Redis
    cleanup_task: asyncio.Task[None] | None = None


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS short_urls (
    short_code TEXT PRIMARY KEY,
    long_url TEXT NOT NULL,
    custom_alias BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_short_urls_expires_at
    ON short_urls (expires_at)
    WHERE expires_at IS NOT NULL;
"""


def get_settings() -> Settings:
    return settings


def cache_ttl(expires_at: datetime | None) -> int | None:
    if expires_at is None:
        return 24 * 60 * 60
    seconds = int((expires_at - datetime.now(UTC)).total_seconds())
    return max(seconds, 1)


def build_short_url(base_url: str, short_code: str) -> str:
    return f"{base_url.rstrip('/')}/{short_code}"


async def insert_short_url(
    db: asyncpg.Pool,
    redis: Redis,
    config: Settings,
    payload: ShortenRequest,
) -> str:
    if payload.custom_alias:
        short_code = payload.custom_alias
        try:
            await db.execute(
                """
                INSERT INTO short_urls (short_code, long_url, custom_alias, expires_at)
                VALUES ($1, $2, true, $3)
                """,
                short_code,
                payload.long_url,
                payload.expiration_date,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(status_code=409, detail="custom alias already exists") from exc
        return short_code

    for _ in range(5):
        counter_value = await redis.incr("shortener:counter")
        short_code = generated_code(counter_value, config.counter_xor_secret)
        try:
            await db.execute(
                """
                INSERT INTO short_urls (short_code, long_url, custom_alias, expires_at)
                VALUES ($1, $2, false, $3)
                """,
                short_code,
                payload.long_url,
                payload.expiration_date,
            )
            return short_code
        except asyncpg.UniqueViolationError:
            continue

    raise HTTPException(status_code=503, detail="could not allocate a unique short code")


async def lookup_long_url(
    db: asyncpg.Pool,
    redis: Redis,
    short_code: str,
) -> tuple[str, bool]:
    cache_key = f"shortener:url:{short_code}"
    cached = await redis.get(cache_key)
    if cached is not None:
        return cached.decode("utf-8"), True

    row = await db.fetchrow(
        """
        SELECT long_url, expires_at
        FROM short_urls
        WHERE short_code = $1
        """,
        short_code,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="short code not found")

    expires_at = row["expires_at"]
    if expires_at is not None and expires_at <= datetime.now(UTC):
        await redis.delete(cache_key)
        raise HTTPException(status_code=410, detail="short code has expired")

    ttl = cache_ttl(expires_at)
    await redis.set(cache_key, row["long_url"], ex=ttl)
    return row["long_url"], False


async def cleanup_expired_urls(state: AppState, interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        rows = await state.db.fetch(
            """
            DELETE FROM short_urls
            WHERE expires_at IS NOT NULL AND expires_at <= now()
            RETURNING short_code
            """
        )
        if rows:
            await state.redis.delete(*[f"shortener:url:{row['short_code']}" for row in rows])


async def recover_counter_from_database(db: asyncpg.Pool, redis: Redis, config: Settings) -> None:
    rows = await db.fetch(
        """
        SELECT short_code
        FROM short_urls
        WHERE custom_alias = false
        """
    )
    if not rows:
        return

    max_counter_value = max(
        generated_counter_value(row["short_code"], config.counter_xor_secret)
        for row in rows
    )
    current_counter = int(await redis.get("shortener:counter") or 0)
    if current_counter < max_counter_value:
        await redis.set("shortener:counter", max_counter_value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url)
    async with state.db.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
    await recover_counter_from_database(state.db, state.redis, settings)
    state.cleanup_task = asyncio.create_task(
        cleanup_expired_urls(state, settings.cleanup_interval_seconds)
    )
    app.state.services = state
    try:
        yield
    finally:
        if state.cleanup_task:
            state.cleanup_task.cancel()
            try:
                await state.cleanup_task
            except asyncio.CancelledError:
                pass
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="Bitly System Design Prototype", lifespan=lifespan)


def get_state(request: Request) -> AppState:
    return request.app.state.services


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.post("/shorten", response_model=ShortenResponse, status_code=201)
async def shorten(
    payload: ShortenRequest,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    short_code = await insert_short_url(state.db, state.redis, config, payload)
    return ShortenResponse(
        short_url=build_short_url(config.base_url, short_code),
        short_code=short_code,
        expires_at=payload.expiration_date,
    )


@app.get("/{short_code}")
async def redirect(short_code: str, state: Annotated[AppState, Depends(get_state)]):
    long_url, cache_hit = await lookup_long_url(state.db, state.redis, short_code)
    response = RedirectResponse(long_url, status_code=302)
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return response
