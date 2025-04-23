# app/models/alert.py
from app import db
from datetime import datetime

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(50), default='info')  # info, warning, critical
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'))  # Make sure the inmate table is defined
    inmate = db.relationship('Inmate', backref='alerts')

    def __repr__(self):
        return f"<Alert {self.level.upper()}: {self.message}>"
