from __future__ import annotations

import json
import socket
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis

from app.config import settings
from app.timeutils import minute_bucket


class AppState:
    db: asyncpg.Pool
    redis: Redis


def get_state(request: Request) -> AppState:
    return request.app.state.services


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


app = FastAPI(title="Ad Click Aggregator Prototype", lifespan=lifespan)


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.get("/click/{ad_id}")
async def click_ad(
    ad_id: str,
    click_id: str,
    user_id: str,
    state: Annotated[AppState, Depends(get_state)],
):
    ad = await state.db.fetchrow("SELECT * FROM ads WHERE id = $1", ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="ad not found")
    event = {
        "click_id": click_id,
        "ad_id": ad_id,
        "user_id": user_id,
        "clicked_at": datetime.now(UTC).isoformat(),
    }
    await state.redis.rpush("click-events", json.dumps(event))
    response = RedirectResponse(ad["target_url"], status_code=302)
    response.headers["X-Tracked"] = "queued"
    return response


@app.post("/processor/tick")
async def process_clicks(state: Annotated[AppState, Depends(get_state)], limit: int = 100):
    processed = 0
    duplicates = 0
    for _ in range(limit):
        raw = await state.redis.lpop("click-events")
        if raw is None:
            break
        event = json.loads(raw)
        clicked_at = datetime.fromisoformat(event["clicked_at"])
        bucket = minute_bucket(clicked_at)
        async with state.db.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                    INSERT INTO click_events (click_id, ad_id, user_id, clicked_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (click_id) DO NOTHING
                    """,
                    event["click_id"],
                    event["ad_id"],
                    event["user_id"],
                    clicked_at,
                )
                if result == "INSERT 0 0":
                    duplicates += 1
                    continue
                await conn.execute(
                    """
                    INSERT INTO click_aggregates (ad_id, minute_bucket, click_count, unique_users)
                    VALUES ($1, $2, 1, 1)
                    ON CONFLICT (ad_id, minute_bucket)
                    DO UPDATE SET
                        click_count = click_aggregates.click_count + 1,
                        unique_users = (
                            SELECT COUNT(DISTINCT user_id)
                            FROM click_events
                            WHERE ad_id = $1
                              AND date_trunc('minute', clicked_at) = $2
                        )
                    """,
                    event["ad_id"],
                    bucket,
                )
                processed += 1
    return {"processed": processed, "duplicates": duplicates}


@app.get("/metrics")
async def get_metrics(
    ad_id: str,
    state: Annotated[AppState, Depends(get_state)],
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
):
    start = minute_bucket(start or datetime(1970, 1, 1, tzinfo=UTC))
    end = minute_bucket(end or datetime.now(UTC))
    rows = await state.db.fetch(
        """
        SELECT ad_id, minute_bucket, click_count, unique_users
        FROM click_aggregates
        WHERE ad_id = $1 AND minute_bucket BETWEEN $2 AND $3
        ORDER BY minute_bucket
        """,
        ad_id,
        start,
        end,
    )
    return {
        "adId": ad_id,
        "buckets": [
            {
                "minute": row["minute_bucket"].isoformat(),
                "clickCount": row["click_count"],
                "uniqueUsers": row["unique_users"],
            }
            for row in rows
        ],
    }
