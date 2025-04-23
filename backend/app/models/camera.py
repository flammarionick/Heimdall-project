# models/camera.py
from app.extensions import db


class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # add other fields as needed

    stream_url = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
