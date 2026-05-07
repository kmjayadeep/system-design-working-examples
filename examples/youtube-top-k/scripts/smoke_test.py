import json
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8190"
AT = "2026-05-07T13:45:00Z"


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close"},
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "YouTube Top K" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    request_json("/reset", method="POST")
    payload = {
        "views": [
            {"videoId": "video-a", "count": 10, "viewedAt": AT},
            {"videoId": "video-b", "count": 7, "viewedAt": AT},
            {"videoId": "video-c", "count": 3, "viewedAt": AT},
            {"videoId": "video-a", "count": 4, "viewedAt": AT},
        ]
    }
    status, batch = request_json("/views/batch", method="POST", payload=payload)
    assert status == 202 and batch["accepted"] == 4, (status, batch)

    for window in ["all", "hour", "day", "month"]:
        status, top = request_json(f"/views/top-k?window={window}&k=2&at={quote(AT)}")
        assert status == 200, (status, top)
        assert [(item["videoId"], item["views"]) for item in top["results"]] == [("video-a", 14), ("video-b", 7)], top

    status, limited = request_json(f"/views/top-k?window=all&k=1&at={quote(AT)}")
    assert status == 200 and limited["results"] == [{"videoId": "video-a", "views": 14}], limited

    print(f"ok proxy instances={sorted(instances)}")
    print("ok view ingestion and top-k queries across all windows")


if __name__ == "__main__":
    main()
