from app.geo import haversine_km


def test_haversine_distance_is_reasonable_for_sf_to_oakland():
    distance = haversine_km(37.7749, -122.4194, 37.8044, -122.2712)
    assert 12 <= distance <= 15
