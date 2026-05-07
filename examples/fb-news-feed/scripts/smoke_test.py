import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8120"


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
    assert status == 200 and "FB News Feed" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, follow = request_json("/users/bob/follow", method="PUT")
    assert status == 200 and follow["status"] == "following", (status, follow)

    post_ids = []
    for index in range(3):
        status, post = request_json(
            "/posts",
            method="POST",
            payload={"content": {"text": f"post {index}"}},
            user_id="bob",
        )
        assert status == 201 and post["status"] == "queued_for_fanout", (status, post)
        post_ids.append(post["postId"])

    status, empty_feed = request_json("/feed?page_size=5")
    assert status == 200 and empty_feed["items"] == [], (status, empty_feed)

    status, fanout = request_json("/workers/fanout/tick?limit=10", method="POST")
    assert status == 200 and fanout["jobsProcessed"] == 3 and fanout["feedWrites"] >= 6, (status, fanout)

    status, feed = request_json("/feed?page_size=2")
    assert status == 200 and len(feed["items"]) == 2 and feed["nextCursor"], (status, feed)
    assert feed["items"][0]["postId"] == post_ids[-1], feed

    status, second_page = request_json(f"/feed?page_size=2&cursor={quote(feed['nextCursor'])}")
    assert status == 200 and len(second_page["items"]) == 1, (status, second_page)

    status, dave_feed = request_json("/feed?page_size=5", user_id="dave")
    assert status == 200 and len(dave_feed["items"]) == 3, (status, dave_feed)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok follow, post creation, async fanout, and cursor paging")


if __name__ == "__main__":
    main()
