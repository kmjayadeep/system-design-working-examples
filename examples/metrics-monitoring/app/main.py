from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.metrics import metric_key, parse_timestamp
from app.ui import ui_response


class AppState:
    redis: Redis


class MetricPoint(BaseModel):
    name: str = Field(min_length=1)
    value: float
    timestamp: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class MetricBatch(BaseModel):
    points: list[MetricPoint] = Field(min_length=1, max_length=1000)


class AlertRule(BaseModel):
    name: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    threshold: float
    direction: Literal["above", "below"] = "above"


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


app = FastAPI(title="Metrics Monitoring Prototype", lifespan=lifespan)


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


async def store_point(redis: Redis, point: MetricPoint) -> dict:
    ts = parse_timestamp(point.timestamp)
    sample = {"name": point.name, "value": point.value, "timestamp": ts.isoformat(), "tags": point.tags}
    key = metric_key(point.name)
    await redis.zadd(key, {json.dumps(sample): ts.timestamp()})
    await redis.expire(key, settings.retention_seconds)
    await redis.xadd("metric-events", {"name": point.name, "value": point.value, "timestamp": ts.isoformat()}, maxlen=1000)
    return sample


@app.post("/metrics", status_code=202)
async def ingest_metric(point: MetricPoint, state: Annotated[AppState, Depends(get_state)]):
    return await store_point(state.redis, point)


@app.post("/metrics/batch", status_code=202)
async def ingest_batch(payload: MetricBatch, state: Annotated[AppState, Depends(get_state)]):
    samples = []
    for point in payload.points:
        samples.append(await store_point(state.redis, point))
    return {"accepted": len(samples), "samples": samples}


@app.get("/metrics/{name}")
async def query_metric(
    name: str,
    state: Annotated[AppState, Depends(get_state)],
    since: float = Query(default=0),
    until: float = Query(default="+inf"),
):
    rows = await state.redis.zrangebyscore(metric_key(name), since, until)
    samples = [json.loads(row) for row in rows]
    avg = sum(sample["value"] for sample in samples) / len(samples) if samples else None
    return {"name": name, "count": len(samples), "avg": avg, "samples": samples}


@app.post("/alerts", status_code=201)
async def create_alert(rule: AlertRule, state: Annotated[AppState, Depends(get_state)]):
    rule_id = str(uuid.uuid4())
    await state.redis.hset(f"alert:{rule_id}", mapping=rule.model_dump())
    await state.redis.sadd("alerts", rule_id)
    return {"alertId": rule_id, **rule.model_dump()}


@app.post("/alerts/evaluate")
async def evaluate_alerts(state: Annotated[AppState, Depends(get_state)]):
    fired = []
    for rule_id in await state.redis.smembers("alerts"):
        rule = await state.redis.hgetall(f"alert:{rule_id}")
        latest = await state.redis.zrevrange(metric_key(rule["metric"]), 0, 0)
        if not latest:
            continue
        sample = json.loads(latest[0])
        threshold = float(rule["threshold"])
        is_firing = sample["value"] > threshold if rule["direction"] == "above" else sample["value"] < threshold
        if is_firing:
            event = {"alertId": rule_id, "name": rule["name"], "metric": rule["metric"], "value": sample["value"], "threshold": threshold}
            await state.redis.xadd("alert-events", event, maxlen=1000)
            fired.append(event)
    return {"fired": fired}
