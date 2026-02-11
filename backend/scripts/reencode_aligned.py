#!/usr/bin/env python3
"""
Re-encode all inmates with ALIGNED ArcFace embeddings for better accuracy.

This script:
1. Uses face alignment before encoding (critical for ArcFace)
2. Generates multiple augmented embeddings per inmate
3. Stores periocular embeddings for glasses/occlusion handling
"""
import os
import sys
import json
import cv2
import numpy as np
import requests
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models.inmate import Inmate
from app.extensions import db

# Embedding service URL
EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001"

def encode_with_alignment(image_path):
    """
    Encode a face image using aligned ArcFace embeddings.
    Returns (face_embedding, periocular_embedding, glasses_detected)
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, None, False

    # Encode to base64
    _, buffer = cv2.imencode('.jpg', img)
    import base64
    b64 = base64.b64encode(buffer).decode('ascii')

    # Get aligned face embedding
    try:
        resp = requests.post(
            f"{EMBEDDING_SERVICE_URL}/encode?align=true",
            json={"image": f"data:image/jpeg;base64,{b64}"},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            face_emb = data.get('embedding')
            method = data.get('method', 'unknown')
            print(f"    Face embedding: {len(face_emb) if face_emb else 0} dims ({method})")
        else:
            face_emb = None
            print(f"    Face embedding FAILED: {resp.status_code}")
    except Exception as e:
        print(f"    Face embedding error: {e}")
        face_emb = None

    # Get periocular embedding
    periocular_emb = None
    glasses_detected = False
    try:
        resp = requests.post(
            f"{EMBEDDING_SERVICE_URL}/encode_periocular",
            json={"image": f"data:image/jpeg;base64,{b64}"},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            if not data.get('fallback_to_face'):
                periocular_emb = data.get('embedding')
                glasses_detected = data.get('glasses_detected', False)
                print(f"    Periocular: {len(periocular_emb) if periocular_emb else 0} dims, glasses={glasses_detected}")
    except Exception as e:
        print(f"    Periocular error: {e}")

    return face_emb, periocular_emb, glasses_detected


def generate_augmented_embeddings(image_path, num_augmentations=5):
    """
    Generate multiple embeddings from augmented versions of the image.
    This improves matching against varied webcam conditions.
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    embeddings = []
    h, w = img.shape[:2]
    center = (w // 2, h // 2)

    # Original + augmentations
    augmentations = [
        ("original", img),
    ]

    # Slight rotations
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append((f"rot_{angle}", rotated))

    # Brightness variations
    bright = cv2.convertScaleAbs(img, alpha=1.2, beta=20)
    dark = cv2.convertScaleAbs(img, alpha=0.8, beta=-20)
    augmentations.append(("bright", bright))
    augmentations.append(("dark", dark))

    # Horizontal flip (for symmetry robustness)
    flipped = cv2.flip(img, 1)
    augmentations.append(("flipped", flipped))

    # CLAHE normalization
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    clahe_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    augmentations.append(("clahe", clahe_img))

    import base64

    for name, aug_img in augmentations[:num_augmentations]:
        try:
            _, buffer = cv2.imencode('.jpg', aug_img)
            b64 = base64.b64encode(buffer).decode('ascii')

            resp = requests.post(
                f"{EMBEDDING_SERVICE_URL}/encode?align=true",
                json={"image": f"data:image/jpeg;base64,{b64}"},
                timeout=30
            )
            if resp.status_code == 200:
                emb = resp.json().get('embedding')
                if emb:
                    embeddings.append(emb)
        except Exception as e:
            print(f"    Aug {name} failed: {e}")

    print(f"    Generated {len(embeddings)} augmented embeddings")
    return embeddings


def main():
    print("=" * 60)
    print("RE-ENCODING ALL INMATES WITH ALIGNED ARCFACE EMBEDDINGS")
    print("=" * 60)

    # Check embedding service
    try:
        resp = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        health = resp.json()
        print(f"\nEmbedding service: {health.get('status')}")
        print(f"Model: {health.get('model')}")
        print(f"ArcFace available: {health.get('arcface_available')}")
    except Exception as e:
        print(f"\nERROR: Embedding service not available: {e}")
        print("Start it with: python backend/app/utils/embedding_service.py")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        inmates = Inmate.query.all()
        print(f"\nFound {len(inmates)} inmates to re-encode\n")

        success_count = 0
        error_count = 0

        for i, inmate in enumerate(inmates, 1):
            print(f"[{i}/{len(inmates)}] {inmate.name} ({inmate.inmate_id})")

            if not inmate.mugshot_path:
                print("    SKIP: No mugshot")
                continue

            # Build full path to mugshot
            mugshot_path = inmate.mugshot_path
            if mugshot_path.startswith('/static/'):
                mugshot_path = os.path.join('app', mugshot_path[1:])
            elif mugshot_path.startswith('static/'):
                mugshot_path = os.path.join('app', mugshot_path)

            if not os.path.exists(mugshot_path):
                print(f"    SKIP: File not found: {mugshot_path}")
                error_count += 1
                continue

            # Get primary aligned embedding + periocular
            face_emb, periocular_emb, glasses = encode_with_alignment(mugshot_path)

            if face_emb is None:
                print("    ERROR: Failed to get face embedding")
                error_count += 1
                continue

            # Generate augmented embeddings
            aug_embeddings = generate_augmented_embeddings(mugshot_path, num_augmentations=6)

            # Update database
            try:
                inmate.face_encoding = face_emb
                inmate.face_encodings_json = json.dumps(aug_embeddings) if aug_embeddings else None
                inmate.periocular_encoding = periocular_emb
                inmate.has_glasses_in_mugshot = glasses
                db.session.commit()
                print(f"    SUCCESS: {len(aug_embeddings)} face + {'1 periocular' if periocular_emb else 'no periocular'}")
                success_count += 1
            except Exception as e:
                print(f"    DB ERROR: {e}")
                db.session.rollback()
                error_count += 1

        print("\n" + "=" * 60)
        print(f"COMPLETE: {success_count} success, {error_count} errors")
        print("=" * 60)


if __name__ == "__main__":
    main()
