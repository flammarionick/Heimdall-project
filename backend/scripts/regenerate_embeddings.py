#!/usr/bin/env python3
"""
Regenerate all inmate face embeddings.

This script clears existing embeddings and regenerates them using the current
NumPy version, fixing pickle compatibility issues.

Usage:
    1. Start embedding service: python app/utils/embedding_service.py
    2. Run this script: python scripts/regenerate_embeddings.py
"""
import base64
import json
import sys
from pathlib import Path

import cv2
import requests

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
sys.path.append(str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EMBEDDING_URL = "http://127.0.0.1:5001/encode"
BACKUP_IMAGES_DIR = BASE_DIR / "app" / "static" / "inmate_images"


def to_data_url(img_path: Path) -> str:
    """Convert image file to data URL."""
    img = cv2.imread(str(img_path))
    if img is None:
        raise RuntimeError(f"Could not read image: {img_path}")
    ok, buf = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError(f"Could not encode image: {img_path}")
    b64 = base64.b64encode(buf).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def resolve_image_path(inmate: Inmate) -> Path | None:
    """Find the image file for an inmate."""
    candidate_paths = []

    if hasattr(inmate, "mugshot_path") and inmate.mugshot_path:
        candidate_paths.append(Path(inmate.mugshot_path))

    if hasattr(inmate, "image_filename") and getattr(inmate, "image_filename", None):
        candidate_paths.append(BACKUP_IMAGES_DIR / inmate.image_filename)

    for p in candidate_paths:
        if p.is_file():
            return p
        alt = BASE_DIR / p
        if alt.is_file():
            return alt

    return None


def find_all_images_for_inmate(inmate_id: str) -> list[Path]:
    """Find all image files for an inmate (for multi-embedding support)."""
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        images.extend(BACKUP_IMAGES_DIR.glob(f"{inmate_id}_*{ext[1:]}"))
        images.extend(BACKUP_IMAGES_DIR.glob(f"{inmate_id}{ext[1:]}"))
    return list(set(images))


def main():
    print("=" * 60)
    print("REGENERATE ALL INMATE EMBEDDINGS")
    print("=" * 60)

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if resp.status_code != 200:
            raise Exception("Bad status")
        print("[OK] Embedding service is running")
    except:
        print("[ERROR] Embedding service not running on port 5001!")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        inmates = db.session.query(Inmate).all()
        print(f"\nFound {len(inmates)} inmates to process")

        updated = 0
        failed = 0

        for i, inmate in enumerate(inmates, 1):
            try:
                # Find all images for this inmate
                all_images = find_all_images_for_inmate(inmate.inmate_id)

                # Also check mugshot_path
                primary_path = resolve_image_path(inmate)
                if primary_path and primary_path not in all_images:
                    all_images.insert(0, primary_path)

                if not all_images:
                    print(f"[{i}/{len(inmates)}] Skip {inmate.inmate_id}: no images found")
                    failed += 1
                    continue

                # Generate embeddings for all images
                embeddings = []
                for img_path in all_images:
                    try:
                        data_url = to_data_url(img_path)
                        resp = requests.post(EMBEDDING_URL, json={"image": data_url}, timeout=60)
                        resp.raise_for_status()
                        embedding = resp.json().get("embedding")
                        if embedding:
                            embeddings.append(embedding)
                    except Exception as e:
                        print(f"  Warning: Failed to encode {img_path.name}: {e}")

                if not embeddings:
                    print(f"[{i}/{len(inmates)}] Failed {inmate.inmate_id}: no valid embeddings")
                    failed += 1
                    continue

                # Store primary embedding
                inmate.face_encoding = embeddings[0]

                # Store all embeddings as JSON
                inmate.face_encodings_json = json.dumps(embeddings)

                updated += 1
                print(f"[{i}/{len(inmates)}] OK {inmate.inmate_id}: {len(embeddings)} embeddings")

                # Commit in batches
                if updated % 10 == 0:
                    db.session.commit()
                    print(f"  Committed {updated} inmates...")

            except Exception as e:
                print(f"[{i}/{len(inmates)}] Error {inmate.inmate_id}: {e}")
                failed += 1

        db.session.commit()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total inmates: {len(inmates)}")
        print(f"Updated:       {updated}")
        print(f"Failed:        {failed}")
        print("=" * 60)

        if updated > 0:
            print("\nEmbeddings regenerated successfully!")
            print("You can now run the performance tests.")
        else:
            print("\nNo embeddings were updated. Check for errors above.")


if __name__ == "__main__":
    main()
