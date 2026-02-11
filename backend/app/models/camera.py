# models/camera.py
from app.extensions import db


class Camera(db.Model):
    __tablename__ = "camera"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    status = db.Column(db.Boolean, default=True)  # Active/Inactive

    # Camera type: 'webcam', 'rtsp', 'usb'
    camera_type = db.Column(db.String(50), default='webcam')
    # RTSP stream URL (e.g., rtsp://ip:port/stream)
    stream_url = db.Column(db.String(500), nullable=True)
    # USB device ID for selecting specific camera
    device_id = db.Column(db.String(100), nullable=True)

    # GPS coordinates for geographic alerting
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    alerts = db.relationship('Alert', backref='camera', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'status': self.status,
            'camera_type': self.camera_type,
            'stream_url': self.stream_url,
            'device_id': self.device_id,
            'latitude': self.latitude,
            'longitude': self.longitude
        }
