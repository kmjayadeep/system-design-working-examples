from math import atan2, cos, radians, sin, sqrt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))


def route_distance_km(points: list[dict]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for previous, current in zip(points, points[1:], strict=False):
        total += haversine_km(previous["latitude"], previous["longitude"], current["latitude"], current["longitude"])
    return total
