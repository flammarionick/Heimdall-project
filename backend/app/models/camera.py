# models/camera.py
from app.extensions import db

class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    status = db.Column(db.Boolean, default=True)  # Active/Inactive

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    alerts = db.relationship('Alert', backref='camera', lazy=True)


    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'status': self.status
        }
