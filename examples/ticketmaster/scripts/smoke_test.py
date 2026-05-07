import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8110"


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
    assert status == 200 and "Ticketmaster Booking" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, search = request_json("/events/search?q=jazz&city=San%20Francisco")
    assert status == 200 and search["events"][0]["id"] == "evt-jazz", (status, search)

    status, event = request_json("/events/evt-jazz")
    assert status == 200 and event["cache"] == "MISS", (status, event)

    status, cached = request_json("/events/evt-jazz")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, reservation = request_json(
        "/events/evt-jazz/reservations",
        method="POST",
        payload={"ticket_ids": ["t-jazz-a1", "t-jazz-a2"]},
    )
    assert status == 201 and reservation["status"] == "reserved", (status, reservation)

    status, conflict = request_json(
        "/events/evt-jazz/reservations",
        method="POST",
        payload={"ticket_ids": ["t-jazz-a1"]},
        user_id="bob",
    )
    assert status == 409, (status, conflict)

    status, booking = request_json(
        "/bookings",
        method="POST",
        payload={"reservation_id": reservation["reservationId"]},
    )
    assert status == 201 and booking["status"] == "confirmed", (status, booking)

    status, sold_conflict = request_json(
        "/events/evt-jazz/reservations",
        method="POST",
        payload={"ticket_ids": ["t-jazz-a1"]},
        user_id="bob",
    )
    assert status == 409, (status, sold_conflict)

    status, refreshed = request_json("/events/evt-jazz")
    assert status == 200 and refreshed["cache"] == "MISS"
    sold = {ticket["ticketId"]: ticket["status"] for ticket in refreshed["tickets"]}
    assert sold["t-jazz-a1"] == "sold" and sold["t-jazz-a2"] == "sold", sold

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok reservation={reservation['reservationId']}")
    print(f"ok booking={booking['bookingId']}")
    print("ok search, event cache, reservation conflict, and sold tickets")


if __name__ == "__main__":
    main()
