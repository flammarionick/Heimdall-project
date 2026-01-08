# backend/app/models/active_recognition.py
"""
ActiveRecognition model for tracking ongoing inmate detections.
Used for deduplication - prevents multiple alerts for same inmate
unless detected at different location or after 1 hour.
"""

from datetime import datetime
from app.extensions import db


class ActiveRecognition(db.Model):
    __tablename__ = "active_recognition"

    id = db.Column(db.Integer, primary_key=True)

    # Which inmate was detected
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'), nullable=False)

    # Where they were detected (camera reference)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=True)

    # GPS coordinates of detection location
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Timestamps for deduplication logic
    first_detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Reference to the original alert created
    alert_id = db.Column(db.Integer, db.ForeignKey('alert.id'), nullable=True)

    # Relationships
    inmate = db.relationship('Inmate', backref=db.backref('active_recognitions', lazy=True))
    camera = db.relationship('Camera', backref=db.backref('active_recognitions', lazy=True))
    alert = db.relationship('Alert', backref=db.backref('active_recognition', uselist=False))

    def __repr__(self):
        return f'<ActiveRecognition inmate={self.inmate_id} camera={self.camera_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'inmate_id': self.inmate_id,
            'camera_id': self.camera_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'first_detected_at': self.first_detected_at.isoformat() if self.first_detected_at else None,
            'last_detected_at': self.last_detected_at.isoformat() if self.last_detected_at else None,
            'alert_id': self.alert_id
        }
