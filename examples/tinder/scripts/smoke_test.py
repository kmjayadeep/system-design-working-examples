import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8130"
SF = {"latitude": 37.7749, "longitude": -122.4194}


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
    assert status == 200 and "Tinder Matching" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, profile = request_json(
        "/profile",
        method="POST",
        payload={
            "name": "Alice",
            "age": 29,
            "gender": "female",
            "interested_in": "male",
            "min_age": 24,
            "max_age": 38,
            "max_distance_km": 15,
            **SF,
        },
    )
    assert status == 201 and profile["status"] == "saved", (status, profile)

    status, feed = request_json(f"/feed?latitude={SF['latitude']}&longitude={SF['longitude']}")
    assert status == 200 and feed["cache"] == "MISS", (status, feed)
    assert [item["userId"] for item in feed["profiles"]] == ["bob"], feed

    status, cached = request_json(f"/feed?latitude={SF['latitude']}&longitude={SF['longitude']}")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, alice_swipe = request_json("/swipe/bob", method="POST", payload={"decision": "yes"})
    assert status == 201 and not alice_swipe["matched"], (status, alice_swipe)

    status, bob_swipe = request_json("/swipe/alice", method="POST", payload={"decision": "yes"}, user_id="bob")
    assert status == 201 and bob_swipe["matched"], (status, bob_swipe)

    status, matches = request_json("/matches")
    assert status == 200 and matches["matches"][0]["matchedUserId"] == "bob", (status, matches)

    status, refreshed = request_json(f"/feed?latitude={SF['latitude']}&longitude={SF['longitude']}")
    assert status == 200 and refreshed["profiles"] == [], (status, refreshed)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok profile, recommendation feed, swipe consistency, and mutual match")


if __name__ == "__main__":
    main()
