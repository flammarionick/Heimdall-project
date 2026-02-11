#!/usr/bin/env python3
"""
Debug test to understand why comprehensive test is failing.
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

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"


def get_service_embedding(img_bgr):
    """Get embedding from service."""
    _, buffer = cv2.imencode('.jpg', img_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}

    resp = requests.post(EMBEDDING_SERVICE_URL, files=files, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        return np.array(data.get('embedding'))
    return None


def main():
    print("=" * 60)
    print("DEBUG MATCHING TEST")
    print("=" * 60)

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

    # Test with first 3 inmates
    test_inmates = list(inmate_embeddings.keys())[:3]

    for inmate_id in test_inmates:
        data = inmate_embeddings[inmate_id]
        mugshot_path = data['mugshot_path']
        name = data['name']

        print(f"\n{'='*60}")
        print(f"Testing: {name} ({inmate_id})")

        # Load image
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
            print(f"  Image not found: {mugshot_path}")
            continue

        img = cv2.imread(str(full_path))
        if img is None:
            continue

        # Get query embedding from service
        query_emb = get_service_embedding(img)
        if query_emb is None:
            print("  Service failed")
            continue

        # Find best match in database
        best_match = None
        best_distance = float('inf')
        distances = []

        for other_id, other_data in inmate_embeddings.items():
            for emb in other_data['embeddings']:
                dist = cosine(query_emb, emb)
                distances.append((other_id, other_data['name'], dist))
                if dist < best_distance:
                    best_distance = dist
                    best_match = other_id

        # Sort by distance
        distances.sort(key=lambda x: x[2])

        # Print top 5 matches
        print(f"\nTop 5 matches:")
        for i, (match_id, match_name, dist) in enumerate(distances[:5]):
            marker = "<-- SELF" if match_id == inmate_id else ""
            print(f"  {i+1}. {match_name} ({match_id}): dist={dist:.4f} {marker}")

        # Check result
        print(f"\nBest match: {best_match}, distance: {best_distance:.4f}")
        print(f"Expected: {inmate_id}")

        if best_match == inmate_id and best_distance < 0.4:
            print("RESULT: CORRECT")
        else:
            if best_match != inmate_id:
                print("RESULT: WRONG PERSON MATCHED")
            else:
                print("RESULT: DISTANCE TOO LARGE")

    conn.close()


if __name__ == '__main__':
    main()
