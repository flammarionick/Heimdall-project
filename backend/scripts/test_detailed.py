#!/usr/bin/env python3
"""
Detailed test to understand accuracy issues.
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

def get_service_embedding(img_bgr, use_denoising=False):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', img_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}

    try:
        url = EMBEDDING_SERVICE_URL
        if use_denoising:
            url += "?denoise=auto"

        resp = requests.post(url, files=files, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return np.array(data.get('embedding')), None
        else:
            return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)


def add_gaussian_noise(image, sigma):
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def main():
    print("=" * 60)
    print("DETAILED ACCURACY TEST")
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

    # Test only "original" and "noise_30"
    test_cases = ['original', 'noise_30']
    results = {tc: {'correct': 0, 'wrong': 0, 'error': 0, 'distances': []} for tc in test_cases}
    failures = []

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

        for test_case in test_cases:
            if test_case == 'original':
                test_img = image.copy()
                use_denoise = False
            else:  # noise_30
                test_img = add_gaussian_noise(image, 30)
                use_denoise = True

            query_emb, error = get_service_embedding(test_img, use_denoising=use_denoise)

            if error or query_emb is None:
                results[test_case]['error'] += 1
                if error and len(failures) < 5:
                    failures.append(f"{data['name']} ({test_case}): {error}")
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

            results[test_case]['distances'].append(best_distance)

            if best_match == inmate_id and best_distance < 0.4:
                results[test_case]['correct'] += 1
            else:
                results[test_case]['wrong'] += 1
                if len(failures) < 10 and test_case == 'original':
                    failures.append(f"ORIGINAL FAIL: {data['name']} - best_dist={best_distance:.4f}, matched={best_match}")

        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx+1}/{len(inmate_embeddings)}")

    # Print results
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    for test_case in test_cases:
        r = results[test_case]
        total = r['correct'] + r['wrong'] + r['error']
        accuracy = (r['correct'] / (r['correct'] + r['wrong']) * 100) if (r['correct'] + r['wrong']) > 0 else 0

        print(f"\n{test_case.upper()}:")
        print(f"  Correct: {r['correct']}")
        print(f"  Wrong: {r['wrong']}")
        print(f"  Errors: {r['error']}")
        print(f"  Accuracy: {accuracy:.1f}%")

        if r['distances']:
            print(f"  Distance stats:")
            print(f"    Min: {min(r['distances']):.4f}")
            print(f"    Max: {max(r['distances']):.4f}")
            print(f"    Mean: {np.mean(r['distances']):.4f}")
            print(f"    Median: {np.median(r['distances']):.4f}")

            # Check threshold impact
            within_03 = sum(1 for d in r['distances'] if d < 0.3)
            within_04 = sum(1 for d in r['distances'] if d < 0.4)
            within_05 = sum(1 for d in r['distances'] if d < 0.5)
            within_06 = sum(1 for d in r['distances'] if d < 0.6)
            print(f"    Within 0.3: {within_03} ({within_03/len(r['distances'])*100:.1f}%)")
            print(f"    Within 0.4: {within_04} ({within_04/len(r['distances'])*100:.1f}%)")
            print(f"    Within 0.5: {within_05} ({within_05/len(r['distances'])*100:.1f}%)")
            print(f"    Within 0.6: {within_06} ({within_06/len(r['distances'])*100:.1f}%)")

    if failures:
        print(f"\n\nSample failures:")
        for f in failures[:10]:
            print(f"  {f}")

    conn.close()


if __name__ == '__main__':
    main()
