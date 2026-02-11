#!/usr/bin/env python3
"""
Debug script to test a specific image against all inmates.
Usage: python scripts/debug_match.py <path_to_image> [expected_inmate_id]
"""

import os
import sys
import cv2
import numpy as np
import requests
from io import BytesIO
from scipy.spatial.distance import cosine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.inmate import Inmate
from app.extensions import db

EMBEDDING_URL = "http://127.0.0.1:5001/encode"


def get_embedding(image_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', image_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    resp = requests.post(EMBEDDING_URL, files=files, timeout=30)
    if resp.status_code == 200:
        return np.array(resp.json().get('embedding'))
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_match.py <image_path> [expected_inmate_id]")
        print("\nExample:")
        print("  python scripts/debug_match.py /path/to/distorted.jpg CDJ-8F3E0C")
        sys.exit(1)

    image_path = sys.argv[1]
    expected_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Check embedding service
    try:
        requests.get("http://127.0.0.1:5001/health", timeout=5)
    except:
        print("ERROR: Embedding service not running!")
        sys.exit(1)

    # Load image
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        sys.exit(1)

    image = cv2.imread(image_path)
    if image is None:
        print(f"ERROR: Could not read image: {image_path}")
        sys.exit(1)

    print(f"Image loaded: {image.shape}")

    # Get embedding for query image
    print("\nGetting embedding for query image...")
    query_emb = get_embedding(image)
    if query_emb is None:
        print("ERROR: Could not get embedding")
        sys.exit(1)
    print(f"Query embedding: {len(query_emb)} dimensions")

    # Load all inmates
    app = create_app()
    with app.app_context():
        inmates = Inmate.query.filter(
            db.or_(
                Inmate.face_encoding.isnot(None),
                Inmate.face_encodings_json.isnot(None)
            )
        ).all()

        print(f"\nComparing against {len(inmates)} inmates...")
        print("=" * 80)

        results = []
        expected_result = None

        for inmate in inmates:
            encodings = inmate.get_all_encodings()
            if not encodings:
                continue

            # Find minimum distance across all embeddings
            min_dist = float('inf')
            for enc in encodings:
                dist = cosine(query_emb, enc)
                if dist < min_dist:
                    min_dist = dist

            confidence = (1 - min_dist) * 100
            results.append((inmate.inmate_id, inmate.name, min_dist, confidence, len(encodings)))

            if expected_id and inmate.inmate_id == expected_id:
                expected_result = (inmate.inmate_id, inmate.name, min_dist, confidence, len(encodings))

        # Sort by distance
        results.sort(key=lambda x: x[2])

        # Show top 10
        print("\nTop 10 matches:")
        print("-" * 80)
        for i, (iid, name, dist, conf, n_enc) in enumerate(results[:10]):
            marker = " <-- EXPECTED" if expected_id and iid == expected_id else ""
            marker += " <-- TOP MATCH" if i == 0 else ""
            print(f"{i+1:2}. {iid:15} | {name:25} | dist: {dist:.4f} | conf: {conf:.1f}% | {n_enc} enc{marker}")

        if expected_id and expected_result:
            print("\n" + "=" * 80)
            print(f"EXPECTED INMATE ({expected_id}):")
            rank = [r[0] for r in results].index(expected_id) + 1
            print(f"  Rank: #{rank}")
            print(f"  Distance: {expected_result[2]:.4f}")
            print(f"  Confidence: {expected_result[3]:.1f}%")
            print(f"  Embeddings: {expected_result[4]}")

            if rank > 1:
                print(f"\n  Gap from #1: {expected_result[2] - results[0][2]:.4f}")
                print(f"  The system incorrectly matches to: {results[0][0]} ({results[0][1]})")


if __name__ == "__main__":
    main()
