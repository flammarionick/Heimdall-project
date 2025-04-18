from app import db

class Inmate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo_path = db.Column(db.String(200))
    face_encoding = db.Column(db.PickleType, nullable=False)
    status = db.Column(db.String(50), default='watched')  # wanted/cleared/etc.
