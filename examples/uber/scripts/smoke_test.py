import json
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8200"


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close"},
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
    assert status == 200 and "Uber" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    drivers = [
        ("driver-near", 37.7750, -122.4195),
        ("driver-farther", 37.7790, -122.4230),
    ]
    for driver_id, lat, lng in drivers:
        status, driver = request_json(f"/drivers/{quote(driver_id)}/location", method="POST", payload={"lat": lat, "lng": lng, "available": True})
        assert status == 200 and driver["status"] == "available", (status, driver)

    estimate_path = "/fare-estimate?startLat=37.7749&startLng=-122.4194&destLat=37.8044&destLng=-122.2712"
    status, estimate = request_json(estimate_path)
    assert status == 200 and estimate["estimatedFare"] > 5, (status, estimate)

    ride_payload = {
        "riderId": "rider-1",
        "startLat": 37.7749,
        "startLng": -122.4194,
        "destLat": 37.8044,
        "destLng": -122.2712,
    }
    status, ride = request_json("/rides", method="POST", payload=ride_payload)
    assert status == 201 and ride["driverId"] == "driver-near" and ride["status"] == "requested", (status, ride)

    status, second = request_json("/rides", method="POST", payload={**ride_payload, "riderId": "rider-2"})
    assert status == 201 and second["driverId"] == "driver-farther", (status, second)

    status, accepted = request_json(f"/rides/{ride['rideId']}/respond", method="POST", payload={"driverId": "driver-near", "accept": True})
    assert status == 200 and accepted["status"] == "accepted", (status, accepted)

    status, completed = request_json(f"/rides/{ride['rideId']}/complete", method="POST")
    assert status == 200 and completed["status"] == "completed", (status, completed)

    status, fetched = request_json(f"/rides/{ride['rideId']}")
    assert status == 200 and fetched["status"] == "completed", (status, fetched)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok fare estimates, nearby matching, assignment locking, and ride lifecycle")


if __name__ == "__main__":
    main()
