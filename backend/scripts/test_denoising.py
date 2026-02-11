#!/usr/bin/env python3
"""
Test the effect of denoising on noise_30 accuracy.
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


def denoise_nlm(img_bgr, h=10):
    """Non-local means denoising."""
    return cv2.fastNlMeansDenoisingColored(img_bgr, None, h, h, 7, 21)


def denoise_bilateral(img_bgr):
    """Bilateral filter - preserves edges better."""
    return cv2.bilateralFilter(img_bgr, 9, 75, 75)


def denoise_combined(img_bgr, h=12):
    """Combined denoising: NLM + bilateral."""
    denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, h, h, 7, 21)
    return cv2.bilateralFilter(denoised, 5, 50, 50)


def main():
    print("=" * 60)
    print("DENOISING EFFECT TEST")
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

    # Test methods
    methods = [
        ('no_denoise', lambda x: x),
        ('nlm_h5', lambda x: denoise_nlm(x, 5)),
        ('nlm_h10', lambda x: denoise_nlm(x, 10)),
        ('nlm_h15', lambda x: denoise_nlm(x, 15)),
        ('bilateral', denoise_bilateral),
        ('combined_h10', lambda x: denoise_combined(x, 10)),
        ('combined_h15', lambda x: denoise_combined(x, 15)),
    ]

    results = {m[0]: {'correct': 0, 'distances': []} for m in methods}

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

        # Add noise
        noisy = add_gaussian_noise(image, 30)

        for method_name, denoise_fn in methods:
            processed = denoise_fn(noisy)
            query_emb = get_service_embedding(processed)

            if query_emb is None:
                continue

            # Find best match
            best_match = None
            best_distance = float('inf')

            for other_id, other_data in inmate_embeddings.items():
                for emb in other_data['embeddings']:
                    dist = cosine(query_emb, emb)
                    if dist < best_distance:
                        best_distance = dist
                        best_match = other_id

            results[method_name]['distances'].append(best_distance)

            if best_match == inmate_id and best_distance < 0.4:
                results[method_name]['correct'] += 1

        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx+1}/{len(inmate_embeddings)}")

    # Print results
    print()
    print("=" * 60)
    print("RESULTS - NOISE_30 with different denoising methods")
    print("=" * 60)
    print()
    print(f"{'Method':<20} {'Accuracy':>10} {'Mean Dist':>12} {'<0.4':>10} {'<0.5':>10} {'<0.6':>10}")
    print("-" * 72)

    for method_name, _ in methods:
        r = results[method_name]
        if r['distances']:
            total = len(r['distances'])
            accuracy = r['correct'] / total * 100
            mean_dist = np.mean(r['distances'])
            within_04 = sum(1 for d in r['distances'] if d < 0.4) / total * 100
            within_05 = sum(1 for d in r['distances'] if d < 0.5) / total * 100
            within_06 = sum(1 for d in r['distances'] if d < 0.6) / total * 100

            print(f"{method_name:<20} {accuracy:>9.1f}% {mean_dist:>11.4f} {within_04:>9.1f}% {within_05:>9.1f}% {within_06:>9.1f}%")

    conn.close()


if __name__ == '__main__':
    main()
