import json
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8090"


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


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Online Auction" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    ends_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    status, auction = request_json(
        "/auctions",
        method="POST",
        payload={
            "title": "Vintage keyboard",
            "description": "Clicky local demo hardware.",
            "starting_price": "50.00",
            "ends_at": ends_at,
        },
    )
    assert status == 201 and auction["currentPrice"] == "50.00", (status, auction)
    auction_id = auction["auctionId"]

    status, own_bid = request_json(f"/auctions/{auction_id}/bids", method="POST", payload={"amount": "55.00"})
    assert status == 409, (status, own_bid)

    status, bid_one = request_json(
        f"/auctions/{auction_id}/bids",
        method="POST",
        payload={"amount": "75.00"},
        user_id="bob",
    )
    assert status == 201 and bid_one["currentWinner"] == "bob", (status, bid_one)

    status, stale_bid = request_json(
        f"/auctions/{auction_id}/bids",
        method="POST",
        payload={"amount": "70.00"},
        user_id="charlie",
    )
    assert status == 409, (status, stale_bid)

    status, bid_two = request_json(
        f"/auctions/{auction_id}/bids",
        method="POST",
        payload={"amount": "90.00"},
        user_id="charlie",
    )
    assert status == 201 and bid_two["currentWinner"] == "charlie", (status, bid_two)

    status, view = request_json(f"/auctions/{auction_id}")
    assert status == 200 and view["cache"] == "MISS" and len(view["bids"]) == 2, (status, view)

    status, cached = request_json(f"/auctions/{auction_id}")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok auction={auction_id}")
    print("ok bid ordering, stale bid rejection, cache miss/hit")


if __name__ == "__main__":
    main()
