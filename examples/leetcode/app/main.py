from __future__ import annotations

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
from app.runner import evaluate_python
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class SubmitRequest(BaseModel):
    language: str = Field(default="python", pattern="^python$")
    code: str = Field(min_length=1, max_length=10000)
    competition_id: str | None = None


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def problem_summary(row: asyncpg.Record) -> dict:
    return {"problemId": row["id"], "title": row["title"], "difficulty": row["difficulty"], "tags": row["tags"]}


def problem_payload(row: asyncpg.Record) -> dict:
    payload = problem_summary(row)
    payload.update({"statement": row["statement"], "codeStub": row["code_stub"]})
    return payload


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


app = FastAPI(title="LeetCode Prototype", lifespan=lifespan)


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


@app.get("/problems")
async def list_problems(state: Annotated[AppState, Depends(get_state)], page: int = 1, limit: int = Query(default=20, ge=1, le=100)):
    rows = await state.db.fetch("SELECT * FROM problems ORDER BY id LIMIT $1 OFFSET $2", limit, (page - 1) * limit)
    return {"problems": [problem_summary(row) for row in rows]}


@app.get("/problems/{problem_id}")
async def get_problem(
    problem_id: str,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    cache_key = f"problem:{problem_id}"
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload
    row = await state.db.fetchrow("SELECT * FROM problems WHERE id = $1", problem_id)
    if row is None:
        raise HTTPException(status_code=404, detail="problem not found")
    payload = problem_payload(row)
    payload["cache"] = "MISS"
    await state.redis.set(cache_key, json.dumps({k: v for k, v in payload.items() if k != "cache"}), ex=config.problem_cache_ttl_seconds)
    return payload


@app.post("/problems/{problem_id}/submit", status_code=202)
async def submit(
    problem_id: str,
    payload: SubmitRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    problem = await state.db.fetchrow("SELECT id FROM problems WHERE id = $1", problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="problem not found")
    submission_id = uuid.uuid4()
    await state.db.execute(
        """
        INSERT INTO submissions (id, user_id, problem_id, competition_id, language, code, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'queued')
        """,
        submission_id,
        actor_user_id,
        problem_id,
        payload.competition_id,
        payload.language,
        payload.code,
    )
    await state.redis.rpush("submissions", str(submission_id))
    return {"submissionId": str(submission_id), "status": "queued"}


@app.post("/workers/judge/tick")
async def judge_tick(state: Annotated[AppState, Depends(get_state)], limit: int = 10):
    processed = 0
    for _ in range(limit):
        raw = await state.redis.lpop("submissions")
        if raw is None:
            break
        submission_id = uuid.UUID(raw.decode() if isinstance(raw, bytes) else raw)
        submission = await state.db.fetchrow("SELECT * FROM submissions WHERE id = $1", submission_id)
        if submission is None or submission["status"] != "queued":
            continue
        cases = await state.db.fetch("SELECT input, expected FROM test_cases WHERE problem_id = $1 ORDER BY id", submission["problem_id"])
        result = evaluate_python(submission["code"], [dict(case) for case in cases])
        await state.db.execute(
            """
            UPDATE submissions
            SET status = $2, passed_tests = $3, total_tests = $4, message = $5
            WHERE id = $1
            """,
            submission_id,
            result["status"],
            result["passed"],
            result["total"],
            result["message"],
        )
        processed += 1
    return {"processed": processed}


@app.get("/submissions/{submission_id}")
async def get_submission(submission_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    row = await state.db.fetchrow("SELECT * FROM submissions WHERE id = $1", submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="submission not found")
    return {
        "submissionId": str(row["id"]),
        "userId": row["user_id"],
        "problemId": row["problem_id"],
        "status": row["status"],
        "passedTests": row["passed_tests"],
        "totalTests": row["total_tests"],
        "message": row["message"],
    }


@app.get("/leaderboard/{competition_id}")
async def leaderboard(competition_id: str, state: Annotated[AppState, Depends(get_state)], limit: int = Query(default=100, ge=1, le=100)):
    rows = await state.db.fetch(
        """
        SELECT user_id, COUNT(DISTINCT problem_id)::int AS solved, MAX(created_at) AS last_solve
        FROM submissions
        WHERE competition_id = $1 AND status = 'accepted'
        GROUP BY user_id
        ORDER BY solved DESC, last_solve ASC
        LIMIT $2
        """,
        competition_id,
        limit,
    )
    return {
        "competitionId": competition_id,
        "rankings": [
            {"rank": index, "userId": row["user_id"], "solved": row["solved"], "lastSolveAt": row["last_solve"].isoformat()}
            for index, row in enumerate(rows, start=1)
        ],
    }
