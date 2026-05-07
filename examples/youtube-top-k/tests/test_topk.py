from datetime import datetime, timezone

from app.topk import bucket_key, parse_timestamp


def test_bucket_keys_for_tumbling_windows():
    viewed_at = datetime(2026, 5, 7, 13, 45, tzinfo=timezone.utc)
    assert bucket_key("hour", viewed_at) == "views:hour:2026050713"
    assert bucket_key("day", viewed_at) == "views:day:20260507"
    assert bucket_key("month", viewed_at) == "views:month:202605"
    assert bucket_key("all", viewed_at) == "views:all"


def test_parse_timestamp_defaults_timezone_to_utc():
    assert parse_timestamp("2026-05-07T13:45:00").tzinfo == timezone.utc
