#!/usr/bin/env python3
"""
Test threshold safety - ensure no false positives at 0.5/0.6 thresholds.
"""

import os
import sys
import cv2
import numpy as np
import json
import requests
import sqlite3
from io import BytesIO
from scipy.spatial.distance import cosine
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"


def get_service_embedding(img_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', img_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    resp = requests.post(EMBEDDING_SERVICE_URL, files=files, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        return np.array(data.get('embedding'))
    return None


def add_gaussian_noise(image, sigma):
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def bilateral_denoise(img_bgr):
    return cv2.bilateralFilter(img_bgr, 9, 75, 75)


def main():
    print("=" * 60)
    print("THRESHOLD SAFETY TEST")
    print("=" * 60)

    # Connect to database
    db_path = str(backend_dir / 'instance' / 'heimdall.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load all inmates
    cursor.execute("""
        SELECT id, inmate_id, name, mugshot_path, face_encodings_json
        FROM inmate
        WHERE face_encodings_json IS NOT NULL
    """)
    inmates = cursor.fetchall()

    # Build embedding database
    inmate_embeddings = {}
    for db_id, inmate_id, name, mugshot_path, encodings_json in inmates:
        try:
            encodings = json.loads(encodings_json)
            if isinstance(encodings[0], list):
                inmate_embeddings[inmate_id] = {
                    'name': name,
                    'mugshot_path': mugshot_path,
                    'embeddings': [np.array(e) for e in encodings]
                }
            else:
                inmate_embeddings[inmate_id] = {
                    'name': name,
                    'mugshot_path': mugshot_path,
                    'embeddings': [np.array(encodings)]
                }
        except:
            continue

    print(f"Loaded {len(inmate_embeddings)} inmates")
    print()

    # Test: for each noisy+denoised image, measure distance to:
    # 1. Own embedding (should be small)
    # 2. All other embeddings (should be large)

    self_distances = []
    other_distances = []
    false_positives = {0.4: 0, 0.5: 0, 0.6: 0}
    total_comparisons = 0

    for idx, inmate_id in enumerate(list(inmate_embeddings.keys())):
        data = inmate_embeddings[inmate_id]
        mugshot_path = data['mugshot_path']

        if not mugshot_path:
            continue

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
            continue

        image = cv2.imread(str(full_path))
        if image is None:
            continue

        # Add noise and denoise
        noisy = add_gaussian_noise(image, 30)
        denoised = bilateral_denoise(noisy)
        query_emb = get_service_embedding(denoised)

        if query_emb is None:
            continue

        # Measure distance to own embedding
        for emb in data['embeddings']:
            dist = cosine(query_emb, emb)
            self_distances.append(dist)

        # Measure distance to OTHER embeddings
        for other_id, other_data in inmate_embeddings.items():
            if other_id == inmate_id:
                continue
            for emb in other_data['embeddings']:
                dist = cosine(query_emb, emb)
                other_distances.append(dist)
                total_comparisons += 1

                # Check false positives
                if dist < 0.4:
                    false_positives[0.4] += 1
                if dist < 0.5:
                    false_positives[0.5] += 1
                if dist < 0.6:
                    false_positives[0.6] += 1

        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx+1}/{len(inmate_embeddings)}")

    # Print results
    print()
    print("=" * 60)
    print("DISTANCE DISTRIBUTIONS")
    print("=" * 60)

    print(f"\nSELF (noisy query vs own DB embedding):")
    print(f"  Count: {len(self_distances)}")
    print(f"  Min: {min(self_distances):.4f}")
    print(f"  Max: {max(self_distances):.4f}")
    print(f"  Mean: {np.mean(self_distances):.4f}")
    print(f"  Median: {np.median(self_distances):.4f}")

    print(f"\nOTHER (noisy query vs other people's DB embeddings):")
    print(f"  Count: {len(other_distances)}")
    print(f"  Min: {min(other_distances):.4f}")
    print(f"  Max: {max(other_distances):.4f}")
    print(f"  Mean: {np.mean(other_distances):.4f}")
    print(f"  Median: {np.median(other_distances):.4f}")

    print(f"\nFALSE POSITIVES (other person matched incorrectly):")
    for threshold in [0.4, 0.5, 0.6]:
        fp = false_positives[threshold]
        rate = fp / total_comparisons * 100 if total_comparisons > 0 else 0
        print(f"  Threshold {threshold}: {fp} / {total_comparisons} ({rate:.4f}%)")

    print(f"\nGAP ANALYSIS:")
    self_max = max(self_distances)
    other_min = min(other_distances)
    gap = other_min - self_max
    print(f"  Max self-distance: {self_max:.4f}")
    print(f"  Min other-distance: {other_min:.4f}")
    print(f"  Gap: {gap:.4f}")

    if gap > 0:
        safe_threshold = (self_max + other_min) / 2
        print(f"  Safe threshold (midpoint): {safe_threshold:.4f}")

    conn.close()


if __name__ == '__main__':
    main()
