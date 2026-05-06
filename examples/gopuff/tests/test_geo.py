from app.geo import haversine_km


def test_haversine_same_point_is_zero():
    assert haversine_km(37.7749, -122.4194, 37.7749, -122.4194) == 0


def test_haversine_san_francisco_to_oakland_is_nearby():
    distance = haversine_km(37.7749, -122.4194, 37.8044, -122.2712)
    assert 10 < distance < 20
