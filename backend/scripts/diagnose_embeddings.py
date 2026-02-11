#!/usr/bin/env python3
"""
Diagnostic script to check if database embeddings match service embeddings.
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
        return np.array(data.get('embedding')), data.get('method')
    return None, None


def main():
    print("=" * 60)
    print("EMBEDDING DIAGNOSTIC")
    print("=" * 60)

    # Connect to database
    db_path = str(backend_dir / 'instance' / 'heimdall.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get first 5 inmates with embeddings
    cursor.execute("""
        SELECT id, inmate_id, name, mugshot_path, face_encodings_json
        FROM inmate
        WHERE face_encodings_json IS NOT NULL
        LIMIT 5
    """)
    inmates = cursor.fetchall()

    print(f"\nChecking {len(inmates)} inmates...\n")

    for db_id, inmate_id, name, mugshot_path, encodings_json in inmates:
        print(f"Inmate: {name} ({inmate_id})")

        # Load database embedding
        try:
            db_emb = json.loads(encodings_json)
            if isinstance(db_emb[0], list):
                db_emb = np.array(db_emb[0])
            else:
                db_emb = np.array(db_emb)
            print(f"  DB embedding: dim={len(db_emb)}, norm={np.linalg.norm(db_emb):.4f}")
            print(f"  DB emb sample: [{db_emb[0]:.4f}, {db_emb[1]:.4f}, {db_emb[2]:.4f}, ...]")
        except Exception as e:
            print(f"  DB embedding error: {e}")
            continue

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

        img_bgr = cv2.imread(str(full_path))
        if img_bgr is None:
            print(f"  Could not read image")
            continue

        # Get fresh embedding from service
        service_emb, method = get_service_embedding(img_bgr)

        if service_emb is None:
            print(f"  Service embedding failed")
            continue

        print(f"  Service embedding: dim={len(service_emb)}, norm={np.linalg.norm(service_emb):.4f}")
        print(f"  Service method: {method}")
        print(f"  Service emb sample: [{service_emb[0]:.4f}, {service_emb[1]:.4f}, {service_emb[2]:.4f}, ...]")

        # Compare
        dist = cosine(db_emb, service_emb)
        print(f"  Cosine distance: {dist:.4f}")

        if dist < 0.4:
            print(f"  MATCH (within threshold)")
        else:
            print(f"  NO MATCH (distance too large)")

        print()

    conn.close()


if __name__ == '__main__':
    main()
