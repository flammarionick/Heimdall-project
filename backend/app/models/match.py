# backend/app/models/match.py
from datetime import datetime
from app.extensions import db


class Match(db.Model):
    __tablename__ = "match"

    id = db.Column(db.Integer, primary_key=True)
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Match {self.id} - Inmate {self.inmate_id}>'
