import json
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8210"


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


def put_bytes(url: str, data: bytes):
    request = Request(url, data=data, headers={"connection": "close"}, method="PUT")
    with urlopen(request, timeout=10) as response:
        return response.status


def publish_for(user_id: str, caption: str, media_type: str = "photo"):
    status, upload = request_json("/media/uploads", method="POST", payload={"mediaType": media_type}, user_id=user_id)
    assert status == 201 and upload["status"] == "pending", (status, upload)
    assert put_bytes(upload["uploadUrl"], b"fake image bytes") == 200
    status, post = request_json("/posts", method="POST", payload={"postId": upload["postId"], "caption": caption}, user_id=user_id)
    assert status == 201 and post["caption"] == caption and post["mediaUrl"], (status, post)
    return post


def main():
    status, html = get_text("/")
    assert status == 200 and "Instagram" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    alice_post = publish_for("alice", "alice photo")
    bob_post = publish_for("bob", "bob video", media_type="video")

    status, follow = request_json("/follows", method="POST", payload={"userId": "alice"}, user_id="carol")
    assert status == 201 and follow["followeeId"] == "alice", (status, follow)
    status, follow = request_json("/follows", method="POST", payload={"userId": "bob"}, user_id="carol")
    assert status == 201 and follow["followeeId"] == "bob", (status, follow)

    status, feed = request_json("/feed", user_id="carol")
    assert status == 200, (status, feed)
    captions = [post["caption"] for post in feed["posts"]]
    assert captions == ["bob video", "alice photo"], feed
    assert {post["postId"] for post in feed["posts"]} == {alice_post["postId"], bob_post["postId"]}

    status, alice_posts = request_json("/users/alice/posts", user_id="carol")
    assert status == 200 and [post["caption"] for post in alice_posts["posts"]] == ["alice photo"], alice_posts

    print(f"ok proxy instances={sorted(instances)}")
    print("ok media upload, post publish, follows, and chronological feed")


if __name__ == "__main__":
    main()
