import json
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8180"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close", "X-User-Id": user_id},
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
    assert status == 200 and "FB Post Search" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    posts = []
    for user, content in [
        ("alice", "coffee and distributed systems"),
        ("bob", "coffee shops near work"),
        ("carol", "search indexing at scale"),
    ]:
        status, post = request_json("/posts", method="POST", payload={"content": content}, user_id=user)
        assert status == 201 and post["content"] == content, (status, post)
        posts.append(post)

    for user in ["dave", "erin", "frank"]:
        status, like = request_json("/likes", method="POST", payload={"postId": posts[0]["postId"]}, user_id=user)
        assert status == 201 and like["post"]["likeCount"] >= 1, (status, like)
    status, duplicate = request_json("/likes", method="POST", payload={"postId": posts[0]["postId"]}, user_id="dave")
    assert status == 201 and duplicate["liked"] is False and duplicate["post"]["likeCount"] == 3, (status, duplicate)
    request_json("/likes", method="POST", payload={"postId": posts[1]["postId"]}, user_id="grace")

    status, recency = request_json(f"/search?q={quote('coffee')}&sort=recency")
    assert status == 200 and [item["postId"] for item in recency["results"][:2]] == [posts[1]["postId"], posts[0]["postId"]], recency
    assert recency["cached"] is False

    status, cached = request_json(f"/search?q={quote('coffee')}&sort=recency")
    assert status == 200 and cached["cached"] is True, cached

    status, likes = request_json(f"/search?q={quote('coffee')}&sort=likes")
    assert status == 200 and [item["postId"] for item in likes["results"][:2]] == [posts[0]["postId"], posts[1]["postId"]], likes

    status, multi = request_json(f"/search?q={quote('search indexing')}&sort=recency")
    assert status == 200 and [item["postId"] for item in multi["results"]] == [posts[2]["postId"]], multi

    print(f"ok proxy instances={sorted(instances)}")
    print("ok post creation, likes, cached keyword search, and sort modes")


if __name__ == "__main__":
    main()
