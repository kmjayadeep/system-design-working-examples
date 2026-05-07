from __future__ import annotations

import socket
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.ring import owner_for_key
from app.ui import ui_response


class AppState:
    redis: Redis


class CacheValueRequest(BaseModel):
    value: str = Field(max_length=10000)
    ttl_seconds: int | None = Field(default=60, alias="ttlSeconds", ge=1, le=3600)


def nodes() -> list[str]:
    return [node.strip() for node in settings.cache_nodes.split(",") if node.strip()]


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


app = FastAPI(title="Distributed Cache Prototype", lifespan=lifespan)


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


@app.put("/cache/{key:path}")
async def set_cache(key: str, payload: CacheValueRequest, state: Annotated[AppState, Depends(get_state)]):
    owner = owner_for_key(key, nodes())
    redis_key = f"cache:{owner}:{key}"
    if payload.ttl_seconds:
        await state.redis.setex(redis_key, payload.ttl_seconds, payload.value)
    else:
        await state.redis.set(redis_key, payload.value)
    return {"key": key, "owner": owner, "status": "stored"}


@app.get("/cache/{key:path}")
async def get_cache(key: str, state: Annotated[AppState, Depends(get_state)]):
    owner = owner_for_key(key, nodes())
    value = await state.redis.get(f"cache:{owner}:{key}")
    if value is None:
        raise HTTPException(status_code=404, detail="cache miss")
    ttl = await state.redis.ttl(f"cache:{owner}:{key}")
    return {"key": key, "owner": owner, "value": value, "ttlSeconds": ttl, "hit": True}


@app.delete("/cache/{key:path}")
async def delete_cache(key: str, state: Annotated[AppState, Depends(get_state)]):
    owner = owner_for_key(key, nodes())
    deleted = await state.redis.delete(f"cache:{owner}:{key}")
    return {"key": key, "owner": owner, "deleted": bool(deleted)}


@app.get("/ring/{key:path}")
async def ring_lookup(key: str):
    return {"key": key, "nodes": nodes(), "owner": owner_for_key(key, nodes())}
