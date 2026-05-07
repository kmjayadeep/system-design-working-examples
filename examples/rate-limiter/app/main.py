from __future__ import annotations

import socket
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.limiter import TokenBucketRule, refill_tokens, retry_after_ms
from app.ui import ui_response


class AppState:
    redis: Redis


class RuleRequest(BaseModel):
    rule_id: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    refill_per_second: float = Field(gt=0)


DEFAULT_RULE = TokenBucketRule("default", capacity=5, refill_per_second=1)
BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local state = redis.call('HMGET', key, 'tokens', 'updated_at')
local tokens = tonumber(state[1])
local updated = tonumber(state[2])
if tokens == nil then
  tokens = capacity
  updated = now
end
local elapsed = math.max(0, now - updated)
tokens = math.min(capacity, tokens + (elapsed * refill))
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call('HMSET', key, 'tokens', tokens, 'updated_at', now)
redis.call('EXPIRE', key, math.ceil((capacity / refill) * 2))
local retry = 0
if allowed == 0 then
  retry = math.ceil(((1 - tokens) / refill) * 1000)
end
return {allowed, math.floor(tokens), retry}
"""


def get_state(request: Request) -> AppState:
    return request.app.state.services


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.redis = Redis.from_url(settings.redis_url)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()


app = FastAPI(title="Distributed Rate Limiter Prototype", lifespan=lifespan)


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


async def get_rule(redis: Redis, rule_id: str) -> TokenBucketRule:
    data = await redis.hgetall(f"rule:{rule_id}")
    if not data:
        return DEFAULT_RULE if rule_id == "default" else await get_rule(redis, "default")
    return TokenBucketRule(
        rule_id=rule_id,
        capacity=int(data[b"capacity"]),
        refill_per_second=float(data[b"refill_per_second"]),
    )


@app.post("/rules", status_code=201)
async def upsert_rule(payload: RuleRequest, state: Annotated[AppState, Depends(get_state)]):
    await state.redis.hset(
        f"rule:{payload.rule_id}",
        mapping={"capacity": payload.capacity, "refill_per_second": payload.refill_per_second},
    )
    return {"status": "saved", "ruleId": payload.rule_id}


@app.post("/check")
async def check_request(
    state: Annotated[AppState, Depends(get_state)],
    client_id: str = Query(min_length=1),
    rule_id: str = Query(default="default"),
):
    rule = await get_rule(state.redis, rule_id)
    now = time.time()
    key = f"bucket:{rule.rule_id}:{client_id}"
    allowed, remaining, retry = await state.redis.eval(
        BUCKET_SCRIPT,
        1,
        key,
        rule.capacity,
        rule.refill_per_second,
        now,
    )
    return {
        "allowed": bool(allowed),
        "clientId": client_id,
        "ruleId": rule.rule_id,
        "remaining": int(remaining),
        "retryAfterMs": None if allowed else int(retry),
    }


@app.post("/reset")
async def reset(state: Annotated[AppState, Depends(get_state)]):
    keys = await state.redis.keys("bucket:*")
    if keys:
        await state.redis.delete(*keys)
    return {"status": "reset", "deleted": len(keys)}
