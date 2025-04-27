# models/inmate.py
from app.extensions import db
from datetime import datetime, timedelta

class Inmate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mugshot_path = db.Column(db.String(300), nullable=False)
    sentence_start = db.Column(db.DateTime, default=datetime.utcnow)
    sentence_duration_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Incarcerated')  # or 'Released'

    alerts = db.relationship('Alert', backref='inmate', lazy=True)

    def expected_release_date(self):
        return self.sentence_start + timedelta(days=self.sentence_duration_days)

