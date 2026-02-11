#!/usr/bin/env python3
"""
Re-encode inmates with augmented embeddings for noise robustness.

Instead of storing a single clean embedding, we store multiple embeddings
including noisy versions. This allows matching noisy query images to
noisy stored embeddings.

Usage:
    cd backend
    python scripts/reencode_with_augmentation.py
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
import cv2

import warnings
warnings.filterwarnings('ignore')

import onnxruntime as ort


def backup_database(db_path: str) -> str:
    """Create backup of database."""
    backup_path = db_path.replace('.db', f'_backup_aug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def preprocess_for_arcface(img_bgr):
    """Preprocess image for ArcFace."""
    img_resized = cv2.resize(img_bgr, (112, 112))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_transposed = img_rgb.transpose(2, 0, 1)
    img_normalized = (img_transposed.astype(np.float32) - 127.5) / 127.5
    return np.expand_dims(img_normalized, axis=0)


def add_gaussian_noise(image, sigma):
    """Add Gaussian noise to an image."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    return noisy


def generate_augmentations(img_bgr):
    """Generate augmented versions of an image."""
    augmented = []

    # Original
    augmented.append(('original', img_bgr.copy()))

    # Noise levels - expanded range for better coverage
    for sigma in [10, 20, 25, 30, 35, 40]:
        noisy = add_gaussian_noise(img_bgr, sigma)
        augmented.append((f'noise_{sigma}', noisy))

    # Grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmented.append(('grayscale', gray_bgr))

    # Grayscale + noise (common in surveillance)
    gray_noisy = add_gaussian_noise(gray_bgr, 25)
    augmented.append(('grayscale_noisy', gray_noisy))

    # CLAHE enhanced
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    augmented.append(('clahe', enhanced))

    # Brightness variations
    bright = cv2.convertScaleAbs(img_bgr, alpha=1.3, beta=30)
    augmented.append(('bright', bright))

    dark = cv2.convertScaleAbs(img_bgr, alpha=0.7, beta=-20)
    augmented.append(('dark', dark))

    # Combined: noise + brightness
    noisy_dark = add_gaussian_noise(dark, 20)
    augmented.append(('noisy_dark', noisy_dark))

    return augmented


def main():
    print("=" * 60)
    print("HEIMDALL - AUGMENTED EMBEDDING RE-ENCODING")
    print("=" * 60)
    print()

    # Load ArcFace model
    model_path = os.path.expanduser("~/.insightface/models/buffalo_l/w600k_r50.onnx")
    print(f"Loading ArcFace model: {model_path}")
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print("Model loaded.")
    print()

    # Connect to database
    import sqlite3
    db_path = str(backend_dir / 'instance' / 'heimdall.db')

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    # Backup
    backup_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all inmates
    cursor.execute("SELECT id, inmate_id, name, mugshot_path FROM inmate")
    inmates = cursor.fetchall()

    print(f"Found {len(inmates)} inmates to re-encode")
    print(f"Each inmate will have ~8 augmented embeddings")
    print()

    success_count = 0
    fail_count = 0

    for db_id, inmate_id, name, mugshot_path in inmates:
        print(f"Processing: {name} ({inmate_id})")

        if not mugshot_path:
            print(f"  WARNING: No mugshot path")
            fail_count += 1
            continue

        # Load image
        clean_path = mugshot_path.lstrip('/')
        possible_paths = [
            backend_dir / 'app' / clean_path,
            backend_dir / clean_path,
            backend_dir / 'app' / 'static' / 'inmate_images' / Path(mugshot_path).name,
        ]

        full_path = None
        for p in possible_paths:
            if p.exists():
                full_path = p
                break

        if not full_path:
            print(f"  ERROR: Image not found")
            fail_count += 1
            continue

        img_bgr = cv2.imread(str(full_path))
        if img_bgr is None:
            print(f"  ERROR: Could not read image")
            fail_count += 1
            continue

        # Generate augmentations and get embeddings
        augmentations = generate_augmentations(img_bgr)
        all_embeddings = []

        for aug_name, aug_img in augmentations:
            img_input = preprocess_for_arcface(aug_img)
            embedding = session.run([output_name], {input_name: img_input})[0][0]
            embedding = embedding / np.linalg.norm(embedding)
            all_embeddings.append(embedding.tolist())

        # Store as JSON list of embeddings
        embeddings_json = json.dumps(all_embeddings)

        # Store the average embedding as the primary (for backward compat)
        avg_embedding = np.mean(all_embeddings, axis=0)
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        embedding_blob = avg_embedding.astype(np.float32).tobytes()

        # Update database
        cursor.execute("""
            UPDATE inmate
            SET face_encoding = ?,
                face_encodings_json = ?
            WHERE id = ?
        """, (embedding_blob, embeddings_json, db_id))
        conn.commit()

        print(f"  Stored {len(all_embeddings)} augmented embeddings")
        success_count += 1

    conn.close()

    print()
    print("=" * 60)
    print("RE-ENCODING COMPLETE")
    print("=" * 60)
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print()
    print("Each inmate now has multiple embeddings including noisy versions.")
    print("The recognition system should match against ALL stored embeddings.")


if __name__ == '__main__':
    main()
