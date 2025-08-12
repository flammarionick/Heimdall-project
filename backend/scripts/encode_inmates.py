# backend/scripts/encode_inmates.py
import base64
from pathlib import Path
import cv2
import requests
from sqlalchemy import or_
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
sys.path.append(str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

# Where your images were written by the seeder (used only as a fallback):
BACKUP_IMAGES_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "inmate_images"
EMBEDDING_URL = "http://127.0.0.1:5001/encode"   # embedding service must be running

def to_data_url(img_path: Path) -> str:
    img = cv2.imread(str(img_path))
    if img is None:
        raise RuntimeError(f"Could not read image: {img_path}")
    ok, buf = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError(f"Could not encode image: {img_path}")
    b64 = base64.b64encode(buf).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

def resolve_image_path(inmate: Inmate) -> Path | None:
    """
    Prefer inmate.mugshot_path (your schema).
    Fallback to image_filename if your DB ever had it.
    Try to make relative paths absolute if needed.
    """
    candidate_paths: list[Path] = []

    # Primary: mugshot_path (stored as a full or relative path)
    if hasattr(inmate, "mugshot_path") and inmate.mugshot_path:
        candidate_paths.append(Path(inmate.mugshot_path))

    # Fallback: image_filename (older schema)
    if hasattr(inmate, "image_filename") and getattr(inmate, "image_filename", None):
        candidate_paths.append(BACKUP_IMAGES_DIR / inmate.image_filename)

    # Try each candidate; repair relative paths if needed
    for p in candidate_paths:
        if p.is_file():
            return p
        # Sometimes mugshot_path is saved relative to backend root
        backend_root = Path(__file__).resolve().parents[1]
        alt = backend_root / p
        if alt.is_file():
            return alt

    return None

def main():
    app = create_app()
    with app.app_context():
        # Only encode those missing an embedding
        to_encode = (
            db.session.query(Inmate)
            .filter(or_(Inmate.face_encoding.is_(None), Inmate.face_encoding == ""))
            .all()
        )
        print(f"Encoding {len(to_encode)} inmates...")

        updated = 0
        for i, inmate in enumerate(to_encode, 1):
            try:
                img_path = resolve_image_path(inmate)
                if not img_path:
                    print(f"[{i}] Skip inmate id={inmate.id}: no readable image path.")
                    continue

                data_url = to_data_url(img_path)
                resp = requests.post(EMBEDDING_URL, json={"image": data_url}, timeout=40)
                resp.raise_for_status()
                embedding = resp.json().get("embedding")
                if not embedding:
                    print(f"[{i}] No embedding returned for inmate id={inmate.id}")
                    continue

                inmate.face_encoding = embedding
                updated += 1

                # Commit in batches
                if updated % 25 == 0:
                    db.session.commit()
                    print(f"Committed {updated} embeddings so far...")

            except requests.RequestException as e:
                print(f"[{i}] HTTP error for inmate id={inmate.id}: {e}")
            except Exception as e:
                print(f"[{i}] Failed for inmate id={inmate.id}: {e}")

        db.session.commit()
        print(f"Done. Updated {updated} inmate embeddings.")

if __name__ == "__main__":
    main()