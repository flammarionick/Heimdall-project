# models/camera.py
from app import db

class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(256))
    status = db.Column(db.Boolean, default=True)  # True = Active, False = Inactive

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'status': self.status
        }
