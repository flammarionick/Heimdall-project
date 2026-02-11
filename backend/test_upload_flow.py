"""
Test the exact flow that upload_recognition uses.
Simulates reading image as bytes and decoding with imdecode.
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

def test_upload_flow():
    app = create_app()

    with app.app_context():
        # Get first inmate with face encoding
        inmate = Inmate.query.filter(Inmate.face_encoding.isnot(None)).first()

        if not inmate:
            print("ERROR: No inmates with face encodings found!")
            return

        print(f"\n=== Testing upload flow for: {inmate.name} ({inmate.inmate_id}) ===")

        stored_encoding = np.array(inmate.face_encoding, dtype=np.float32)
        print(f"Stored encoding dimensions: {len(stored_encoding)}")

        # Load the mugshot image file as BYTES (like upload does)
        mugshot_file = os.path.join('app', inmate.mugshot_path.lstrip('/'))
        print(f"Loading image from: {mugshot_file}")

        if not os.path.exists(mugshot_file):
            print(f"ERROR: File not found!")
            return

        # Method 1: cv2.imread (how admin_api saves and re-reads)
        img_imread = cv2.imread(mugshot_file)
        print(f"\ncv2.imread shape: {img_imread.shape}")

        # Method 2: Read as bytes and decode with imdecode (how upload works)
        with open(mugshot_file, 'rb') as f:
            file_bytes = f.read()

        npimg = np.frombuffer(file_bytes, np.uint8)
        img_imdecode = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        print(f"cv2.imdecode shape: {img_imdecode.shape}")

        # Check if images are identical
        if np.array_equal(img_imread, img_imdecode):
            print("Images from imread and imdecode are IDENTICAL")
        else:
            diff = np.abs(img_imread.astype(float) - img_imdecode.astype(float))
            print(f"Images DIFFER! Max diff: {diff.max()}, Mean diff: {diff.mean()}")

        # Process both through the recognition pipeline
        face_imread = cv2.resize(img_imread, (128, 128))
        face_imdecode = cv2.resize(img_imdecode, (128, 128))

        encoding_imread = extract_hog_3060(face_imread)
        encoding_imdecode = extract_hog_3060(face_imdecode)

        # Compare all three
        dist_stored_vs_imread = cosine(stored_encoding, encoding_imread)
        dist_stored_vs_imdecode = cosine(stored_encoding, encoding_imdecode)
        dist_imread_vs_imdecode = cosine(encoding_imread, encoding_imdecode)

        print(f"\n=== DISTANCE RESULTS ===")
        print(f"Stored vs imread:   {dist_stored_vs_imread:.6f}")
        print(f"Stored vs imdecode: {dist_stored_vs_imdecode:.6f}")
        print(f"imread vs imdecode: {dist_imread_vs_imdecode:.6f}")

        print(f"\nThreshold: 0.15")
        if dist_stored_vs_imdecode < 0.15:
            print(f"PASS: Upload flow would match! ({dist_stored_vs_imdecode:.4f} < 0.15)")
        else:
            print(f"FAIL: Upload flow would NOT match! ({dist_stored_vs_imdecode:.4f} >= 0.15)")

if __name__ == "__main__":
    test_upload_flow()
