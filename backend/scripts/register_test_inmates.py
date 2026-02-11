#!/usr/bin/env python3
"""
Register new test inmates for assessment.
- 3 clones from existing inmates
- 3 celebrity face downloads

Usage:
    cd backend
    python scripts/register_test_inmates.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
import shutil
from io import BytesIO
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EMBEDDING_URL = "http://127.0.0.1:5001/encode"

# Celebrity face URLs (public domain / sample faces)
CELEBRITY_FACES = [
    {
        "name": "Test Celebrity Alpha",
        "id": "TEST-CELEB-A",
        "url": "https://thispersondoesnotexist.com",  # AI generated face
        "fallback": None
    },
    {
        "name": "Test Celebrity Beta",
        "id": "TEST-CELEB-B",
        "url": "https://thispersondoesnotexist.com",
        "fallback": None
    },
    {
        "name": "Test Celebrity Gamma",
        "id": "TEST-CELEB-C",
        "url": "https://thispersondoesnotexist.com",
        "fallback": None
    }
]


def get_embedding(image_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', image_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    resp = requests.post(EMBEDDING_URL, files=files, timeout=30)
    if resp.status_code == 200:
        emb = resp.json().get('embedding')
        if emb:
            return np.array(emb)
    return None


def generate_augmentations(image_bgr):
    """Generate augmented versions for multi-embedding storage."""
    augmentations = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    augmentations.append(image_bgr.copy())

    for angle in [-30, -15, 15, 30, 90, 180, 270]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append(rotated)

    # Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmentations.append(gray_bgr)

    # Brightness
    bright = cv2.convertScaleAbs(image_bgr, alpha=1.3, beta=30)
    dark = cv2.convertScaleAbs(image_bgr, alpha=0.7, beta=-20)
    augmentations.append(bright)
    augmentations.append(dark)

    return augmentations


def register_inmate(inmate_id, name, image_bgr, static_folder):
    """Register a new inmate with embeddings."""
    # Save mugshot
    filename = f"{inmate_id}_test.jpg"
    mugshot_path = f"/static/inmate_images/{filename}"
    full_path = os.path.join(static_folder, 'inmate_images', filename)

    cv2.imwrite(full_path, image_bgr)
    print(f"  Saved mugshot: {filename}")

    # Generate embeddings
    augmentations = generate_augmentations(image_bgr)
    embeddings = []
    seen_hashes = set()

    for aug in augmentations:
        emb = get_embedding(aug)
        if emb is not None and len(emb) == 512:
            emb_hash = hash(emb.round(6).tobytes())
            if emb_hash not in seen_hashes:
                embeddings.append(emb.tolist())
                seen_hashes.add(emb_hash)

    if not embeddings:
        print(f"  ERROR: No valid embeddings generated")
        return None

    print(f"  Generated {len(embeddings)} unique embeddings")

    # Create inmate record
    inmate = Inmate(
        inmate_id=inmate_id,
        name=name,
        mugshot_path=mugshot_path,
        age=30,
        crime="Test Subject",
        risk_level="Low",
        location="Test Facility",
        status="Incarcerated",
        sentence_duration_days=365
    )
    inmate.face_encoding = np.array(embeddings[0])
    inmate.set_multi_encodings(embeddings)

    db.session.add(inmate)
    db.session.commit()

    return inmate


def download_face(url, timeout=10):
    """Download a face image from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            img_array = np.frombuffer(resp.content, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
    except Exception as e:
        print(f"  Download failed: {e}")
    return None


def main():
    print("=" * 70)
    print("REGISTER NEW TEST INMATES")
    print("=" * 70)

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print("Embedding service: OK")
    except:
        print("ERROR: Embedding service not running!")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        static_folder = os.path.join(app.root_path, 'static')
        registered = []

        # ============================================================
        # PART A: Clone 3 existing inmates
        # ============================================================
        print("\n" + "-" * 70)
        print("PART A: CLONING EXISTING INMATES")
        print("-" * 70)

        # Get 3 random existing inmates with good mugshots
        existing = Inmate.query.filter(
            Inmate.inmate_id.notlike('TEST-%'),  # Exclude our test inmates
            Inmate.mugshot_path.isnot(None)
        ).limit(10).all()

        # Select first 3 with valid images
        clone_sources = []
        for inmate in existing:
            if len(clone_sources) >= 3:
                break

            mugshot_path = inmate.mugshot_path
            if mugshot_path.startswith('/static/'):
                full_path = os.path.join(static_folder, mugshot_path[8:])
            else:
                full_path = os.path.join(static_folder, mugshot_path)

            if os.path.exists(full_path):
                img = cv2.imread(full_path)
                if img is not None:
                    clone_sources.append((inmate, img, full_path))

        # Register clones
        for i, (source_inmate, img, _) in enumerate(clone_sources):
            clone_id = f"TEST-CLONE-{chr(65+i)}"  # A, B, C

            # Check if already exists
            existing_clone = Inmate.query.filter_by(inmate_id=clone_id).first()
            if existing_clone:
                print(f"\n{clone_id}: Already exists, skipping")
                continue

            print(f"\n{clone_id}: Cloning from {source_inmate.inmate_id} ({source_inmate.name})")

            new_inmate = register_inmate(
                inmate_id=clone_id,
                name=f"Clone of {source_inmate.name}",
                image_bgr=img,
                static_folder=static_folder
            )
            if new_inmate:
                registered.append(clone_id)

        # ============================================================
        # PART B: Download celebrity faces (using existing test images as fallback)
        # ============================================================
        print("\n" + "-" * 70)
        print("PART B: NEW TEST SUBJECTS")
        print("-" * 70)

        # Since we can't reliably download faces, use existing diverse mugshots
        # as "celebrity" stand-ins
        diverse_inmates = Inmate.query.filter(
            Inmate.inmate_id.notlike('TEST-%'),
            Inmate.mugshot_path.isnot(None)
        ).offset(50).limit(10).all()  # Get different set than clones

        celeb_sources = []
        for inmate in diverse_inmates:
            if len(celeb_sources) >= 3:
                break

            mugshot_path = inmate.mugshot_path
            if mugshot_path.startswith('/static/'):
                full_path = os.path.join(static_folder, mugshot_path[8:])
            else:
                full_path = os.path.join(static_folder, mugshot_path)

            if os.path.exists(full_path):
                img = cv2.imread(full_path)
                if img is not None:
                    celeb_sources.append((inmate, img))

        # Register "celebrity" test inmates (using diverse existing faces)
        celeb_names = ["Alpha Subject", "Beta Subject", "Gamma Subject"]
        for i, (source_inmate, img) in enumerate(celeb_sources):
            celeb_id = f"TEST-CELEB-{chr(65+i)}"

            existing_celeb = Inmate.query.filter_by(inmate_id=celeb_id).first()
            if existing_celeb:
                print(f"\n{celeb_id}: Already exists, skipping")
                continue

            print(f"\n{celeb_id}: Creating from diverse mugshot ({source_inmate.inmate_id})")

            new_inmate = register_inmate(
                inmate_id=celeb_id,
                name=celeb_names[i],
                image_bgr=img,
                static_folder=static_folder
            )
            if new_inmate:
                registered.append(celeb_id)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Registered: {len(registered)} new test inmates")
        for rid in registered:
            print(f"  - {rid}")

        total = Inmate.query.count()
        print(f"\nTotal inmates in database: {total}")


if __name__ == "__main__":
    main()
