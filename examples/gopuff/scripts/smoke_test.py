import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8020"
SF = {"latitude": 37.7749, "longitude": -122.4194}


def request_json(path, method="GET", payload=None, user_id="alice"):
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

    query = urlencode({**SF, "item_id": "cheetos"})
    status, availability = request_json(f"/availability?{query}")
    assert status == 200, (status, availability)
    assert availability["cache"] == "MISS"
    assert availability["items"][0]["itemId"] == "cheetos"
    assert availability["items"][0]["availableQuantity"] == 8

    status, cached = request_json(f"/availability?{query}")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, order = request_json(
        "/orders",
        method="POST",
        payload={**SF, "items": [{"item_id": "cheetos", "quantity": 4}]},
    )
    assert status == 201 and order["status"] == "created", (status, order)

    status, after_order = request_json(f"/availability?{query}")
    assert status == 200, (status, after_order)
    assert after_order["cache"] == "MISS"
    assert after_order["items"][0]["availableQuantity"] == 4

    status, conflict = request_json(
        "/orders",
        method="POST",
        payload={**SF, "items": [{"item_id": "cheetos", "quantity": 5}]},
        user_id="bob",
    )
    assert status == 409, (status, conflict)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok order={order['orderId']}")
    print("ok availability cache miss/hit and invalidation")
    print("ok oversell prevention")


if __name__ == "__main__":
    main()
