#!/usr/bin/env python3
"""
Distortion Assessment Script.
Tests 10 progressive distortion levels to find the "breaking point".

Usage:
    cd backend
    python scripts/distortion_assessment.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
from datetime import datetime
from io import BytesIO
from scipy.spatial.distance import cosine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EMBEDDING_URL = "http://127.0.0.1:5001/encode"
SIMILARITY_THRESHOLD = 0.45


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


def add_gaussian_noise(image, sigma):
    """Add Gaussian noise to image."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def apply_distortion_level(image_bgr, level):
    """
    Apply progressive distortion based on level (1-10).

    Level 1: Original (no distortion)
    Level 2: 10° rotation
    Level 3: 20° rotation
    Level 4: 30° rotation + slight exposure
    Level 5: 30° rotation + moderate exposure + slight noise
    Level 6: 45° rotation + grayscale + slight noise
    Level 7: 60° rotation + grayscale + moderate noise
    Level 8: 90° rotation + grayscale + moderate noise
    Level 9: 120° rotation + extreme exposure + grayscale + heavy noise
    Level 10: 180° rotation + extreme exposure + grayscale + heavy noise
    """
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)
    result = image_bgr.copy()

    if level == 1:
        # No distortion
        return result

    elif level == 2:
        # 10° rotation
        M = cv2.getRotationMatrix2D(center, 10, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    elif level == 3:
        # 20° rotation
        M = cv2.getRotationMatrix2D(center, 20, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    elif level == 4:
        # 30° rotation + slight exposure
        M = cv2.getRotationMatrix2D(center, 30, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.convertScaleAbs(result, alpha=1.1, beta=10)

    elif level == 5:
        # 30° rotation + moderate exposure + slight noise
        M = cv2.getRotationMatrix2D(center, 30, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.convertScaleAbs(result, alpha=1.2, beta=20)
        result = add_gaussian_noise(result, 10)

    elif level == 6:
        # 45° rotation + grayscale + slight noise
        M = cv2.getRotationMatrix2D(center, 45, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        result = add_gaussian_noise(result, 15)

    elif level == 7:
        # 60° rotation + grayscale + moderate noise
        M = cv2.getRotationMatrix2D(center, 60, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        result = add_gaussian_noise(result, 25)

    elif level == 8:
        # 90° rotation + grayscale + moderate noise
        M = cv2.getRotationMatrix2D(center, 90, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        result = add_gaussian_noise(result, 30)

    elif level == 9:
        # 120° rotation + extreme exposure + grayscale + heavy noise
        M = cv2.getRotationMatrix2D(center, 120, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.convertScaleAbs(result, alpha=0.5, beta=-30)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        result = add_gaussian_noise(result, 40)

    elif level == 10:
        # 180° rotation + extreme exposure + grayscale + heavy noise
        M = cv2.getRotationMatrix2D(center, 180, 1.0)
        result = cv2.warpAffine(result, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        result = cv2.convertScaleAbs(result, alpha=0.4, beta=-40)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        result = add_gaussian_noise(result, 50)

    return result


def get_mugshot_path(inmate, static_folder):
    """Get full path to inmate's mugshot."""
    mugshot_path = inmate.mugshot_path
    if not mugshot_path:
        return None

    if mugshot_path.startswith('/static/'):
        full_path = os.path.join(static_folder, mugshot_path[8:])
    elif mugshot_path.startswith('static/'):
        full_path = os.path.join(static_folder, mugshot_path[7:])
    else:
        full_path = os.path.join(static_folder, mugshot_path)

    if os.path.exists(full_path):
        return full_path

    alt_paths = [
        os.path.join(static_folder, 'inmate_images', os.path.basename(mugshot_path)),
    ]
    for alt in alt_paths:
        if os.path.exists(alt):
            return alt

    return None


def match_against_database(query_embedding, inmate_encodings):
    """Find the best match for a query embedding."""
    best_match = None
    best_distance = float('inf')

    for inmate_id, encodings in inmate_encodings.items():
        for enc in encodings:
            dist = cosine(query_embedding, enc)
            if dist < best_distance:
                best_distance = dist
                best_match = inmate_id

    return best_match, best_distance


def main():
    print("=" * 70)
    print("DISTORTION LEVEL ASSESSMENT")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

        # Get test inmates (prioritize TEST- prefixed, fall back to regular)
        test_inmates = Inmate.query.filter(
            Inmate.inmate_id.like('TEST-%')
        ).all()

        if len(test_inmates) < 6:
            # Add some regular inmates if not enough test inmates
            regular = Inmate.query.filter(
                ~Inmate.inmate_id.like('TEST-%'),
                Inmate.face_encoding.isnot(None)
            ).limit(6 - len(test_inmates)).all()
            test_inmates.extend(regular)

        print(f"Testing {len(test_inmates)} subjects")

        # Pre-load all encodings
        all_inmates = Inmate.query.filter(
            db.or_(
                Inmate.face_encoding.isnot(None),
                Inmate.face_encodings_json.isnot(None)
            )
        ).all()

        inmate_encodings = {}
        for inmate in all_inmates:
            encodings = inmate.get_all_encodings()
            if encodings:
                inmate_encodings[inmate.inmate_id] = encodings

        print(f"Loaded encodings for {len(inmate_encodings)} inmates")
        print("=" * 70)

        # Results by level
        level_results = {i: {"correct": 0, "wrong": 0, "no_match": 0, "total": 0}
                        for i in range(1, 11)}

        # Test each subject at each distortion level
        for inmate in test_inmates:
            mugshot_path = get_mugshot_path(inmate, static_folder)
            if not mugshot_path:
                print(f"{inmate.inmate_id}: SKIPPED (no mugshot)")
                continue

            image = cv2.imread(mugshot_path)
            if image is None:
                print(f"{inmate.inmate_id}: SKIPPED (couldn't load)")
                continue

            print(f"\n{inmate.inmate_id} ({inmate.name}):")

            # Test each level
            results_line = []
            breaking_point = None

            for level in range(1, 11):
                level_results[level]["total"] += 1

                # Apply distortion
                distorted = apply_distortion_level(image, level)

                # Get embedding
                query_emb = get_embedding(distorted)
                if query_emb is None:
                    level_results[level]["no_match"] += 1
                    results_line.append("X")
                    continue

                # Match
                matched_id, distance = match_against_database(query_emb, inmate_encodings)

                if distance >= SIMILARITY_THRESHOLD:
                    level_results[level]["no_match"] += 1
                    results_line.append("-")
                    if breaking_point is None:
                        breaking_point = level
                elif matched_id == inmate.inmate_id:
                    level_results[level]["correct"] += 1
                    results_line.append("✓")
                else:
                    level_results[level]["wrong"] += 1
                    results_line.append("!")
                    if breaking_point is None:
                        breaking_point = level

            # Print results
            line = " ".join(f"L{i}:{r}" for i, r in enumerate(results_line, 1))
            print(f"  {line}")
            if breaking_point:
                print(f"  Breaking point: Level {breaking_point}")

        # Summary
        print("\n" + "=" * 70)
        print("DISTORTION LEVEL ACCURACY")
        print("=" * 70)

        level_descriptions = [
            "Original (no distortion)",
            "10° rotation",
            "20° rotation",
            "30° rotation + slight exposure",
            "30° rotation + exposure + noise",
            "45° rotation + grayscale + noise",
            "60° rotation + grayscale + noise",
            "90° rotation + grayscale + noise",
            "120° rotation + extreme + noise",
            "180° rotation + extreme + noise"
        ]

        print(f"\n{'Level':<8} {'Description':<35} {'Accuracy':>10} {'Results':<20}")
        print("-" * 75)

        for level in range(1, 11):
            data = level_results[level]
            if data["total"] > 0:
                accuracy = (data["correct"] / data["total"]) * 100
            else:
                accuracy = 0

            bar = "█" * int(accuracy / 10) + "░" * (10 - int(accuracy / 10))
            desc = level_descriptions[level - 1]
            stats = f"{data['correct']}/{data['total']}"

            print(f"L{level:<7} {desc:<35} {accuracy:>6.1f}%    {bar} {stats}")

        # Overall robustness score (average accuracy across all levels)
        total_correct = sum(level_results[l]["correct"] for l in range(1, 11))
        total_tests = sum(level_results[l]["total"] for l in range(1, 11))
        overall = (total_correct / total_tests * 100) if total_tests > 0 else 0

        print("\n" + "-" * 70)
        print(f"OVERALL ROBUSTNESS: {overall:.1f}%")
        print(f"Total tests: {total_tests}")
        print(f"Correct: {total_correct}")

        # Find recommended threshold
        recommended_level = 10
        for level in range(1, 11):
            data = level_results[level]
            if data["total"] > 0:
                accuracy = (data["correct"] / data["total"]) * 100
                if accuracy < 80:
                    recommended_level = level - 1
                    break

        print(f"\nRECOMMENDED MAX DISTORTION: Level {recommended_level}")
        if recommended_level > 0:
            print(f"  ({level_descriptions[recommended_level - 1]})")

        # Save results
        output_data = {
            "test_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "subjects_tested": len(test_inmates),
            "total_tests": total_tests,
            "overall_accuracy": round(overall, 2),
            "recommended_max_level": recommended_level,
            "level_results": {
                f"level_{l}": {
                    "description": level_descriptions[l - 1],
                    **level_results[l],
                    "accuracy": round((level_results[l]["correct"] / level_results[l]["total"] * 100)
                                     if level_results[l]["total"] > 0 else 0, 2)
                }
                for l in range(1, 11)
            }
        }

        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'distortion_assessment.json'
        )
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
