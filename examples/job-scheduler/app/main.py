from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class JobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    payload: dict = Field(default_factory=dict)
    run_at: str | None = Field(default=None, alias="runAt")
    delay_seconds: int = Field(default=0, alias="delaySeconds", ge=0, le=86400)
    max_attempts: int = Field(default=3, alias="maxAttempts", ge=1, le=10)


def parse_run_at(payload: JobRequest) -> datetime:
    if payload.run_at:
        parsed = datetime.fromisoformat(payload.run_at.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) + timedelta(seconds=payload.delay_seconds)


def normalize_payload(payload) -> dict:
    if isinstance(payload, str):
        return json.loads(payload)
    return payload or {}


def should_fail(payload) -> bool:
    payload = normalize_payload(payload)
    return bool(payload.get("fail"))


def get_state(request: Request) -> AppState:
    return request.app.state.services


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


app = FastAPI(title="Job Scheduler Prototype", lifespan=lifespan)


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


def job_payload(row: asyncpg.Record) -> dict:
    return {
        "jobId": str(row["id"]),
        "name": row["name"],
        "payload": normalize_payload(row["payload"]),
        "runAt": row["run_at"].isoformat(),
        "status": row["status"],
        "attempts": row["attempts"],
        "maxAttempts": row["max_attempts"],
        "lastError": row["last_error"],
    }


@app.post("/jobs", status_code=201)
async def create_job(payload: JobRequest, state: Annotated[AppState, Depends(get_state)]):
    job_id = uuid.uuid4()
    run_at = parse_run_at(payload)
    row = await state.db.fetchrow(
        """
        INSERT INTO jobs (id, name, payload, run_at, status, max_attempts)
        VALUES ($1, $2, $3::jsonb, $4, 'scheduled', $5)
        RETURNING *
        """,
        job_id,
        payload.name,
        json.dumps(payload.payload),
        run_at,
        payload.max_attempts,
    )
    await state.redis.zadd("jobs:due", {str(job_id): run_at.timestamp()})
    return job_payload(row)


@app.post("/jobs/run-due")
async def run_due_jobs(state: Annotated[AppState, Depends(get_state)], limit: int = Query(default=10, ge=1, le=100)):
    rows = await state.db.fetch(
        """
        SELECT *
        FROM jobs
        WHERE status = 'scheduled' AND run_at <= now()
        ORDER BY run_at ASC
        LIMIT $1
        FOR UPDATE SKIP LOCKED
        """,
        limit,
    )
    results = []
    async with state.db.acquire() as conn:
        for row in rows:
            async with conn.transaction():
                job = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1 FOR UPDATE", row["id"])
                if job is None or job["status"] != "scheduled" or job["run_at"] > datetime.now(timezone.utc):
                    continue
                attempts = job["attempts"] + 1
                if should_fail(job["payload"]):
                    status = "failed" if attempts >= job["max_attempts"] else "scheduled"
                    error = "simulated failure"
                    run_at = datetime.now(timezone.utc) + timedelta(seconds=1) if status == "scheduled" else job["run_at"]
                    updated = await conn.fetchrow(
                        "UPDATE jobs SET status = $1, attempts = $2, run_at = $3, last_error = $4, updated_at = now() WHERE id = $5 RETURNING *",
                        status,
                        attempts,
                        run_at,
                        error,
                        job["id"],
                    )
                    await conn.execute("INSERT INTO job_runs (job_id, status, output) VALUES ($1, 'failed', $2)", job["id"], error)
                    if status == "scheduled":
                        await state.redis.zadd("jobs:due", {str(job["id"]): run_at.timestamp()})
                else:
                    updated = await conn.fetchrow(
                        "UPDATE jobs SET status = 'succeeded', attempts = $1, updated_at = now() WHERE id = $2 RETURNING *",
                        attempts,
                        job["id"],
                    )
                    await conn.execute("INSERT INTO job_runs (job_id, status, output) VALUES ($1, 'succeeded', 'executed')", job["id"])
                    await state.redis.zrem("jobs:due", str(job["id"]))
                results.append(job_payload(updated))
    return {"ran": len(results), "jobs": results}


@app.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    row = await state.db.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    return job_payload(row)


@app.get("/jobs/{job_id}/runs")
async def get_runs(job_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch("SELECT * FROM job_runs WHERE job_id = $1 ORDER BY id", job_id)
    return {"runs": [{"status": row["status"], "output": row["output"], "createdAt": row["created_at"].isoformat()} for row in rows]}
