# app/models/__init__.py
# Import model classes here so other modules can do `from app.models import Inmate, User, ...`
# IMPORTANT: Do NOT import `app` or attempt to register blueprints here.
# Keep this file side-effect free to avoid circular import issues.

from .inmate import Inmate
from .user import User
from .camera import Camera
from .alert import Alert
from .facial_embedding import FacialEmbedding
from .match import Match

__all__ = [
    "Inmate",
    "User",
    "Camera",
    "Alert",
    "FacialEmbedding",
    "Match",
]