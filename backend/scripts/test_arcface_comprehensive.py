#!/usr/bin/env python3
"""
Comprehensive ArcFace evaluation - tests all distortion types.
Uses the embedding service for proper face alignment.
"""

import os
import sys
import cv2
import numpy as np
import json
import requests
from io import BytesIO
from scipy.spatial.distance import cosine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

# Embedding service URLs
EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"
ROTATION_AUG_URL = "http://127.0.0.1:5001/encode_with_rotation_augmentation"

_stats = {'direct': 0, 'direct_denoised': 0, 'rotation_aug': 0, 'service_errors': 0}

# Distortions that benefit from denoising
NOISE_DISTORTIONS = {'noise_10', 'noise_20', 'noise_30', 'noise_50', 'salt_pepper', 'combined'}


def get_arcface_embedding(img_bgr, use_rotation_augmentation=False, use_denoising=False):
    """Get ArcFace embedding via embedding service.

    Args:
        img_bgr: BGR image
        use_rotation_augmentation: If True, returns multiple embeddings for different rotations
        use_denoising: If True, applies adaptive denoising for noisy images
    """
    global _stats

    try:
        _, buffer = cv2.imencode('.jpg', img_bgr)
        files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}

        if use_rotation_augmentation:
            resp = requests.post(ROTATION_AUG_URL, files=files, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get('embeddings', [])
                if embeddings:
                    _stats['rotation_aug'] += 1
                    # Return list of (rotation, embedding) tuples
                    return [(e['rotation'], np.array(e['embedding'])) for e in embeddings]
        else:
            # Add denoise parameter if requested
            url = EMBEDDING_SERVICE_URL
            if use_denoising:
                url += "?denoise=auto"

            resp = requests.post(url, files=files, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                emb = data.get('embedding')
                if emb:
                    if use_denoising and data.get('denoised', False):
                        _stats['direct_denoised'] += 1
                    else:
                        _stats['direct'] += 1
                    return np.array(emb)

        _stats['service_errors'] += 1
        return None

    except Exception as e:
        _stats['service_errors'] += 1
        return None


def print_alignment_stats():
    """Print encoding statistics."""
    print(f"\nEncoding stats: {_stats['direct']} direct, {_stats['direct_denoised']} denoised, {_stats['rotation_aug']} rotation-augmented")
    if _stats['service_errors'] > 0:
        print(f"Service errors: {_stats['service_errors']}")


def add_gaussian_noise(image, sigma):
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def reduce_resolution(image, target_size):
    original_size = (image.shape[1], image.shape[0])
    small = cv2.resize(image, (target_size, target_size), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, original_size, interpolation=cv2.INTER_LINEAR)


def apply_distortion(image, distortion_type):
    """Apply distortion and return distorted image."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    if distortion_type == 'original':
        return image.copy()
    elif distortion_type == 'rotation_30':
        M = cv2.getRotationMatrix2D(center, 30, 1.0)
        return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    elif distortion_type == 'dark':
        return cv2.convertScaleAbs(image, alpha=0.5, beta=-30)
    elif distortion_type == 'bright':
        return cv2.convertScaleAbs(image, alpha=1.5, beta=30)
    elif distortion_type == 'blur_11':
        return cv2.GaussianBlur(image, (11, 11), 0)
    elif distortion_type == 'blur_21':
        return cv2.GaussianBlur(image, (21, 21), 0)
    elif distortion_type == 'noise_10':
        return add_gaussian_noise(image, 10)
    elif distortion_type == 'noise_20':
        return add_gaussian_noise(image, 20)
    elif distortion_type == 'noise_30':
        return add_gaussian_noise(image, 30)
    elif distortion_type == 'noise_50':
        return add_gaussian_noise(image, 50)
    elif distortion_type == 'resolution_48':
        return reduce_resolution(image, 48)
    elif distortion_type == 'resolution_32':
        return reduce_resolution(image, 32)
    elif distortion_type == 'grayscale':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif distortion_type == 'jpeg_low':
        _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 10])
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    elif distortion_type == 'combined':
        M = cv2.getRotationMatrix2D(center, 20, 1.0)
        result = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.convertScaleAbs(result, alpha=0.8, beta=-10)
        return add_gaussian_noise(result, 15)
    elif distortion_type == 'motion_blur':
        kernel_size = 15
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[kernel_size // 2, :] = 1
        kernel = kernel / kernel_size
        return cv2.filter2D(image, -1, kernel)
    elif distortion_type == 'salt_pepper':
        result = image.copy()
        prob = 0.05
        rnd = np.random.random(image.shape[:2])
        result[rnd < prob/2] = 0
        result[rnd > 1 - prob/2] = 255
        return result
    else:
        return image.copy()


def main():
    print("=" * 70)
    print("ARCFACE COMPREHENSIVE DISTORTION TEST")
    print("=" * 70)
    print(f"Using embedding service: {EMBEDDING_SERVICE_URL}")
    print()

    # Connect to database
    import sqlite3
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, 'instance', 'heimdall.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, inmate_id, name, mugshot_path, face_encodings_json
        FROM inmate
        WHERE face_encodings_json IS NOT NULL
    """)
    inmates = cursor.fetchall()

    # Load stored embeddings
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

    # Distortion types to test
    distortions = [
        'original', 'rotation_30', 'dark', 'bright', 'blur_11', 'blur_21',
        'noise_10', 'noise_20', 'noise_30', 'noise_50',
        'resolution_48', 'resolution_32', 'grayscale', 'jpeg_low',
        'combined', 'motion_blur', 'salt_pepper'
    ]

    results = {d: {'correct': 0, 'wrong': 0, 'total': 0} for d in distortions}

    test_inmates = list(inmate_embeddings.keys())
    print(f"Testing {len(test_inmates)} inmates with {len(distortions)} distortions")
    print("-" * 70)

    for idx, inmate_id in enumerate(test_inmates):
        data = inmate_embeddings[inmate_id]
        mugshot_path = data['mugshot_path']

        if not mugshot_path:
            continue

        clean_path = mugshot_path.lstrip('/')
        full_path = os.path.join(backend_dir, 'app', clean_path)

        if not os.path.exists(full_path):
            full_path = os.path.join(backend_dir, 'app', 'static', 'inmate_images',
                                     os.path.basename(mugshot_path))

        if not os.path.exists(full_path):
            continue

        image = cv2.imread(full_path)
        if image is None:
            continue

        # Progress indicator
        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx + 1}/{len(test_inmates)} inmates tested...")

        for distortion in distortions:
            distorted = apply_distortion(image, distortion)

            # Use rotation augmentation for rotation-related distortions
            use_rot_aug = distortion in ['rotation_30', 'combined']
            # Use denoising for noise-related distortions
            use_denoise = distortion in NOISE_DISTORTIONS

            if use_rot_aug:
                # Get multiple embeddings for different rotations
                rot_embeddings = get_arcface_embedding(distorted, use_rotation_augmentation=True)
                if rot_embeddings is None:
                    results[distortion]['total'] += 1
                    results[distortion]['wrong'] += 1
                    continue

                # Find best match across all rotations
                best_match = None
                best_distance = float('inf')

                for rot_angle, query_emb in rot_embeddings:
                    for other_id, other_data in inmate_embeddings.items():
                        for emb in other_data['embeddings']:
                            dist = cosine(query_emb, emb)
                            if dist < best_distance:
                                best_distance = dist
                                best_match = other_id
            else:
                # Standard single embedding (with optional denoising)
                query_emb = get_arcface_embedding(distorted, use_denoising=use_denoise)
                if query_emb is None:
                    results[distortion]['total'] += 1
                    results[distortion]['wrong'] += 1
                    continue

                best_match = None
                best_distance = float('inf')

                for other_id, other_data in inmate_embeddings.items():
                    for emb in other_data['embeddings']:
                        dist = cosine(query_emb, emb)
                        if dist < best_distance:
                            best_distance = dist
                            best_match = other_id

            results[distortion]['total'] += 1

            if best_match == inmate_id and best_distance < 0.4:
                results[distortion]['correct'] += 1
            else:
                results[distortion]['wrong'] += 1

    # Print results
    print()
    print("=" * 70)
    print("RESULTS BY DISTORTION TYPE")
    print("=" * 70)
    print()
    print(f"{'Distortion':<20} {'Accuracy':>10} {'Correct':>10} {'Total':>10}")
    print("-" * 50)

    for distortion in distortions:
        r = results[distortion]
        if r['total'] > 0:
            accuracy = (r['correct'] / r['total']) * 100
            print(f"{distortion:<20} {accuracy:>9.1f}% {r['correct']:>10} {r['total']:>10}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY - COMPARISON WITH PREVIOUS FACENET RESULTS")
    print("=" * 70)
    print()
    print(f"{'Distortion':<20} {'FaceNet (Old)':>15} {'ArcFace (New)':>15} {'Change':>10}")
    print("-" * 60)

    # Previous FaceNet results from CLAUDE.md
    old_results = {
        'original': 100.0,
        'rotation_30': 100.0,
        'dark': 100.0,
        'blur_11': 94.3,
        'noise_30': 19.1,
        'resolution_48': 99.0,
        'grayscale': 100.0,
        'combined': 14.3,
    }

    for distortion in ['original', 'rotation_30', 'dark', 'blur_11', 'noise_30',
                        'resolution_48', 'grayscale', 'combined']:
        r = results.get(distortion, {'correct': 0, 'total': 1})
        if r['total'] > 0:
            new_acc = (r['correct'] / r['total']) * 100
            old_acc = old_results.get(distortion, 0)
            change = new_acc - old_acc
            change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
            print(f"{distortion:<20} {old_acc:>14.1f}% {new_acc:>14.1f}% {change_str:>10}")

    # Overall
    total_correct = sum(r['correct'] for r in results.values())
    total_tests = sum(r['total'] for r in results.values())
    overall = (total_correct / total_tests * 100) if total_tests > 0 else 0

    print()
    print(f"Overall Accuracy: {overall:.1f}% ({total_correct}/{total_tests})")
    print()

    # Target check
    noise_30 = results['noise_30']
    if noise_30['total'] > 0:
        acc = (noise_30['correct'] / noise_30['total']) * 100
        if acc >= 97:
            print("TARGET ACHIEVED: noise_30 accuracy >= 97%")
        else:
            print(f"Target: 97% on noise_30, Current: {acc:.1f}%")

    # Print alignment stats
    print_alignment_stats()

    conn.close()


if __name__ == '__main__':
    main()
