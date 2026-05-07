import json
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8230"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(BASE_URL + path, data=data, headers={"content-type": "application/json", "connection": "close", "X-User-Id": user_id}, method=method)
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"})
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Google Docs" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    status, doc = request_json("/documents", "POST", {"title": "Design Notes"})
    assert status == 201 and doc["version"] == 0, doc
    doc_id = doc["documentId"]
    status, share = request_json(f"/documents/{doc_id}/share", "POST", {"userId": "bob", "permission": "write"})
    assert status == 201 and share["userId"] == "bob", share
    status, edit1 = request_json(f"/documents/{doc_id}/operations", "POST", {"baseVersion": 0, "text": "first"}, user_id="bob")
    assert status == 201 and edit1["version"] == 1, edit1
    status, edit2 = request_json(f"/documents/{doc_id}/operations", "POST", {"baseVersion": 1, "text": "second"})
    assert status == 201 and edit2["content"] == "first\nsecond", edit2
    status, loaded = request_json(f"/documents/{doc_id}", user_id="bob")
    assert status == 200 and loaded["version"] == 2, loaded
    status, events = request_json(f"/documents/{doc_id}/events?after={quote('0-0')}")
    assert status == 200 and [e["text"] for e in events["events"]] == ["first", "second"], events
    print(f"ok proxy instances={sorted(instances)}")
    print("ok document creation, sharing, versioned edits, and event polling")


if __name__ == "__main__":
    main()
