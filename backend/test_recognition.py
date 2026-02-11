"""
Quick diagnostic script to test face recognition matching.
Run from backend folder: python test_recognition.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate
from app.utils.hog_features import extract_hog_3060
from scipy.spatial.distance import cosine
import cv2
import numpy as np

def test_recognition():
    app = create_app()

    with app.app_context():
        # Get first inmate with face encoding
        inmate = Inmate.query.filter(Inmate.face_encoding.isnot(None)).first()

        if not inmate:
            print("ERROR: No inmates with face encodings found!")
            return

        print(f"\n=== Testing with inmate: {inmate.name} ({inmate.inmate_id}) ===")
        print(f"Mugshot path: {inmate.mugshot_path}")

        # Check stored encoding
        stored_encoding = np.array(inmate.face_encoding, dtype=np.float32)
        print(f"Stored encoding: {len(stored_encoding)} dimensions")
        print(f"Stored encoding sample (first 5): {stored_encoding[:5]}")

        # Load the mugshot image
        mugshot_file = os.path.join('app', inmate.mugshot_path.lstrip('/'))
        print(f"\nLoading image from: {mugshot_file}")

        if not os.path.exists(mugshot_file):
            print(f"ERROR: Mugshot file not found!")
            return

        # Load and process exactly like upload_recognition does
        img = cv2.imread(mugshot_file)
        if img is None:
            print("ERROR: Could not read image!")
            return

        print(f"Image loaded: {img.shape}")

        # Process exactly like recognition_api.py does (use_detection=False)
        # Just resize to 128x128
        face_resized = cv2.resize(img, (128, 128))
        print(f"Resized to: {face_resized.shape}")

        # Extract HOG features
        new_encoding = extract_hog_3060(face_resized)
        print(f"New encoding: {len(new_encoding)} dimensions")
        print(f"New encoding sample (first 5): {new_encoding[:5]}")

        # Compare
        distance = cosine(stored_encoding, new_encoding)
        similarity = (1 - distance) * 100

        print(f"\n=== RESULTS ===")
        print(f"Cosine distance: {distance:.6f}")
        print(f"Similarity: {similarity:.2f}%")
        print(f"Threshold: 0.15 (85% similarity)")

        if distance < 0.15:
            print(f"✓ MATCH! Distance {distance:.4f} < 0.15")
        else:
            print(f"✗ NO MATCH. Distance {distance:.4f} >= 0.15")

        # Check if encodings are exactly equal
        if np.allclose(stored_encoding, new_encoding, atol=1e-6):
            print("\n✓ Encodings are IDENTICAL (within floating point tolerance)")
        else:
            diff = np.abs(stored_encoding - new_encoding)
            print(f"\n✗ Encodings differ!")
            print(f"  Max difference: {diff.max():.6f}")
            print(f"  Mean difference: {diff.mean():.6f}")
            print(f"  Positions with large diff (>0.01): {np.sum(diff > 0.01)}")

if __name__ == "__main__":
    test_recognition()
