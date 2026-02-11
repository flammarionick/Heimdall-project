#!/usr/bin/env python3
"""
Direct test of facial recognition with distorted images.
Bypasses API authentication by testing the recognition logic directly.
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
from io import BytesIO
from scipy.spatial.distance import cosine

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

# Embedding service URL
EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"

# Matching threshold
SIMILARITY_THRESHOLD = 0.6


def apply_distortions(image_bgr):
    """Apply various distortions to test robustness."""
    distortions = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    distortions.append((image_bgr.copy(), "original"))

    for angle in [15, 30, -15, -30]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        distortions.append((rotated, f"rotated_{angle}deg"))

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    distortions.append((gray_bgr, "grayscale"))

    bright = cv2.convertScaleAbs(image_bgr, alpha=1.5, beta=50)
    distortions.append((bright, "bright_exposure"))

    dark = cv2.convertScaleAbs(image_bgr, alpha=0.5, beta=-30)
    distortions.append((dark, "dark_exposure"))

    M = cv2.getRotationMatrix2D(center, 25, 1.0)
    rotated_gray = cv2.warpAffine(gray_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append((rotated_gray, "rotated_25deg_grayscale"))

    M = cv2.getRotationMatrix2D(center, -20, 1.0)
    rotated_bright = cv2.warpAffine(bright, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append((rotated_bright, "rotated_-20deg_bright"))

    extreme = cv2.convertScaleAbs(rotated_gray, alpha=1.3, beta=40)
    distortions.append((extreme, "extreme_all_distortions"))

    return distortions


def get_embedding(image_bgr):
    """Get embedding from embedding service."""
    try:
        _, buffer = cv2.imencode('.jpg', image_bgr)
        jpg_bytes = buffer.tobytes()
        files = {'image': ('face.jpg', BytesIO(jpg_bytes), 'image/jpeg')}
        response = requests.post(EMBEDDING_SERVICE_URL, files=files, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return np.array(data.get('embedding')), data.get('method', 'unknown')
        return None, None
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None, None


def match_against_inmates(query_embedding, inmate_encodings):
    """
    Match query embedding against all inmates.
    Returns list of (inmate_id, name, confidence, distance) sorted by confidence.
    """
    matches = []

    for inmate_id, name, encodings in inmate_encodings:
        min_dist = float('inf')

        # Compare against ALL embeddings for this inmate
        for encoding in encodings:
            dist = cosine(query_embedding, encoding)
            if dist < min_dist:
                min_dist = dist

        if min_dist < SIMILARITY_THRESHOLD:
            confidence = (1 - min_dist) * 100
            matches.append((inmate_id, name, confidence, min_dist))

    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches[:5]


def load_inmate_encodings(app):
    """Load all inmate encodings from database."""
    encodings_list = []

    with app.app_context():
        inmates = Inmate.query.filter(
            db.or_(
                Inmate.face_encoding.isnot(None),
                Inmate.face_encodings_json.isnot(None)
            )
        ).all()

        for inmate in inmates:
            encodings = inmate.get_all_encodings()
            if encodings:
                encodings_list.append((inmate.inmate_id, inmate.name, encodings))

    return encodings_list


def main():
    print("=" * 70)
    print("DIRECT DISTORTED IMAGE RECOGNITION TEST")
    print("=" * 70)

    # Check embedding service
    try:
        response = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print(f"Embedding Service: OK ({response.json()})")
    except:
        print("ERROR: Embedding service not running!")
        sys.exit(1)

    # Create Flask app
    app = create_app()

    # Load inmate encodings
    print("\nLoading inmate encodings from database...")
    inmate_encodings = load_inmate_encodings(app)
    total_encodings = sum(len(enc) for _, _, enc in inmate_encodings)
    print(f"Loaded {len(inmate_encodings)} inmates with {total_encodings} total embeddings")

    if not inmate_encodings:
        print("ERROR: No inmate encodings found!")
        sys.exit(1)

    # Find test images
    static_folder = os.path.join(app.root_path, 'static')
    inmate_images_dir = os.path.join(static_folder, 'inmate_images')

    image_files = [f for f in os.listdir(inmate_images_dir) if f.endswith(('.jpg', '.png', '.jpeg'))][:3]

    if not image_files:
        print("ERROR: No inmate images found!")
        sys.exit(1)

    print(f"\nTesting with {len(image_files)} inmate image(s)")

    total_tests = 0
    passed_tests = 0

    for img_file in image_files:
        inmate_id = img_file.rsplit('_', 1)[0]
        img_path = os.path.join(inmate_images_dir, img_file)

        print(f"\n{'=' * 70}")
        print(f"Testing Inmate: {inmate_id}")
        print(f"Image: {img_file}")
        print("=" * 70)

        image = cv2.imread(img_path)
        if image is None:
            print(f"  Failed to load image: {img_path}")
            continue

        distortions = apply_distortions(image)

        for distorted_img, distortion_name in distortions:
            total_tests += 1

            # Get embedding for distorted image
            embedding, method = get_embedding(distorted_img)

            if embedding is None:
                print(f"  [FAIL] | {distortion_name:30} | No embedding generated")
                continue

            # Match against inmates
            matches = match_against_inmates(embedding, inmate_encodings)

            if matches:
                top_id, top_name, top_conf, top_dist = matches[0]

                # Check if correct inmate is in top 3
                top_3_ids = [m[0] for m in matches[:3]]
                success = inmate_id in top_3_ids

                if success:
                    passed_tests += 1

                status = "[PASS]" if success else "[FAIL]"
                match_str = ", ".join([f"{m[0]}({m[2]:.0f}%)" for m in matches[:3]])
                print(f"  {status} | {distortion_name:30} | Top: {top_id:12} ({top_conf:.0f}%) | {match_str}")
            else:
                print(f"  [FAIL] | {distortion_name:30} | No matches found (method: {method})")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    success_rate = (passed_tests/total_tests*100) if total_tests > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    print("=" * 70)

    if passed_tests == total_tests:
        print("\nALL TESTS PASSED! Recognition is robust against distortions.")
    elif success_rate >= 80:
        print("\nGOOD: Most tests passed. Recognition is reasonably robust.")
    elif success_rate >= 50:
        print("\nMODERATE: Some improvements may be needed.")
    else:
        print("\nWARNING: Many tests failed. Recognition needs improvement.")


if __name__ == "__main__":
    main()
