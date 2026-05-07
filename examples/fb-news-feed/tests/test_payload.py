import json
from types import SimpleNamespace

from app.main import post_payload


def test_post_payload_decodes_json_content():
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "author_id": "alice",
        "content": json.dumps({"text": "hello"}),
        "created_at": SimpleNamespace(isoformat=lambda: "now"),
    }

    assert post_payload(row)["content"] == {"text": "hello"}
