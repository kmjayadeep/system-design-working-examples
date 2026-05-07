from __future__ import annotations

import socket
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.topk import VALID_WINDOWS, bucket_key, bucket_ttl_seconds, parse_timestamp
from app.ui import ui_response


class AppState:
    redis: Redis


class ViewRequest(BaseModel):
    video_id: str = Field(alias="videoId", min_length=1)
    count: int = Field(default=1, ge=1, le=10000)
    viewed_at: str | None = Field(default=None, alias="viewedAt")


class BatchViewRequest(BaseModel):
    views: list[ViewRequest] = Field(min_length=1, max_length=1000)


def get_state(request: Request) -> AppState:
    return request.app.state.services


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()


app = FastAPI(title="YouTube Top K Prototype", lifespan=lifespan)


@app.get("/")
async def ui():
    return ui_response()


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


async def record_view(redis: Redis, payload: ViewRequest) -> dict:
    viewed_at = parse_timestamp(payload.viewed_at)
    pipe = redis.pipeline()
    keys = []
    for window in ["all", "hour", "day", "month"]:
        key = bucket_key(window, viewed_at)
        keys.append(key)
        pipe.zincrby(key, payload.count, payload.video_id)
        ttl = bucket_ttl_seconds(window)
        if ttl:
            pipe.expire(key, ttl)
    await pipe.execute()
    await redis.xadd(
        "view-events",
        {"video_id": payload.video_id, "count": payload.count, "viewed_at": viewed_at.isoformat()},
        maxlen=1000,
        approximate=True,
    )
    return {"videoId": payload.video_id, "count": payload.count, "viewedAt": viewed_at.isoformat(), "buckets": keys}


@app.post("/views", status_code=202)
async def ingest_view(payload: ViewRequest, state: Annotated[AppState, Depends(get_state)]):
    return await record_view(state.redis, payload)


@app.post("/views/batch", status_code=202)
async def ingest_batch(payload: BatchViewRequest, state: Annotated[AppState, Depends(get_state)]):
    results = []
    for view in payload.views:
        results.append(await record_view(state.redis, view))
    return {"accepted": len(results), "views": results}


@app.get("/views/top-k")
async def top_k(
    state: Annotated[AppState, Depends(get_state)],
    window: Literal["hour", "day", "month", "all"] = Query(default="all"),
    k: int = Query(default=10, ge=1, le=1000),
    at: str | None = Query(default=None),
):
    if window not in VALID_WINDOWS:
        raise HTTPException(status_code=400, detail="unsupported window")
    viewed_at = parse_timestamp(at)
    key = bucket_key(window, viewed_at)
    rows = await state.redis.zrevrange(key, 0, min(k, settings.max_k) - 1, withscores=True)
    return {
        "window": window,
        "bucket": key,
        "k": k,
        "results": [{"videoId": video_id, "views": int(score)} for video_id, score in rows],
    }


@app.post("/reset")
async def reset(state: Annotated[AppState, Depends(get_state)]):
    keys = [key async for key in state.redis.scan_iter("views:*")]
    keys.extend([key async for key in state.redis.scan_iter("view-events")])
    if keys:
        await state.redis.delete(*keys)
    return {"status": "reset", "deleted": len(keys)}
