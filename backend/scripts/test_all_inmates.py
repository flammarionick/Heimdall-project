#!/usr/bin/env python3
"""
Comprehensive Inmate Identification Test

Tests all 105 inmates under various conditions:
1. Normal (original image)
2. Obscured (blur, partial occlusion simulation)
3. Various noise levels (sigma 10, 20, 30, 50)

Reports per-inmate identification success/failure.
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
from datetime import datetime

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"
ROTATION_AUG_URL = "http://127.0.0.1:5001/encode_with_rotation_augmentation"

# Matching threshold - 0.5 is safe (0 false positives verified)
MATCH_THRESHOLD = 0.5


def get_embedding(img_bgr, use_denoising=False, use_rotation_aug=False):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', img_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}

    try:
        if use_rotation_aug:
            resp = requests.post(ROTATION_AUG_URL, files=files, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get('embeddings', [])
                if embeddings:
                    return [(e['rotation'], np.array(e['embedding'])) for e in embeddings]
            return None
        else:
            url = EMBEDDING_SERVICE_URL
            if use_denoising:
                url += "?denoise=auto"
            resp = requests.post(url, files=files, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                emb = data.get('embedding')
                if emb:
                    return np.array(emb)
            return None
    except Exception as e:
        return None


def add_gaussian_noise(image, sigma):
    """Add Gaussian noise to image."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def apply_blur(image, kernel_size=15):
    """Apply Gaussian blur."""
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def apply_motion_blur(image, kernel_size=15):
    """Apply horizontal motion blur."""
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[kernel_size // 2, :] = 1
    kernel = kernel / kernel_size
    return cv2.filter2D(image, -1, kernel)


def apply_partial_occlusion(image, occlusion_type='lower'):
    """Simulate partial face occlusion (like mask)."""
    result = image.copy()
    h, w = image.shape[:2]

    if occlusion_type == 'lower':
        # Cover lower half (like wearing a mask)
        result[h//2:, :] = 0
    elif occlusion_type == 'left':
        # Cover left half
        result[:, :w//2] = 0
    elif occlusion_type == 'right':
        # Cover right half
        result[:, w//2:] = 0
    elif occlusion_type == 'random':
        # Random rectangular occlusion
        x1 = np.random.randint(0, w//2)
        y1 = np.random.randint(0, h//2)
        x2 = x1 + np.random.randint(w//4, w//2)
        y2 = y1 + np.random.randint(h//4, h//2)
        result[y1:y2, x1:x2] = 0

    return result


def apply_rotation(image, angle):
    """Apply rotation."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def find_best_match(query_emb, inmate_embeddings, use_rotation_aug=False):
    """Find best matching inmate."""
    best_match = None
    best_distance = float('inf')

    if use_rotation_aug and isinstance(query_emb, list):
        # Multiple embeddings from rotation augmentation
        for rot_angle, emb in query_emb:
            for inmate_id, data in inmate_embeddings.items():
                for db_emb in data['embeddings']:
                    dist = cosine(emb, db_emb)
                    if dist < best_distance:
                        best_distance = dist
                        best_match = inmate_id
    else:
        # Single embedding
        for inmate_id, data in inmate_embeddings.items():
            for db_emb in data['embeddings']:
                dist = cosine(query_emb, db_emb)
                if dist < best_distance:
                    best_distance = dist
                    best_match = inmate_id

    return best_match, best_distance


def main():
    print("=" * 80)
    print("COMPREHENSIVE INMATE IDENTIFICATION TEST")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Match threshold: {MATCH_THRESHOLD}")
    print()

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
    inmate_info = {}

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
            inmate_info[inmate_id] = {'name': name, 'mugshot_path': mugshot_path}
        except:
            continue

    print(f"Loaded {len(inmate_embeddings)} inmates from database")
    print()

    # Test conditions: (name, transform_fn, use_denoise, use_rot_aug)
    test_conditions = [
        # Normal
        ('normal', lambda img: img, False, False),

        # Noise variations - use denoising
        ('noise_10', lambda img: add_gaussian_noise(img, 10), True, False),
        ('noise_20', lambda img: add_gaussian_noise(img, 20), True, False),
        ('noise_30', lambda img: add_gaussian_noise(img, 30), True, False),
        ('noise_50', lambda img: add_gaussian_noise(img, 50), True, False),

        # Blur/obscured
        ('blur_light', lambda img: apply_blur(img, 7), False, False),
        ('blur_heavy', lambda img: apply_blur(img, 15), False, False),
        ('motion_blur', lambda img: apply_motion_blur(img, 15), False, False),

        # Occlusion (simulating masks, partial views)
        ('occluded_lower', lambda img: apply_partial_occlusion(img, 'lower'), False, False),
        ('occluded_left', lambda img: apply_partial_occlusion(img, 'left'), False, False),
        ('occluded_right', lambda img: apply_partial_occlusion(img, 'right'), False, False),

        # Rotation
        ('rotation_15', lambda img: apply_rotation(img, 15), False, True),
        ('rotation_30', lambda img: apply_rotation(img, 30), False, True),

        # Combined challenges
        ('noise_blur', lambda img: apply_blur(add_gaussian_noise(img, 20), 7), True, False),
        ('dark', lambda img: cv2.convertScaleAbs(img, alpha=0.5, beta=-30), False, False),
        ('bright', lambda img: cv2.convertScaleAbs(img, alpha=1.5, beta=30), False, False),
    ]

    # Results storage
    results = {cond[0]: {'passed': [], 'failed': [], 'errors': []} for cond in test_conditions}

    # Test each inmate
    total_inmates = len(inmate_embeddings)

    for idx, (inmate_id, data) in enumerate(inmate_embeddings.items()):
        mugshot_path = data['mugshot_path']
        name = data['name']

        if not mugshot_path:
            continue

        # Find image path
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
            for cond_name, _, _, _ in test_conditions:
                results[cond_name]['errors'].append((inmate_id, name, "Image not found"))
            continue

        image = cv2.imread(str(full_path))
        if image is None:
            for cond_name, _, _, _ in test_conditions:
                results[cond_name]['errors'].append((inmate_id, name, "Could not read image"))
            continue

        # Test each condition
        for cond_name, transform_fn, use_denoise, use_rot_aug in test_conditions:
            try:
                # Apply transformation
                test_img = transform_fn(image)

                # Get embedding
                if use_rot_aug:
                    query_emb = get_embedding(test_img, use_denoising=use_denoise, use_rotation_aug=True)
                else:
                    query_emb = get_embedding(test_img, use_denoising=use_denoise)

                if query_emb is None:
                    results[cond_name]['errors'].append((inmate_id, name, "Embedding failed"))
                    continue

                # Find best match
                best_match, best_distance = find_best_match(query_emb, inmate_embeddings, use_rot_aug)

                # Check if correct
                if best_match == inmate_id and best_distance < MATCH_THRESHOLD:
                    results[cond_name]['passed'].append((inmate_id, name, best_distance))
                else:
                    matched_name = inmate_embeddings.get(best_match, {}).get('name', 'Unknown')
                    results[cond_name]['failed'].append((inmate_id, name, best_distance, best_match, matched_name))

            except Exception as e:
                results[cond_name]['errors'].append((inmate_id, name, str(e)))

        # Progress
        if (idx + 1) % 10 == 0:
            print(f"  Progress: {idx + 1}/{total_inmates} inmates tested...")

    conn.close()

    # Print results
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Condition':<20} {'Passed':>8} {'Failed':>8} {'Errors':>8} {'Accuracy':>10}")
    print("-" * 60)

    category_results = {
        'Normal': [],
        'Noise': [],
        'Obscured/Blur': [],
        'Occlusion': [],
        'Rotation': [],
        'Other': []
    }

    for cond_name, _, _, _ in test_conditions:
        r = results[cond_name]
        passed = len(r['passed'])
        failed = len(r['failed'])
        errors = len(r['errors'])
        total = passed + failed
        accuracy = (passed / total * 100) if total > 0 else 0

        print(f"{cond_name:<20} {passed:>8} {failed:>8} {errors:>8} {accuracy:>9.1f}%")

        # Categorize
        if 'noise' in cond_name:
            category_results['Noise'].append((cond_name, accuracy))
        elif 'blur' in cond_name or 'motion' in cond_name:
            category_results['Obscured/Blur'].append((cond_name, accuracy))
        elif 'occluded' in cond_name:
            category_results['Occlusion'].append((cond_name, accuracy))
        elif 'rotation' in cond_name:
            category_results['Rotation'].append((cond_name, accuracy))
        elif cond_name == 'normal':
            category_results['Normal'].append((cond_name, accuracy))
        else:
            category_results['Other'].append((cond_name, accuracy))

    # Category summary
    print()
    print("=" * 80)
    print("CATEGORY SUMMARY")
    print("=" * 80)
    print()

    for category, items in category_results.items():
        if items:
            avg_acc = sum(acc for _, acc in items) / len(items)
            print(f"{category}: {avg_acc:.1f}% average")
            for name, acc in items:
                print(f"  - {name}: {acc:.1f}%")
            print()

    # Failed inmates details
    print("=" * 80)
    print("INMATES THAT FAILED NORMAL IDENTIFICATION")
    print("=" * 80)

    normal_failed = results['normal']['failed']
    if normal_failed:
        print(f"\n{len(normal_failed)} inmates failed normal identification:")
        for inmate_id, name, dist, matched_id, matched_name in normal_failed:
            print(f"  - {name} ({inmate_id}): dist={dist:.4f}, matched as {matched_name}")
    else:
        print("\nAll inmates passed normal identification!")

    # Per-inmate summary: who can be identified under all conditions?
    print()
    print("=" * 80)
    print("PER-INMATE IDENTIFICATION CAPABILITY")
    print("=" * 80)

    # Count how many conditions each inmate passes
    inmate_pass_count = {}
    total_conditions = len(test_conditions)

    for inmate_id in inmate_embeddings.keys():
        name = inmate_embeddings[inmate_id]['name']
        passes = 0
        for cond_name, _, _, _ in test_conditions:
            if any(iid == inmate_id for iid, _, _ in results[cond_name]['passed']):
                passes += 1
        inmate_pass_count[inmate_id] = (name, passes)

    # Sort by pass count
    sorted_inmates = sorted(inmate_pass_count.items(), key=lambda x: x[1][1], reverse=True)

    # Perfect identification (all conditions)
    perfect = [(iid, name) for iid, (name, count) in sorted_inmates if count == total_conditions]
    print(f"\nPerfect identification (all {total_conditions} conditions): {len(perfect)} inmates")

    # Good identification (>= 80% conditions)
    good_threshold = int(total_conditions * 0.8)
    good = [(iid, name, count) for iid, (name, count) in sorted_inmates if count >= good_threshold and count < total_conditions]
    print(f"Good identification (>= {good_threshold} conditions): {len(good)} inmates")

    # Poor identification (< 50% conditions)
    poor_threshold = int(total_conditions * 0.5)
    poor = [(iid, name, count) for iid, (name, count) in sorted_inmates if count < poor_threshold]
    print(f"Poor identification (< {poor_threshold} conditions): {len(poor)} inmates")

    if poor:
        print("\nInmates with poor identification:")
        for iid, name, count in poor:
            print(f"  - {name} ({iid}): {count}/{total_conditions} conditions passed")

    # Overall statistics
    print()
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    total_tests = sum(len(r['passed']) + len(r['failed']) for r in results.values())
    total_passed = sum(len(r['passed']) for r in results.values())
    overall_accuracy = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\nTotal tests: {total_tests}")
    print(f"Total passed: {total_passed}")
    print(f"Overall accuracy: {overall_accuracy:.1f}%")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
