import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8080"


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
    assert status == 200 and "Strava Activity Tracking" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, activity = request_json("/activities", method="POST", payload={"activity_type": "run"})
    assert status == 201 and activity["status"] == "active", (status, activity)
    activity_id = activity["activityId"]

    points = [
        {"latitude": 37.7749, "longitude": -122.4194, "recorded_at": "2026-05-07T10:00:00Z"},
        {"latitude": 37.7759, "longitude": -122.4184, "recorded_at": "2026-05-07T10:02:00Z"},
        {"latitude": 37.7769, "longitude": -122.4174, "recorded_at": "2026-05-07T10:04:00Z"},
    ]
    status, live = request_json(f"/activities/{activity_id}/points", method="POST", payload={"points": points})
    assert status == 200 and live["pointCount"] == 3 and live["distanceKm"] > 0, (status, live)

    status, paused = request_json(f"/activities/{activity_id}/pause", method="POST")
    assert status == 200 and paused["status"] == "paused", (status, paused)

    status, resumed = request_json(f"/activities/{activity_id}/resume", method="POST")
    assert status == 200 and resumed["status"] == "active", (status, resumed)

    status, stopped = request_json(f"/activities/{activity_id}/stop", method="POST")
    assert status == 200 and stopped["status"] == "stopped", (status, stopped)

    status, saved = request_json(f"/activities/{activity_id}/save", method="POST")
    assert status == 200 and saved["status"] == "saved", (status, saved)

    status, live_missing = request_json(f"/activities/{activity_id}/live")
    assert status == 404, (status, live_missing)

    status, details = request_json(f"/activities/{activity_id}")
    assert status == 200 and len(details["points"]) == 3, (status, details)

    status, bob_details = request_json(f"/activities/{activity_id}", user_id="bob")
    assert status == 200 and bob_details["userId"] == "alice", (status, bob_details)

    status, charlie_details = request_json(f"/activities/{activity_id}", user_id="charlie")
    assert status == 404, (status, charlie_details)

    status, feed = request_json("/activities/feed", user_id="bob")
    assert status == 200 and feed["activities"][0]["activityId"] == activity_id, (status, feed)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok activity={activity_id}")
    print("ok live stats, lifecycle transitions, save, and friend feed")


if __name__ == "__main__":
    main()
