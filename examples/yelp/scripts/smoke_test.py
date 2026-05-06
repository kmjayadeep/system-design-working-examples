import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8070"


def request_json(path, method="GET", payload=None, user_id="dave"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={
            "content-type": "application/json",
            "connection": "close",
            "X-User-Id": user_id,
        },
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


def main():
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    query = urlencode(
        {
            "q": "tacos",
            "category": "restaurants",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius_km": 5,
        }
    )
    status, search = request_json(f"/businesses/search?{query}")
    assert status == 200 and search["cache"] == "MISS", (status, search)
    assert search["businesses"][0]["id"] == "biz-1"

    status, cached = request_json(f"/businesses/search?{query}")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, details = request_json("/businesses/biz-1")
    assert status == 200
    assert details["business"]["averageRating"] == 4.5
    assert len(details["reviews"]) == 2

    status, created = request_json(
        "/businesses/biz-1/reviews",
        method="POST",
        payload={"rating": 3, "text": "Solid lunch."},
    )
    assert status == 201 and created["status"] == "created", (status, created)

    status, duplicate = request_json(
        "/businesses/biz-1/reviews",
        method="POST",
        payload={"rating": 5, "text": "Duplicate"},
    )
    assert status == 409, (status, duplicate)

    status, updated = request_json("/businesses/biz-1")
    assert status == 200
    assert updated["business"]["reviewCount"] == 3
    assert updated["business"]["averageRating"] == 4.0

    status, refreshed = request_json(f"/businesses/search?{query}")
    assert status == 200 and refreshed["cache"] == "MISS", (status, refreshed)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok cached search by name/category/location")
    print("ok reviews and average rating update")
    print("ok one review per user")


if __name__ == "__main__":
    main()
