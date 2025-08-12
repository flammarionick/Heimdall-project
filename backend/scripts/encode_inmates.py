# backend/scripts/encode_inmates.py
import os, io, base64, requests
from pathlib import Path
from PIL import Image

import sys
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EMBED_URL = os.getenv("EMBEDDING_URL", "http://127.0.0.1:5001/encode")
IMAGES_DIR = BASE_DIR / "app" / "static" / "inmate_images"

APP = create_app()

def img_to_data_url(p: Path) -> str:
    with Image.open(p).convert("RGB") as im:
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

with APP.app_context():
    inmates = Inmate.query.filter(Inmate.face_encoding.is_(None)).all()
    print(f"Encoding {len(inmates)} inmates...")
    for inmate in inmates:
        img_path = IMAGES_DIR / inmate.image_filename
        if not img_path.exists():
            print("Missing image:", img_path)
            continue
        data_url = img_to_data_url(img_path)
        try:
            r = requests.post(EMBED_URL, json={"image": data_url}, timeout=40)
            r.raise_for_status()
            emb = r.json().get("embedding")
            if emb:
                inmate.face_encoding = emb  # SQLAlchemy JSON/ARRAY column recommended
                db.session.add(inmate)
        except Exception as e:
            print("Embed error for", inmate.prison_id, e)
    db.session.commit()
    print("Done.")