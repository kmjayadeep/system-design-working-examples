import base64
import json
from datetime import datetime


def encode_cursor(published_at: datetime, article_id: str) -> str:
    payload = {"published_at": published_at.isoformat(), "article_id": article_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["published_at"]), payload["article_id"]
