# app/models/facial_embedding.py
from datetime import datetime
from app.extensions import db

class FacialEmbedding(db.Model):
    __tablename__ = "facial_embedding"

    id = db.Column(db.Integer, primary_key=True)

    # Store embedding (512-d FaceNet or padded to 3060-d for XGBoost)
    embedding = db.Column(db.PickleType, nullable=False)

    # Link to predicted inmate (if available)
    predicted_id = db.Column(db.Integer, index=True, nullable=True)

    # Optional: link back to actual inmate record if known/confirmed
    inmate_id = db.Column(db.Integer, db.ForeignKey("inmate.id"), nullable=True)

    # Store filename if the recognition came from an uploaded image
    image_name = db.Column(db.String(255), nullable=True)

    # Where the camera was located (optional, for live recognition context)
    camera_id = db.Column(db.String(100), nullable=True)

    # When the embedding was generated
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships (optional)
    inmate = db.relationship("Inmate", backref="embeddings", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "predicted_id": self.predicted_id,
            "inmate_id": self.inmate_id,
            "image_name": self.image_name,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }