# app/utils/geolocation.py
"""
Geolocation utilities for distance calculation and finding nearby facilities.
Used for escaped inmate alarm system to alert nearby facilities.
"""

from math import radians, sin, cos, sqrt, atan2


def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lng1: Latitude and longitude of point 1 (in degrees)
        lat2, lng2: Latitude and longitude of point 2 (in degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    # Convert to radians
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)

    # Haversine formula
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def find_nearby_facilities(lat, lng, radius_km=50):
    """
    Find all users/facilities within a given radius of a point.

    Args:
        lat: Detection latitude
        lng: Detection longitude
        radius_km: Search radius in kilometers (default 50km)

    Returns:
        List of User objects within the radius
    """
    from app.models.user import User

    # Get all users with location data
    users = User.query.filter(
        User.latitude.isnot(None),
        User.longitude.isnot(None)
    ).all()

    nearby = []
    for user in users:
        dist = haversine_distance(lat, lng, user.latitude, user.longitude)
        if dist <= radius_km:
            nearby.append({
                'user': user,
                'distance_km': round(dist, 2)
            })

    # Sort by distance (closest first)
    nearby.sort(key=lambda x: x['distance_km'])

    return nearby


def get_detection_location(camera_id=None, default_lat=None, default_lng=None):
    """
    Get the location where a detection occurred.

    Priority:
    1. Camera's coordinates (if camera_id provided and has coordinates)
    2. Default coordinates (if provided)
    3. None (location unknown)

    Args:
        camera_id: ID of the camera that made the detection
        default_lat: Fallback latitude
        default_lng: Fallback longitude

    Returns:
        Tuple of (latitude, longitude) or (None, None)
    """
    if camera_id:
        from app.models.camera import Camera
        camera = Camera.query.get(camera_id)
        if camera and camera.latitude and camera.longitude:
            return camera.latitude, camera.longitude

    if default_lat is not None and default_lng is not None:
        return default_lat, default_lng

    return None, None
