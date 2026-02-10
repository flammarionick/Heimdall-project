#!/usr/bin/env python3
"""
Clear existing embeddings and regenerate with current NumPy version.

This bypasses SQLAlchemy's pickle deserialization issue by using raw SQL.
"""
import base64
import json
import sqlite3
import sys
from pathlib import Path

import cv2
import requests

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
DB_PATH = BASE_DIR / "instance" / "heimdall.db"
EMBEDDING_URL = "http://127.0.0.1:5001/encode"
IMAGES_DIR = BASE_DIR / "app" / "static" / "inmate_images"


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


def find_images_for_inmate(inmate_id: str, mugshot_path: str = None) -> list[Path]:
    """Find all image files for an inmate."""
    images = []

    # Check mugshot_path first
    if mugshot_path:
        p = Path(mugshot_path)
        if p.is_file():
            images.append(p)
        else:
            alt = BASE_DIR / p
            if alt.is_file():
                images.append(alt)

    # Find additional images by inmate_id pattern
    for img_file in IMAGES_DIR.glob(f"{inmate_id}*"):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png'] and img_file not in images:
            images.append(img_file)

    return images


def main():
    print("=" * 60)
    print("CLEAR AND REGENERATE EMBEDDINGS")
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

    # Check database exists
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    print(f"[OK] Database: {DB_PATH}")

    # Connect directly to SQLite
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Step 1: Clear existing embeddings (avoids pickle issues)
    print("\nStep 1: Clearing existing embeddings...")
    cursor.execute("UPDATE inmate SET face_encoding = NULL, face_encodings_json = NULL")
    conn.commit()
    print(f"  Cleared embeddings for all inmates")

    # Step 2: Get all inmates (without loading pickle data)
    cursor.execute("SELECT id, inmate_id, name, mugshot_path FROM inmate")
    inmates = cursor.fetchall()
    print(f"\nStep 2: Found {len(inmates)} inmates to process")

    # Step 3: Regenerate embeddings
    print("\nStep 3: Generating new embeddings...")
    updated = 0
    failed = 0

    for i, (db_id, inmate_id, name, mugshot_path) in enumerate(inmates, 1):
        try:
            images = find_images_for_inmate(inmate_id, mugshot_path)

            if not images:
                print(f"[{i}/{len(inmates)}] Skip {inmate_id}: no images")
                failed += 1
                continue

            # Generate embeddings for all images
            embeddings = []
            for img_path in images:
                try:
                    data_url = to_data_url(img_path)
                    resp = requests.post(EMBEDDING_URL, json={"image": data_url}, timeout=60)
                    resp.raise_for_status()
                    embedding = resp.json().get("embedding")
                    if embedding:
                        embeddings.append(embedding)
                except Exception as e:
                    print(f"  Warning: {img_path.name}: {e}")

            if not embeddings:
                print(f"[{i}/{len(inmates)}] Failed {inmate_id}: no valid embeddings")
                failed += 1
                continue

            # Convert to pickle bytes for face_encoding (primary)
            import pickle
            import numpy as np
            primary_embedding = pickle.dumps(np.array(embeddings[0], dtype=np.float32))

            # Store as JSON for face_encodings_json (multi-embedding)
            embeddings_json = json.dumps(embeddings)

            # Update database
            cursor.execute(
                "UPDATE inmate SET face_encoding = ?, face_encodings_json = ? WHERE id = ?",
                (primary_embedding, embeddings_json, db_id)
            )

            updated += 1
            print(f"[{i}/{len(inmates)}] OK {inmate_id}: {len(embeddings)} embeddings")

            # Commit in batches
            if updated % 10 == 0:
                conn.commit()
                print(f"  Committed {updated}...")

        except Exception as e:
            print(f"[{i}/{len(inmates)}] Error {inmate_id}: {e}")
            failed += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total inmates: {len(inmates)}")
    print(f"Updated:       {updated}")
    print(f"Failed:        {failed}")
    print("=" * 60)

    if updated > 0:
        print("\nEmbeddings regenerated successfully!")
        print("You can now restart the backend and run tests.")
    else:
        print("\nNo embeddings were updated. Check for errors above.")


if __name__ == "__main__":
    main()
