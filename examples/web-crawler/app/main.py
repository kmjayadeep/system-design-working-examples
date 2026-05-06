from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlparse

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis

from app.config import Settings, settings
from app.fetcher import fetch_fixture_page, normalize_url
from app.storage import ensure_bucket, put_bytes


class AppState:
    db: asyncpg.Pool
    redis: Redis


class CreateCrawlJobRequest(BaseModel):
    seeds: list[str] = Field(min_length=1)
    max_pages: int = Field(default=10, ge=1, le=100)

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, value):
        return [normalize_url(seed) for seed in value]


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


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


app = FastAPI(title="Web Crawler Prototype", lifespan=lifespan)


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.post("/crawl-jobs", status_code=201)
async def create_crawl_job(payload: CreateCrawlJobRequest, state: Annotated[AppState, Depends(get_state)]):
    job_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO crawl_jobs (id, status, max_pages) VALUES ($1, 'running', $2)",
                job_id,
                payload.max_pages,
            )
            for seed in payload.seeds:
                await conn.execute(
                    """
                    INSERT INTO pages (id, job_id, url, host, status)
                    VALUES ($1, $2, $3, $4, 'queued')
                    ON CONFLICT (job_id, url) DO NOTHING
                    """,
                    uuid.uuid4(),
                    job_id,
                    seed,
                    urlparse(seed).netloc,
                )
                await state.redis.rpush(f"frontier:{job_id}", seed)
    return {"jobId": str(job_id), "status": "running", "queued": len(payload.seeds)}


@app.post("/crawl-jobs/{job_id}/tick")
async def crawl_tick(
    job_id: uuid.UUID,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    limit: int = 1,
):
    job = await state.db.fetchrow("SELECT * FROM crawl_jobs WHERE id = $1", job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="crawl job not found")

    processed = []
    for _ in range(limit):
        crawled_count = await state.db.fetchval(
            "SELECT COUNT(*) FROM pages WHERE job_id = $1 AND status = 'crawled'",
            job_id,
        )
        if crawled_count >= job["max_pages"]:
            break

        url = await state.redis.lpop(f"frontier:{job_id}")
        if url is None:
            break
        url = url.decode()
        host = urlparse(url).netloc
        polite_key = f"polite:{job_id}:{host}"
        if await state.redis.exists(polite_key):
            await state.redis.rpush(f"frontier:{job_id}", url)
            break
        await state.redis.set(polite_key, "1", ex=config.politeness_delay_seconds)

        page = await state.db.fetchrow(
            """
            UPDATE pages
            SET status = 'fetching', updated_at = now()
            WHERE job_id = $1 AND url = $2 AND status = 'queued'
            RETURNING *
            """,
            job_id,
            url,
        )
        if page is None:
            continue

        http_status, raw, text, links = fetch_fixture_page(url)
        raw_key = f"jobs/{job_id}/raw/{page['id']}.html"
        text_key = f"jobs/{job_id}/text/{page['id']}.txt"
        put_bytes(config, raw_key, raw, "text/html")
        put_bytes(config, text_key, text.encode(), "text/plain")
        await state.db.execute(
            """
            UPDATE pages
            SET status = 'crawled', http_status = $3, raw_object_key = $4,
                text_object_key = $5, discovered_links = $6, updated_at = now()
            WHERE id = $1 AND job_id = $2
            """,
            page["id"],
            job_id,
            http_status,
            raw_key,
            text_key,
            links,
        )
        processed.append(url)

        for link in links:
            result = await state.db.execute(
                """
                INSERT INTO pages (id, job_id, url, host, status)
                VALUES ($1, $2, $3, $4, 'queued')
                ON CONFLICT (job_id, url) DO NOTHING
                """,
                uuid.uuid4(),
                job_id,
                link,
                urlparse(link).netloc,
            )
            if result == "INSERT 0 1":
                await state.redis.rpush(f"frontier:{job_id}", link)

    queued = await state.redis.llen(f"frontier:{job_id}")
    if queued == 0:
        await state.db.execute("UPDATE crawl_jobs SET status = 'completed', updated_at = now() WHERE id = $1", job_id)
    return {"processed": processed, "queued": queued}


@app.get("/crawl-jobs/{job_id}")
async def get_crawl_job(job_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    job = await state.db.fetchrow("SELECT * FROM crawl_jobs WHERE id = $1", job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="crawl job not found")
    pages = await state.db.fetch(
        """
        SELECT url, status, http_status, raw_object_key, text_object_key, discovered_links
        FROM pages
        WHERE job_id = $1
        ORDER BY url
        """,
        job_id,
    )
    return {
        "jobId": str(job_id),
        "status": job["status"],
        "maxPages": job["max_pages"],
        "pages": [dict(page) for page in pages],
    }
