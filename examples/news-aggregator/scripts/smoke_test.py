import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE_URL = "http://localhost:8060"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = build_opener(NoRedirect)


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close"},
        method=method,
    )
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, dict(exc.headers), body


def main():
    instances = set()
    for _ in range(12):
        status, _, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, _, feed = request_json("/feed?limit=2")
    assert status == 200 and feed["cache"] == "MISS", (status, feed)
    assert [article["title"] for article in feed["articles"]] == [
        "Local Team Wins",
        "New Database Released",
    ]
    first_article_id = feed["articles"][0]["id"]

    status, _, cached = request_json("/feed?limit=2")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    cursor = quote(feed["nextCursor"])
    status, _, second_page = request_json(f"/feed?limit=2&cursor={cursor}")
    assert status == 200
    assert [article["title"] for article in second_page["articles"]] == ["Markets Open Higher"]

    status, _, tech = request_json("/feed?limit=5&category=technology")
    assert status == 200
    assert [article["category"] for article in tech["articles"]] == ["technology"]

    status, _, ingested = request_json(
        "/ingest/articles",
        method="POST",
        payload={
            "publisher_id": "tech-wire",
            "title": "Breaking Cache News",
            "summary": "A new cache invalidation story.",
            "category": "technology",
            "publisher_url": "https://publisher.example/cache",
            "published_at": "2026-05-06T10:03:00Z",
        },
    )
    assert status == 201 and ingested["status"] == "ingested", (status, ingested)

    status, _, refreshed = request_json("/feed?limit=1")
    assert status == 200 and refreshed["cache"] == "MISS"
    assert refreshed["articles"][0]["title"] == "Breaking Cache News"

    status, headers, _ = request_json(f"/articles/{first_article_id}/redirect")
    assert status == 302, (status, headers)
    assert headers["location"].startswith("https://publisher.example/")

    print(f"ok proxy instances={sorted(instances)}")
    print("ok cached feed and cursor pagination")
    print("ok ingest invalidates cache")
    print("ok publisher redirect")


if __name__ == "__main__":
    main()
