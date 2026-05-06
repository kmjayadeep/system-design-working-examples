from datetime import UTC, datetime

from app.cursor import decode_cursor, encode_cursor


def test_cursor_round_trip():
    published_at = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    cursor = encode_cursor(published_at, "00000000-0000-0000-0000-000000000001")
    assert decode_cursor(cursor) == (published_at, "00000000-0000-0000-0000-000000000001")
