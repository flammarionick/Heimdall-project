# backend/app/models/recording.py
"""
Recording model for storing video surveillance footage metadata.
Recordings are stored on disk, this model tracks metadata for retrieval.
"""

from datetime import datetime
from app.extensions import db


class Recording(db.Model):
    __tablename__ = "recording"

    id = db.Column(db.Integer, primary_key=True)

    # Camera that recorded this footage
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=False)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # Relative path from static/recordings
    file_size = db.Column(db.BigInteger, nullable=True)  # Size in bytes
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    mime_type = db.Column(db.String(100), default='video/webm')

    # Time information
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    # Location at time of recording
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(200), nullable=True)  # Human-readable location

    # Recording status
    status = db.Column(db.String(50), default='recording')  # recording, completed, error, deleted

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # User who initiated the recording (optional)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    camera = db.relationship('Camera', backref=db.backref('recordings', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('recordings', lazy='dynamic'))

    def __repr__(self):
        return f'<Recording {self.id} camera={self.camera_id} {self.start_time}>'

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'duration': self.duration,
            'mime_type': self.mime_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id,
            # Include camera info if available
            'camera': {
                'id': self.camera.id,
                'name': self.camera.name,
                'location': self.camera.location
            } if self.camera else None
        }

    @property
    def stream_url(self):
        """URL to stream this recording."""
        return f"/api/recordings/{self.id}/stream"

    @property
    def is_complete(self):
        return self.status == 'completed'
