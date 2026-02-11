#!/usr/bin/env python3
"""
Comprehensive Recognition Model Assessment.
Runs ~1050 tests (105 inmates × 10 distortion types).

Usage:
    cd backend
    python scripts/comprehensive_test.py
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


def generate_distortions(image_bgr):
    """Generate 10 distorted versions of an image."""
    distortions = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    # 1. Original
    distortions.append(('original', image_bgr.copy()))

    # 2. Rotate -30°
    M = cv2.getRotationMatrix2D(center, -30, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append(('rotate_-30', rotated))

    # 3. Rotate +30°
    M = cv2.getRotationMatrix2D(center, 30, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append(('rotate_+30', rotated))

    # 4. Rotate 90°
    M = cv2.getRotationMatrix2D(center, 90, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append(('rotate_90', rotated))

    # 5. Rotate 180°
    M = cv2.getRotationMatrix2D(center, 180, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append(('rotate_180', rotated))

    # 6. Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    distortions.append(('grayscale', gray_bgr))

    # 7. Bright exposure
    bright = cv2.convertScaleAbs(image_bgr, alpha=1.5, beta=50)
    distortions.append(('bright', bright))

    # 8. Dark exposure
    dark = cv2.convertScaleAbs(image_bgr, alpha=0.5, beta=-30)
    distortions.append(('dark', dark))

    # 9. Combined: rotate + grayscale + exposure
    M = cv2.getRotationMatrix2D(center, 25, 1.0)
    combined = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    combined = cv2.cvtColor(combined, cv2.COLOR_BGR2GRAY)
    combined = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
    combined = cv2.convertScaleAbs(combined, alpha=0.8, beta=-10)
    distortions.append(('combined', combined))

    # 10. Gaussian blur
    blurred = cv2.GaussianBlur(image_bgr, (7, 7), 0)
    distortions.append(('blur', blurred))

    return distortions


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

    # Try alternative paths
    alt_paths = [
        os.path.join(static_folder, 'inmate_images', os.path.basename(mugshot_path)),
        os.path.join(static_folder, os.path.basename(mugshot_path)),
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
    print("COMPREHENSIVE RECOGNITION MODEL ASSESSMENT")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print(f"Embedding service: OK")
    except:
        print("ERROR: Embedding service not running!")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        static_folder = os.path.join(app.root_path, 'static')

        # Load all inmates with encodings
        inmates = Inmate.query.filter(
            db.or_(
                Inmate.face_encoding.isnot(None),
                Inmate.face_encodings_json.isnot(None)
            )
        ).all()

        print(f"Total inmates with encodings: {len(inmates)}")

        # Pre-load all encodings for faster matching
        inmate_encodings = {}
        for inmate in inmates:
            encodings = inmate.get_all_encodings()
            if encodings:
                inmate_encodings[inmate.inmate_id] = encodings

        print(f"Loaded encodings for {len(inmate_encodings)} inmates")
        print("=" * 70)

        # Results tracking
        results = {
            "test_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_inmates": len(inmates),
            "total_tests": 0,
            "correct_matches": 0,
            "wrong_matches": 0,
            "no_matches": 0,
            "per_distortion": {},
            "problem_inmates": []
        }

        distortion_names = [
            'original', 'rotate_-30', 'rotate_+30', 'rotate_90', 'rotate_180',
            'grayscale', 'bright', 'dark', 'combined', 'blur'
        ]

        for name in distortion_names:
            results["per_distortion"][name] = {
                "correct": 0,
                "wrong": 0,
                "no_match": 0,
                "total": 0
            }

        # Test each inmate
        for idx, inmate in enumerate(inmates):
            mugshot_path = get_mugshot_path(inmate, static_folder)
            if not mugshot_path:
                print(f"[{idx+1}/{len(inmates)}] {inmate.inmate_id}: SKIPPED (no mugshot)")
                continue

            image = cv2.imread(mugshot_path)
            if image is None:
                print(f"[{idx+1}/{len(inmates)}] {inmate.inmate_id}: SKIPPED (couldn't load image)")
                continue

            # Generate distortions
            distortions = generate_distortions(image)
            inmate_failures = []

            status_line = f"[{idx+1}/{len(inmates)}] {inmate.inmate_id}: "
            test_results = []

            for dist_name, dist_img in distortions:
                results["total_tests"] += 1
                results["per_distortion"][dist_name]["total"] += 1

                # Get embedding for distorted image
                query_emb = get_embedding(dist_img)
                if query_emb is None:
                    results["no_matches"] += 1
                    results["per_distortion"][dist_name]["no_match"] += 1
                    test_results.append("X")
                    inmate_failures.append(f"{dist_name}: embedding failed")
                    continue

                # Find best match
                matched_id, distance = match_against_database(query_emb, inmate_encodings)

                if distance >= SIMILARITY_THRESHOLD:
                    # No match (below threshold)
                    results["no_matches"] += 1
                    results["per_distortion"][dist_name]["no_match"] += 1
                    test_results.append("-")
                    inmate_failures.append(f"{dist_name}: no match (dist={distance:.3f})")
                elif matched_id == inmate.inmate_id:
                    # Correct match
                    results["correct_matches"] += 1
                    results["per_distortion"][dist_name]["correct"] += 1
                    test_results.append("+")
                else:
                    # Wrong match
                    results["wrong_matches"] += 1
                    results["per_distortion"][dist_name]["wrong"] += 1
                    test_results.append("!")
                    inmate_failures.append(f"{dist_name}: WRONG (matched {matched_id})")

            # Print status line
            result_str = "".join(test_results)
            correct = result_str.count("+")
            print(f"{status_line}{result_str} ({correct}/10)")

            # Track problem inmates
            if inmate_failures:
                results["problem_inmates"].append({
                    "inmate_id": inmate.inmate_id,
                    "name": inmate.name,
                    "failures": inmate_failures
                })

        # Calculate accuracies
        if results["total_tests"] > 0:
            results["overall_accuracy"] = round(
                (results["correct_matches"] / results["total_tests"]) * 100, 2
            )

        for dist_name in distortion_names:
            dist_data = results["per_distortion"][dist_name]
            if dist_data["total"] > 0:
                dist_data["accuracy"] = round(
                    (dist_data["correct"] / dist_data["total"]) * 100, 2
                )

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total tests: {results['total_tests']}")
        print(f"Correct matches: {results['correct_matches']}")
        print(f"Wrong matches: {results['wrong_matches']}")
        print(f"No matches: {results['no_matches']}")
        print(f"Overall accuracy: {results.get('overall_accuracy', 0)}%")

        print("\n" + "-" * 70)
        print("ACCURACY BY DISTORTION TYPE")
        print("-" * 70)
        for dist_name in distortion_names:
            dist_data = results["per_distortion"][dist_name]
            acc = dist_data.get("accuracy", 0)
            bar = "#" * int(acc / 5) + "." * (20 - int(acc / 5))
            print(f"{dist_name:15} {bar} {acc:5.1f}% ({dist_data['correct']}/{dist_data['total']})")

        # Problem inmates summary
        wrong_match_inmates = [
            p for p in results["problem_inmates"]
            if any("WRONG" in f for f in p["failures"])
        ]
        if wrong_match_inmates:
            print("\n" + "-" * 70)
            print(f"INMATES WITH WRONG MATCHES ({len(wrong_match_inmates)}):")
            print("-" * 70)
            for p in wrong_match_inmates[:10]:  # Show first 10
                wrong_failures = [f for f in p["failures"] if "WRONG" in f]
                print(f"  {p['inmate_id']} ({p['name']}): {len(wrong_failures)} wrong matches")

        # Save results to JSON
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'assessment_report.json'
        )
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to: {output_path}")

        print("\n" + "=" * 70)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
