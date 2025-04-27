# app/models/alert.py
from app.extensions import db
from datetime import datetime

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500))
    level = db.Column(db.String(50))  # info, warning, danger
    resolved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


    def __repr__(self):
        return f"<Alert {self.level.upper()}: {self.message}>"
