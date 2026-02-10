# backend/scripts/seed_lfw_inmates.py
import os
import random
import uuid
from pathlib import Path

from PIL import Image
import numpy as np
from sklearn.datasets import fetch_lfw_people

# --- Flask app bootstrap so we can use models/db ---
import sys
BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
sys.path.append(str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate  # adjust if your import path differs

def build_inmate_kwargs(person_name, prison_id, main_filename):
    """
    Adapt to your current Inmate model by only setting fields that exist.
    Common mappings handled automatically.
    """
    cols = set(Inmate.__table__.columns.keys())

    candidates = {
        "full_name": person_name,                         # newer schema
        "name": person_name,                              # fallback if your column is 'name'
        "prison_id": prison_id,                           # common id/reference field
        "image_filename": main_filename,                  # single image filename
        "mugshot_path": f"app/static/inmate_images/{main_filename}",  # older schema
        "duration_months": random.randint(6, 48),         # newer schema idea
        "sentence_duration_days": random.randint(6, 48) * 30,  # older schema
        "status": "in_custody",
        "face_encoding": None,                            # will be filled later by embedding pipeline
    }

    return {k: v for k, v in candidates.items() if k in cols}

# --------- CONFIG ----------
APP = create_app()
IMAGES_DIR = BASE_DIR / "app" / "static" / "inmate_images"  # served by Flask
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

NUM_IDENTITIES = 100            # how many distinct people to import
MIN_IMAGES_PER_ID = 1           # save at least 1 image per identity
MAX_IMAGES_PER_ID = 3           # up to N per identity
# ---------------------------

def name_to_prison_id(name: str) -> str:
    # Simple stable-ish ID: initials + random 6 chars
    parts = [p for p in name.split() if p]
    initials = "".join([p[0].upper() for p in parts])[:3]
    return f"{initials}-{uuid.uuid4().hex[:6].upper()}"

def save_pil(img_array: np.ndarray, path: Path):
    """
    LFW returns grayscale float arrays 0..1 (H,W). Convert to RGB JPEG for consistency.
    """
    if img_array.ndim == 2:
        # Convert grayscale -> RGB
        img = Image.fromarray((img_array * 255).astype("uint8"), mode="L").convert("RGB")
    else:
        img = Image.fromarray((img_array * 255).astype("uint8"))
    img.save(path, format="JPEG", quality=92)

def main():
    with APP.app_context():
        print("Downloading LFW (this may take a minute on first run)...")
        # grayscale, resized; includes person names in target_names
        lfw = fetch_lfw_people(min_faces_per_person=2, resize=0.5, color=False)
        images = lfw.images          # shape (N, H, W), floats 0..1
        labels = lfw.target          # ints
        names = lfw.target_names     # unique person names

        # Build mapping name -> indices
        idx_by_name = {}
        for idx, lab in enumerate(labels):
            name = names[lab]
            idx_by_name.setdefault(name, []).append(idx)

        # Keep identities that have at least 2 images (gives us some choice)
        eligible = [(name, idxs) for name, idxs in idx_by_name.items() if len(idxs) >= 2]
        if len(eligible) < NUM_IDENTITIES:
            print(f"Only {len(eligible)} identities have >=2 images; reducing to that.")
        sample_identities = random.sample(eligible, k=min(NUM_IDENTITIES, len(eligible)))

        # (Optional) Show what columns your Inmate model has
        print("Inmate columns:", list(Inmate.__table__.columns.keys()))

        created = 0
        for person_name, idxs in sample_identities:
            per_person = random.randint(MIN_IMAGES_PER_ID, min(MAX_IMAGES_PER_ID, len(idxs)))
            chosen = random.sample(idxs, per_person)

            prison_id = name_to_prison_id(person_name)
            main_filename = None

            # Save 1..3 images
            for i, img_idx in enumerate(chosen):
                img = images[img_idx]  # (H, W) floats
                filename = f"{prison_id}_{i+1}.jpg"
                out_path = IMAGES_DIR / filename
                save_pil(img, out_path)
                if main_filename is None:
                    main_filename = filename

            # Build kwargs that match your model
            kwargs = build_inmate_kwargs(person_name, prison_id, main_filename)
            if not kwargs:
                raise RuntimeError(
                    "Could not map any fields to your Inmate model. "
                    "Print the columns and adjust build_inmate_kwargs()."
                )

            inmate = Inmate(**kwargs)
            db.session.add(inmate)
            created += 1

        db.session.commit()
        print(f"Inserted {created} inmates.")
        print(f"Images saved under: {IMAGES_DIR}")

if __name__ == "__main__":
    main()