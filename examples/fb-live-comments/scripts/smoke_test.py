import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8170"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close", "X-User-Id": user_id},
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, body


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "FB Live Comments" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    ids = []
    for user, message in [("alice", "first"), ("bob", "second"), ("charlie", "third")]:
        status, comment = request_json("/comments/live-1", method="POST", payload={"message": message}, user_id=user)
        assert status == 201 and comment["message"] == message, (status, comment)
        ids.append(comment["commentId"])

    status, history = request_json("/comments/live-1?page_size=2")
    assert status == 200 and [item["message"] for item in history["comments"]] == ["third", "second"], (status, history)
    assert history["nextCursor"]

    status, older = request_json(f"/comments/live-1?page_size=2&cursor={quote(history['nextCursor'])}")
    assert status == 200 and [item["message"] for item in older["comments"]] == ["first"], (status, older)

    status, stream = request_json("/comments/live-1/stream?after=0-0&count=10")
    assert status == 200 and len(stream["events"]) == 3, (status, stream)
    last_stream_id = stream["events"][-1]["streamId"]

    request_json("/comments/live-1", method="POST", payload={"message": "fourth"}, user_id="dave")
    status, incremental = request_json(f"/comments/live-1/stream?after={quote(last_stream_id)}&count=10")
    assert status == 200 and [item["message"] for item in incremental["events"]] == ["fourth"], (status, incremental)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok comment creation, cursor history, and stream polling")


if __name__ == "__main__":
    main()
