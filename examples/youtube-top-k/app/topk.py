from __future__ import annotations

from datetime import datetime, timezone


VALID_WINDOWS = {"hour", "day", "month", "all"}


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def bucket_key(window: str, viewed_at: datetime) -> str:
    if window == "all":
        return "views:all"
    if window == "hour":
        return f"views:hour:{viewed_at:%Y%m%d%H}"
    if window == "day":
        return f"views:day:{viewed_at:%Y%m%d}"
    if window == "month":
        return f"views:month:{viewed_at:%Y%m}"
    raise ValueError(f"unsupported window: {window}")


def bucket_ttl_seconds(window: str) -> int | None:
    if window == "hour":
        return 60 * 60 * 3
    if window == "day":
        return 60 * 60 * 24 * 3
    if window == "month":
        return 60 * 60 * 24 * 40
    return None
