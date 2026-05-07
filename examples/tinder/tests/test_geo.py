from app.geo import haversine_km
from app.main import gender_matches


def test_haversine_distance_for_nearby_profiles():
    assert haversine_km(37.7749, -122.4194, 37.7755, -122.4189) < 0.1


def test_gender_preferences():
    assert gender_matches("both", "female")
    assert gender_matches("any", "nonbinary")
    assert gender_matches("male", "male")
    assert not gender_matches("female", "male")
