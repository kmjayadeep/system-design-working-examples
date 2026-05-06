from app.geo import haversine_km


def test_distance_same_point_is_zero():
    assert haversine_km(37.0, -122.0, 37.0, -122.0) == 0


def test_distance_sf_to_oakland():
    assert 10 < haversine_km(37.7749, -122.4194, 37.8044, -122.2711) < 20
