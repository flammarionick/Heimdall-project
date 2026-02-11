"""
One-time script to regenerate all inmate face embeddings using FaceNet.
IMPORTANT: Requires the embedding service to be running on port 5001.

Usage:
  1. Start embedding service: python -m app.utils.embedding_service
  2. Run this script: python regenerate_embeddings.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate
from app.utils.embedding_client import extract_embedding_from_frame
import cv2

def regenerate_all_embeddings():
    """Regenerate FaceNet embeddings for all inmates with mugshots."""
    app = create_app()

    with app.app_context():
        inmates = Inmate.query.all()
        print(f"Found {len(inmates)} inmates to process")

        success_count = 0
        fail_count = 0

        for inmate in inmates:
            if not inmate.mugshot_path:
                print(f"  [{inmate.inmate_id}] Skipped - no mugshot")
                continue

            # Build full path to mugshot
            mugshot_file = os.path.join('app', inmate.mugshot_path.lstrip('/'))

            if not os.path.exists(mugshot_file):
                print(f"  [{inmate.inmate_id}] Skipped - file not found: {mugshot_file}")
                fail_count += 1
                continue

            # Load image
            img = cv2.imread(mugshot_file)
            if img is None:
                print(f"  [{inmate.inmate_id}] Failed - could not read image")
                fail_count += 1
                continue

            # Get FaceNet embedding from service
            embedding = extract_embedding_from_frame(img)

            if embedding is None:
                print(f"  [{inmate.inmate_id}] Failed - embedding service error (is it running?)")
                fail_count += 1
                continue

            # Update inmate record - use session.query().update() to avoid comparison issues
            try:
                Inmate.query.filter_by(id=inmate.id).update(
                    {"face_encoding": embedding},
                    synchronize_session=False
                )
                db.session.commit()
                print(f"  [{inmate.inmate_id}] Success - {len(embedding)} FaceNet features")
                success_count += 1
            except Exception as e:
                print(f"  [{inmate.inmate_id}] DB Error: {e}")
                db.session.rollback()
                fail_count += 1
                continue

        print(f"\n=== Summary ===")
        print(f"Successfully updated: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"Total processed: {len(inmates)}")

if __name__ == "__main__":
    print("Regenerating FaceNet embeddings for all inmates...")
    print("Make sure embedding service is running on port 5001!\n")
    regenerate_all_embeddings()
