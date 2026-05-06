from datetime import UTC, datetime

from app.timeutils import minute_bucket


def test_minute_bucket_truncates_seconds():
    assert minute_bucket(datetime(2026, 5, 6, 12, 34, 56, tzinfo=UTC)) == datetime(
        2026, 5, 6, 12, 34, tzinfo=UTC
    )
