# app/models/facial_embedding.py
from app import db
from datetime import datetime

class FacialEmbedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    embedding = db.Column(db.PickleType, nullable=False)
    predicted_id = db.Column(db.Integer, nullable=False)
    camera_id = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'inmate_id': self.inmate_id,
            'image_name': self.image_name,
            'timestamp': self.timestamp.isoformat()
        }
