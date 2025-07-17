# app/models/facial_embedding.py
from app import db

class FacialEmbedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inmate_id = db.Column(db.Integer, db.ForeignKey('inmate.id'), nullable=False)
    embedding = db.Column(db.PickleType, nullable=False)
    image_name = db.Column(db.String(120))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'inmate_id': self.inmate_id,
            'image_name': self.image_name,
            'timestamp': self.timestamp.isoformat()
        }
