from app.geo import route_distance_km


def test_route_distance_accumulates_segments():
    points = [
        {"latitude": 37.7749, "longitude": -122.4194},
        {"latitude": 37.7759, "longitude": -122.4184},
        {"latitude": 37.7769, "longitude": -122.4174},
    ]

    assert 0.25 < route_distance_km(points) < 0.35


def test_route_distance_requires_two_points():
    assert route_distance_km([]) == 0
    assert route_distance_km([{"latitude": 1, "longitude": 2}]) == 0
