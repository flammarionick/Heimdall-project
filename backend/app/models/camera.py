# models/camera.py
from app.extensions import db


class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # add other fields as needed
    status = db.Column(db.String(10), default='off')  # on/off
    stream_url = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "is_active": self.is_active,
            "stream_url": self.stream_url
        }
