# app/models/__init__.py
"""
Export all models for easy importing.
Usage: from app.models import User, Inmate, Camera, Alert, Match, FacialEmbedding, ActiveRecognition, Recording
"""

from app.models.user import User
from app.models.inmate import Inmate
from app.models.camera import Camera
from app.models.alert import Alert
from app.models.match import Match
from app.models.facial_embedding import FacialEmbedding
from app.models.active_recognition import ActiveRecognition
from app.models.recording import Recording

__all__ = [
    "User",
    "Inmate",
    "Camera",
    "Alert",
    "Match",
    "FacialEmbedding",
    "ActiveRecognition",
    "Recording",
]
