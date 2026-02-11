#!/usr/bin/env python3
"""
Re-encode all inmates with noise augmentation.

This script regenerates face embeddings for all inmates using the updated
augmentation pipeline that includes noise and blur variations.

This fixes the critical weakness where the model fails on noisy images
(4.8% accuracy at sigma=30, breaks at sigma=10).

Usage:
    cd backend
    python scripts/reencode_with_noise.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
from datetime import datetime
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate
from app.utils.image_preprocessing import generate_augmentations

EMBEDDING_URL = "http://127.0.0.1:5001/encode"


def get_embedding(image_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', image_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    try:
        resp = requests.post(EMBEDDING_URL, files=files, timeout=30)
        if resp.status_code == 200:
            emb = resp.json().get('embedding')
            if emb:
                return np.array(emb)
    except Exception as e:
        print(f"    [WARN] Embedding failed: {e}")
    return None


def get_mugshot_path(inmate, static_folder):
    """Get full path to inmate's mugshot."""
    mugshot_path = inmate.mugshot_path
    if not mugshot_path:
        return None

    if mugshot_path.startswith('/static/'):
        full_path = os.path.join(static_folder, mugshot_path[8:])
    elif mugshot_path.startswith('static/'):
        full_path = os.path.join(static_folder, mugshot_path[7:])
    else:
        full_path = os.path.join(static_folder, mugshot_path)

    if os.path.exists(full_path):
        return full_path

    alt_paths = [
        os.path.join(static_folder, 'inmate_images', os.path.basename(mugshot_path)),
        os.path.join(static_folder, os.path.basename(mugshot_path)),
    ]
    for alt in alt_paths:
        if os.path.exists(alt):
            return alt

    return None


def main():
    print("=" * 70)
    print("RE-ENCODE INMATES WITH NOISE AUGMENTATION")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This will generate new embeddings including:")
    print("  - Original + rotations (4 angles)")
    print("  - Brightness variations (4 types)")
    print("  - Grayscale")
    print("  - Noise variations (sigma=10, 20, 30) <- NEW")
    print("  - Blur variations (kernel 5x5, 9x9) <- NEW")
    print("  - Combined rotation+noise <- NEW")
    print()
    print("Total augmentations per image: ~18")
    print("=" * 70)

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print("Embedding service: OK")
    except:
        print("ERROR: Embedding service not running on port 5001!")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        static_folder = os.path.join(app.root_path, 'static')

        # Get all inmates
        inmates = Inmate.query.all()
        print(f"Total inmates: {len(inmates)}")
        print("-" * 70)

        success_count = 0
        skip_count = 0
        fail_count = 0

        for idx, inmate in enumerate(inmates):
            mugshot_path = get_mugshot_path(inmate, static_folder)
            if not mugshot_path:
                print(f"[{idx+1:3}/{len(inmates)}] {inmate.inmate_id}: SKIP (no mugshot)")
                skip_count += 1
                continue

            image = cv2.imread(mugshot_path)
            if image is None:
                print(f"[{idx+1:3}/{len(inmates)}] {inmate.inmate_id}: SKIP (couldn't load image)")
                skip_count += 1
                continue

            # Generate augmentations with noise and blur
            augmentations = generate_augmentations(
                image,
                include_rotations=True,
                include_brightness=True,
                include_grayscale=True,
                include_noise=True,  # NEW: Add noise variations
                include_blur=True    # NEW: Add blur variations
            )

            print(f"[{idx+1:3}/{len(inmates)}] {inmate.inmate_id}: Generating {len(augmentations)} embeddings...", end=" ")

            # Get embeddings for all augmentations
            embeddings = []
            failed_augs = 0

            for aug_img, aug_name in augmentations:
                emb = get_embedding(aug_img)
                if emb is not None:
                    embeddings.append(emb)
                else:
                    failed_augs += 1

            if len(embeddings) == 0:
                print(f"FAILED (no embeddings generated)")
                fail_count += 1
                continue

            # Store embeddings
            inmate.set_multi_encodings(embeddings)

            # Also set the primary encoding (first successful one)
            inmate.face_encoding = embeddings[0]

            db.session.commit()

            print(f"OK ({len(embeddings)} embeddings, {failed_augs} failed)")
            success_count += 1

        # Summary
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Successfully re-encoded: {success_count}")
        print(f"Skipped (no image): {skip_count}")
        print(f"Failed: {fail_count}")
        print()
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("Next steps:")
        print("  1. Run evaluation_1000.py to verify improved accuracy")
        print("  2. Expected improvement on noise tests (sigma=30): 4.8% -> 80%+")


if __name__ == "__main__":
    main()
