#!/usr/bin/env python3
"""
Test multi-face recognition capability.
Creates a composite image with multiple inmate faces and tests recognition.
"""

import os
import sys
import cv2
import numpy as np
import requests
from io import BytesIO

# Configuration
BASE_URL = "http://127.0.0.1:5002"
LOGIN_API = f"{BASE_URL}/auth/api/login"
RECOGNITION_API = f"{BASE_URL}/api/recognition/upload"
MULTI_RECOGNITION_API = f"{BASE_URL}/api/recognition/upload-multi"

# Credentials
USERNAME = "admin"
PASSWORD = "admin123"


def login():
    """Login and return authenticated session."""
    session = requests.Session()
    response = session.post(LOGIN_API, json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        print("[OK] Logged in successfully")
        return session
    else:
        print(f"[ERROR] Login failed: {response.status_code}")
        return None


def create_multiface_image(image_dir, num_faces=3):
    """
    Create a composite image with multiple faces side by side.
    Returns (composite_image, list_of_inmate_ids)
    """
    # Get list of inmate images
    images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    if len(images) < num_faces:
        print(f"[ERROR] Not enough images. Found {len(images)}, need {num_faces}")
        return None, []

    # Select random images
    import random
    selected = random.sample(images, num_faces)

    # Load and resize images
    face_images = []
    inmate_ids = []
    target_size = (200, 200)  # Size for each face

    for img_file in selected:
        img_path = os.path.join(image_dir, img_file)
        img = cv2.imread(img_path)
        if img is not None:
            img_resized = cv2.resize(img, target_size)
            face_images.append(img_resized)
            # Extract inmate ID from filename
            inmate_id = img_file.rsplit('_', 1)[0]
            inmate_ids.append(inmate_id)

    if len(face_images) < num_faces:
        print(f"[ERROR] Could only load {len(face_images)} images")
        return None, []

    # Create horizontal composite
    composite = np.hstack(face_images)

    return composite, inmate_ids


def test_recognition(session, image, expected_ids):
    """Send image to MULTI-FACE recognition API and report results."""
    # Encode image to JPEG
    _, buffer = cv2.imencode('.jpg', image)
    jpg_bytes = buffer.tobytes()

    # Send to MULTI-FACE API
    files = {'file': ('multiface_test.jpg', BytesIO(jpg_bytes), 'image/jpeg')}

    print("\n" + "="*60)
    print("Sending multi-face image to NEW MULTI-FACE API...")
    print(f"Expected inmate IDs in image: {expected_ids}")
    print("="*60)

    response = session.post(MULTI_RECOGNITION_API, files=files, timeout=120)

    print(f"\nResponse status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nAPI Response:")
        print(f"  Status: {data.get('status')}")
        print(f"  Total faces detected: {data.get('total_faces_detected')}")
        print(f"  Matched: {data.get('matched_count')}")
        print(f"  Unmatched: {data.get('unmatched_count')}")
        print(f"  Escaped inmates: {data.get('escaped_count')}")

        if data.get('matches'):
            print(f"\n  MATCHES:")
            matched_ids = []
            for match in data['matches']:
                face_info = match.get('face_info', {})
                print(f"    Face #{face_info.get('face_index')}: {match.get('name')} ({match.get('inmate_id')})")
                print(f"      Confidence: {match.get('confidence')}%")
                print(f"      Status: {match.get('status')}")
                print(f"      BBox: {face_info.get('bbox')}")
                matched_ids.append(match.get('inmate_id'))

            # Check how many expected IDs were found
            found = [eid for eid in expected_ids if eid in matched_ids]
            not_found = [eid for eid in expected_ids if eid not in matched_ids]
            print(f"\n  Expected IDs found: {len(found)}/{len(expected_ids)}")
            if found:
                print(f"    Found: {found}")
            if not_found:
                print(f"    NOT found: {not_found}")

        if data.get('unmatched_faces'):
            print(f"\n  UNMATCHED FACES:")
            for face in data['unmatched_faces']:
                print(f"    Face #{face.get('face_index')}: No match (bbox: {face.get('bbox')})")

        return data
    else:
        print(f"[ERROR] API error: {response.text[:200]}")
        return None


def test_single_faces(session, image_dir, inmate_ids):
    """Test each face individually for comparison."""
    print("\n" + "="*60)
    print("Testing individual faces for comparison...")
    print("="*60)

    for inmate_id in inmate_ids:
        # Find image for this inmate
        images = [f for f in os.listdir(image_dir) if f.startswith(inmate_id)]
        if not images:
            print(f"\n  {inmate_id}: No image found")
            continue

        img_path = os.path.join(image_dir, images[0])
        img = cv2.imread(img_path)

        if img is None:
            continue

        # Resize to match composite face size
        img_resized = cv2.resize(img, (200, 200))

        # Send to API
        _, buffer = cv2.imencode('.jpg', img_resized)
        jpg_bytes = buffer.tobytes()
        files = {'file': ('single_test.jpg', BytesIO(jpg_bytes), 'image/jpeg')}

        response = session.post(RECOGNITION_API, files=files, timeout=60)

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            if 'inmate' in data:
                detected = data['inmate'].get('inmate_id')
                conf = data['inmate'].get('confidence')
                match = "MATCH" if detected == inmate_id else "MISMATCH"
                print(f"\n  {inmate_id}: {status} -> {detected} ({conf}%) [{match}]")
            else:
                print(f"\n  {inmate_id}: {status}")
        else:
            print(f"\n  {inmate_id}: API error {response.status_code}")


def main():
    print("="*60)
    print("MULTI-FACE RECOGNITION TEST")
    print("="*60)

    # Login
    session = login()
    if not session:
        sys.exit(1)

    # Find inmate images directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(script_dir, '..', 'app', 'static', 'inmate_images')

    if not os.path.exists(image_dir):
        print(f"[ERROR] Image directory not found: {image_dir}")
        sys.exit(1)

    # Test with different numbers of faces
    for num_faces in [2, 3, 4]:
        print(f"\n{'='*60}")
        print(f"TEST: {num_faces} faces in single image")
        print(f"{'='*60}")

        # Create composite image
        composite, inmate_ids = create_multiface_image(image_dir, num_faces)

        if composite is None:
            print("[ERROR] Failed to create composite image")
            continue

        print(f"Created composite image: {composite.shape}")
        print(f"Inmates in image: {inmate_ids}")

        # Save composite for inspection
        output_path = os.path.join(script_dir, f'multiface_test_{num_faces}.jpg')
        cv2.imwrite(output_path, composite)
        print(f"Saved test image: {output_path}")

        # Test recognition
        result = test_recognition(session, composite, inmate_ids)

        # Test individual faces for comparison
        test_single_faces(session, image_dir, inmate_ids)

    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    print("""
NEW Multi-Face Recognition System:
- Uses Haar Cascade to detect ALL faces in an image
- Extracts FaceNet embeddings for EACH face separately
- Matches EACH face against the inmate database
- Returns a list of ALL matched persons with bounding boxes

API Endpoints:
- POST /api/recognition/upload-multi  (dedicated multi-face endpoint)
- POST /api/recognition/upload?multi_face=true  (single endpoint with flag)

Response includes:
- total_faces_detected: Number of faces found
- matched_count: Number of faces matched to inmates
- matches: List of all matched inmates with confidence and bbox
- unmatched_faces: List of faces that didn't match anyone
- has_escaped_inmates: Boolean flag for critical alerts
""")


if __name__ == "__main__":
    main()
