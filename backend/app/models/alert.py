from app import db
from datetime import datetime

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    confidence = db.Column(db.Float)
