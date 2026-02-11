#!/usr/bin/env python3
"""
Test facial recognition with distorted images.

This script:
1. Takes an inmate's mugshot
2. Applies various distortions (rotation, B&W, exposure changes)
3. Tests recognition against the API
4. Reports success/failure for each distortion type

Usage:
    cd backend
    python scripts/test_distorted_recognition.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import base64
from io import BytesIO

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API endpoints
RECOGNITION_API = "http://127.0.0.1:5002/api/recognition/upload"

def apply_distortions(image_bgr):
    """
    Apply various distortions to test robustness.
    Returns list of (distorted_image, distortion_name) tuples.
    """
    distortions = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    # Original (control)
    distortions.append((image_bgr.copy(), "original"))

    # Rotations
    for angle in [15, 30, -15, -30]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        distortions.append((rotated, f"rotated_{angle}deg"))

    # Grayscale (B&W)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    distortions.append((gray_bgr, "grayscale"))

    # Increased exposure (brighter)
    bright = cv2.convertScaleAbs(image_bgr, alpha=1.5, beta=50)
    distortions.append((bright, "bright_exposure"))

    # Decreased exposure (darker)
    dark = cv2.convertScaleAbs(image_bgr, alpha=0.5, beta=-30)
    distortions.append((dark, "dark_exposure"))

    # Combined: rotated + grayscale
    M = cv2.getRotationMatrix2D(center, 25, 1.0)
    rotated_gray = cv2.warpAffine(gray_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append((rotated_gray, "rotated_25deg_grayscale"))

    # Combined: rotated + bright
    M = cv2.getRotationMatrix2D(center, -20, 1.0)
    rotated_bright = cv2.warpAffine(bright, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append((rotated_bright, "rotated_-20deg_bright"))

    # Extreme: rotated + grayscale + exposure
    extreme = cv2.convertScaleAbs(rotated_gray, alpha=1.3, beta=40)
    distortions.append((extreme, "extreme_all_distortions"))

    return distortions


def test_recognition(image_bgr, expected_inmate_id):
    """
    Send image to recognition API and check if correct inmate is identified.
    Returns (success, top_match_id, confidence, all_suspects).
    """
    try:
        # Convert to JPEG bytes
        _, buffer = cv2.imencode('.jpg', image_bgr)
        jpg_bytes = buffer.tobytes()

        # Send to recognition API
        files = {'image': ('test.jpg', BytesIO(jpg_bytes), 'image/jpeg')}
        response = requests.post(RECOGNITION_API, files=files, timeout=30)

        if response.status_code == 200:
            data = response.json()
            suspects = data.get('suspects', [])

            if suspects:
                top_match = suspects[0]
                top_id = top_match.get('id', '')
                confidence = top_match.get('confidence', 0)

                # Check if expected inmate is in top 3
                top_3_ids = [s.get('id', '') for s in suspects[:3]]
                success = expected_inmate_id in top_3_ids

                return success, top_id, confidence, suspects[:3]
            else:
                return False, None, 0, []
        else:
            print(f"  API error: {response.status_code} - {response.text[:100]}")
            return False, None, 0, []

    except requests.exceptions.ConnectionError:
        print("  ERROR: Backend API not running!")
        return False, None, 0, []
    except Exception as e:
        print(f"  Error: {e}")
        return False, None, 0, []


def main():
    print("=" * 70)
    print("DISTORTED IMAGE RECOGNITION TEST")
    print("=" * 70)

    # Check API availability
    try:
        response = requests.get("http://127.0.0.1:5002/health", timeout=5)
        print("Recognition API: OK")
    except:
        print("ERROR: Backend API not running on port 5002!")
        print("Start it with: cd backend && python run.py")
        sys.exit(1)

    # Check embedding service
    try:
        response = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print("Embedding Service: OK")
    except:
        print("ERROR: Embedding service not running on port 5001!")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    # Find test images
    static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'static')
    inmate_images_dir = os.path.join(static_folder, 'inmate_images')

    if not os.path.exists(inmate_images_dir):
        print(f"ERROR: Inmate images directory not found: {inmate_images_dir}")
        sys.exit(1)

    # Get first few inmate images for testing
    image_files = [f for f in os.listdir(inmate_images_dir) if f.endswith(('.jpg', '.png', '.jpeg'))][:3]

    if not image_files:
        print("ERROR: No inmate images found!")
        sys.exit(1)

    print(f"\nTesting with {len(image_files)} inmate image(s)")

    total_tests = 0
    passed_tests = 0

    for img_file in image_files:
        # Extract inmate ID from filename (e.g., "AA-9E4092_1.jpg" -> "AA-9E4092")
        inmate_id = img_file.rsplit('_', 1)[0]
        img_path = os.path.join(inmate_images_dir, img_file)

        print(f"\n{'=' * 70}")
        print(f"Testing Inmate: {inmate_id}")
        print(f"Image: {img_file}")
        print("=" * 70)

        # Load image
        image = cv2.imread(img_path)
        if image is None:
            print(f"  Failed to load image: {img_path}")
            continue

        # Generate distortions
        distortions = apply_distortions(image)

        for distorted_img, distortion_name in distortions:
            total_tests += 1
            success, top_id, confidence, suspects = test_recognition(distorted_img, inmate_id)

            status = "[PASS]" if success else "[FAIL]"
            if success:
                passed_tests += 1

            suspect_ids = [f"{s.get('id')}({s.get('confidence', 0):.0f}%)" for s in suspects]

            print(f"  {status} | {distortion_name:30} | Top: {top_id or 'None':12} ({confidence:.0f}%) | {', '.join(suspect_ids) or 'None'}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%")
    print("=" * 70)

    if passed_tests == total_tests:
        print("\nALL TESTS PASSED! Recognition is robust against distortions.")
    elif passed_tests > total_tests * 0.8:
        print("\nGOOD: Most tests passed. Recognition is reasonably robust.")
    else:
        print("\nWARNING: Many tests failed. Recognition may need further improvement.")


if __name__ == "__main__":
    main()
