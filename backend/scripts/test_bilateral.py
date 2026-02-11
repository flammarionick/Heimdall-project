#!/usr/bin/env python3
"""
Test different bilateral filter parameters.
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


def bilateral_multi(img_bgr, d, sigma_color, sigma_space, passes=1):
    """Apply bilateral filter multiple times."""
    result = img_bgr.copy()
    for _ in range(passes):
        result = cv2.bilateralFilter(result, d, sigma_color, sigma_space)
    return result


def median_blur(img_bgr, ksize=5):
    """Median blur - good for impulse noise."""
    return cv2.medianBlur(img_bgr, ksize)


def adaptive_denoise(img_bgr):
    """Combine median blur (for outliers) + bilateral (for Gaussian noise)."""
    # First pass: median to remove salt/pepper and outliers
    result = cv2.medianBlur(img_bgr, 3)
    # Second pass: bilateral for smooth denoising
    result = cv2.bilateralFilter(result, 9, 75, 75)
    return result


def main():
    print("=" * 60)
    print("BILATERAL FILTER PARAMETER TEST")
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

    # Test methods - different bilateral parameters
    methods = [
        ('baseline', lambda x: x),
        ('bilateral_9_75_75', lambda x: bilateral_multi(x, 9, 75, 75, 1)),
        ('bilateral_9_100_100', lambda x: bilateral_multi(x, 9, 100, 100, 1)),
        ('bilateral_9_150_150', lambda x: bilateral_multi(x, 9, 150, 150, 1)),
        ('bilateral_2pass', lambda x: bilateral_multi(x, 9, 75, 75, 2)),
        ('bilateral_3pass', lambda x: bilateral_multi(x, 9, 75, 75, 3)),
        ('median_bilateral', adaptive_denoise),
        ('median_only_5', lambda x: median_blur(x, 5)),
        ('gaussian_bilateral', lambda x: bilateral_multi(cv2.GaussianBlur(x, (3,3), 0), 9, 75, 75, 1)),
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
    print("RESULTS - NOISE_30")
    print("=" * 60)
    print()
    print(f"{'Method':<25} {'Acc@0.4':>10} {'Acc@0.5':>10} {'Acc@0.6':>10} {'MeanDist':>10}")
    print("-" * 65)

    for method_name, _ in methods:
        r = results[method_name]
        if r['distances']:
            total = len(r['distances'])
            acc_04 = sum(1 for d in r['distances'] if d < 0.4) / total * 100
            acc_05 = sum(1 for d in r['distances'] if d < 0.5) / total * 100
            acc_06 = sum(1 for d in r['distances'] if d < 0.6) / total * 100
            mean_dist = np.mean(r['distances'])

            print(f"{method_name:<25} {acc_04:>9.1f}% {acc_05:>9.1f}% {acc_06:>9.1f}% {mean_dist:>9.4f}")

    conn.close()


if __name__ == '__main__':
    main()
