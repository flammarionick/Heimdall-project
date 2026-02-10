# models/inmate.py
from app.extensions import db
from datetime import datetime, timedelta
import json
import numpy as np


class Inmate(db.Model):
    __tablename__ = "inmate"

    id = db.Column(db.Integer, primary_key=True)
    inmate_id = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "CDJ-713551"
    name = db.Column(db.String(150), nullable=False)
    mugshot_path = db.Column(db.String(300), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    crime = db.Column(db.String(200), nullable=True)
    risk_level = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    location = db.Column(db.String(200), nullable=True)
    sentence_start = db.Column(db.DateTime, default=datetime.utcnow)
    sentence_duration_days = db.Column(db.Integer, default=365)
    status = db.Column(db.String(50), default='Incarcerated')  # Incarcerated, Released, Escaped
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    face_encoding = db.Column(db.PickleType, nullable=True)  # Single embedding (legacy)
    face_encodings_json = db.Column(db.Text, nullable=True)  # Multiple embeddings as JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Track who registered this inmate
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    registrant = db.relationship('User', backref='registered_inmates', foreign_keys=[registered_by])

    # Escape tracking fields
    escape_latitude = db.Column(db.Float, nullable=True)
    escape_longitude = db.Column(db.Float, nullable=True)
    escape_date = db.Column(db.DateTime, nullable=True)

    alerts = db.relationship('Alert', backref='inmate', lazy=True)

    def expected_release_date(self):
        return self.sentence_start + timedelta(days=self.sentence_duration_days)

    def to_dict(self):
        return {
            'id': self.inmate_id,
            'db_id': self.id,
            'name': self.name,
            'age': self.age,
            'status': self.status,
            'location': self.location,
            'crime': self.crime,
            'riskLevel': self.risk_level,
            'lastSeen': self.last_seen.strftime('%B %d, %Y') if self.last_seen else 'Unknown',
            'mugshot': self.mugshot_path,
            'sentenceStart': self.sentence_start.isoformat() if self.sentence_start else None,
            'sentenceDays': self.sentence_duration_days,
            'expectedRelease': self.expected_release_date().strftime('%B %d, %Y') if self.sentence_start else None,
            'registeredBy': self.registered_by,
            'registrantEmail': self.registrant.email if self.registrant else None,
            'registrantName': self.registrant.email.split('@')[0] if self.registrant else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'escapeLatitude': self.escape_latitude,
            'escapeLongitude': self.escape_longitude,
            'escapeDate': self.escape_date.isoformat() if self.escape_date else None,
        }

    def get_all_encodings(self):
        """
        Get all face encodings for this inmate.
        Returns list of numpy arrays (includes both legacy and multi-embeddings).
        """
        encodings = []

        # Add legacy single encoding if exists
        if self.face_encoding is not None:
            if isinstance(self.face_encoding, np.ndarray):
                encodings.append(self.face_encoding)
            elif isinstance(self.face_encoding, list):
                encodings.append(np.array(self.face_encoding))

        # Add multi-embeddings if exists
        if self.face_encodings_json:
            try:
                multi_encodings = json.loads(self.face_encodings_json)
                for enc in multi_encodings:
                    if enc is not None:
                        encodings.append(np.array(enc))
            except (json.JSONDecodeError, TypeError):
                pass

        return encodings

    def set_multi_encodings(self, encodings_list):
        """
        Set multiple face encodings for robust matching.
        Args:
            encodings_list: List of numpy arrays or lists (512-dim embeddings)
        """
        # Convert numpy arrays to lists for JSON serialization
        json_encodings = []
        for enc in encodings_list:
            if enc is not None:
                if isinstance(enc, np.ndarray):
                    json_encodings.append(enc.tolist())
                else:
                    json_encodings.append(enc)
        self.face_encodings_json = json.dumps(json_encodings)

    def has_encodings(self):
        """Check if inmate has any face encodings."""
        return self.face_encoding is not None or self.face_encodings_json is not None

