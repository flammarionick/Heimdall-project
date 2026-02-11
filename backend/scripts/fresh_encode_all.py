#!/usr/bin/env python3
"""
Fresh re-encode ALL inmates from their actual mugshots.
Clears existing embeddings and re-generates from scratch.

Usage:
    cd backend
    python scripts/fresh_encode_all.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EMBEDDING_URL = "http://127.0.0.1:5001/encode"


def get_embedding(image_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', image_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    resp = requests.post(EMBEDDING_URL, files=files, timeout=30)
    if resp.status_code == 200:
        return resp.json().get('embedding')
    return None


def validate_embedding(emb):
    """Validate embedding is correct."""
    if emb is None:
        return False
    arr = np.array(emb)
    if len(arr) != 512:
        return False
    if np.isnan(arr).any() or np.isinf(arr).any():
        return False
    return True


def generate_augmentations(image_bgr):
    """Generate unique augmented versions."""
    augmentations = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    # Original
    augmentations.append(('original', image_bgr.copy()))

    # Rotations
    for angle in [-30, -15, 15, 30, 90, 180, 270]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append((f'rotate_{angle}', rotated))

    # Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmentations.append(('grayscale', gray_bgr))

    # Brightness
    bright = cv2.convertScaleAbs(image_bgr, alpha=1.3, beta=30)
    dark = cv2.convertScaleAbs(image_bgr, alpha=0.7, beta=-20)
    augmentations.append(('bright', bright))
    augmentations.append(('dark', dark))

    return augmentations


def get_mugshot_path(inmate, static_folder):
    """Get full path to inmate's mugshot."""
    mugshot_path = inmate.mugshot_path
    if not mugshot_path:
        return None

    # Handle different path formats
    if mugshot_path.startswith('/static/'):
        full_path = os.path.join(static_folder, mugshot_path[8:])
    elif mugshot_path.startswith('static/'):
        full_path = os.path.join(static_folder, mugshot_path[7:])
    else:
        full_path = os.path.join(static_folder, mugshot_path)

    if os.path.exists(full_path):
        return full_path

    # Try alternative paths
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
    print("FRESH RE-ENCODE ALL INMATES")
    print("=" * 70)

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print(f"Embedding service: OK ({resp.json()})")
    except:
        print("ERROR: Embedding service not running!")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        static_folder = os.path.join(app.root_path, 'static')
        inmates = Inmate.query.all()

        print(f"\nTotal inmates: {len(inmates)}")
        print("=" * 70)

        success = 0
        failed = 0

        for i, inmate in enumerate(inmates):
            print(f"\n[{i+1}/{len(inmates)}] {inmate.inmate_id} ({inmate.name})")

            # Get mugshot path
            mugshot_path = get_mugshot_path(inmate, static_folder)
            if not mugshot_path:
                print(f"  ERROR: Mugshot not found: {inmate.mugshot_path}")
                failed += 1
                continue

            print(f"  Mugshot: {os.path.basename(mugshot_path)}")

            # Load image
            image = cv2.imread(mugshot_path)
            if image is None:
                print(f"  ERROR: Could not load image")
                failed += 1
                continue

            # Generate augmentations
            augmentations = generate_augmentations(image)

            # Encode and deduplicate
            embeddings = []
            seen_hashes = set()

            for aug_name, aug_img in augmentations:
                emb = get_embedding(aug_img)

                if not validate_embedding(emb):
                    print(f"    INVALID: {aug_name}")
                    continue

                # Check duplicate
                emb_arr = np.array(emb)
                emb_hash = hash(emb_arr.round(6).tobytes())

                if emb_hash in seen_hashes:
                    continue  # Skip duplicate silently

                embeddings.append(emb)
                seen_hashes.add(emb_hash)

            if not embeddings:
                print(f"  ERROR: No valid embeddings generated")
                failed += 1
                continue

            # Clear old and save new
            inmate.face_encoding = np.array(embeddings[0])
            inmate.set_multi_encodings(embeddings)
            db.session.commit()

            print(f"  Saved {len(embeddings)} unique embeddings")
            success += 1

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total: {len(inmates)}")
        print(f"Success: {success}")
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
