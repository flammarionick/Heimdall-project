#!/usr/bin/env python3
"""
Re-encode All Inmates Using Embedding Service (With Face Alignment)

This script re-generates face embeddings using the embedding service which
applies MTCNN face detection and alignment before ArcFace encoding.

Prerequisites:
    1. Start the embedding service: python app/utils/embedding_service.py
    2. Then run: python scripts/reencode_with_alignment.py

This ensures database embeddings match the alignment used at query time.
"""

import os
import sys
import json
import shutil
import requests
from datetime import datetime
from pathlib import Path
from io import BytesIO

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np

import warnings
warnings.filterwarnings('ignore')

EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"


def backup_database(db_path: str) -> str:
    """Create backup of database."""
    backup_path = db_path.replace('.db', f'_backup_aligned_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def get_embedding_from_service(img_bgr):
    """Get embedding from the embedding service (with alignment)."""
    _, buffer = cv2.imencode('.jpg', img_bgr)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}

    try:
        resp = requests.post(EMBEDDING_SERVICE_URL, files=files, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            emb = data.get('embedding')
            method = data.get('method', 'unknown')
            if emb:
                return np.array(emb), method
    except Exception as e:
        print(f"  Service error: {e}")

    return None, None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Re-encode inmates with aligned ArcFace via service')
    parser.add_argument('--db', type=str, default='instance/heimdall.db', help='Path to database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    print("=" * 60)
    print("RE-ENCODE INMATES WITH ALIGNED ARCFACE")
    print("=" * 60)
    print()

    # Check if embedding service is running
    try:
        health = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if health.status_code != 200:
            print("ERROR: Embedding service not responding")
            print("Start it with: python app/utils/embedding_service.py")
            sys.exit(1)
        print("Embedding service: OK")
        print(f"Service info: {health.json()}")
    except:
        print("ERROR: Embedding service not running")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    print()

    # Connect to database
    import sqlite3
    db_path = str(backend_dir / args.db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    # Backup database
    if not args.dry_run:
        backup_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, inmate_id, name, mugshot_path FROM inmate")
    inmates = cursor.fetchall()
    print(f"Found {len(inmates)} inmates to re-encode")
    print()

    success_count = 0
    fail_count = 0
    alignment_stats = {'5point': 0, '2point': 0, 'direct': 0}

    for db_id, inmate_id, name, mugshot_path in inmates:
        print(f"Processing: {name} ({inmate_id})")

        if not mugshot_path:
            print(f"  WARNING: No mugshot path, skipping")
            fail_count += 1
            continue

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
            print(f"  ERROR: Image not found: {mugshot_path}")
            fail_count += 1
            continue

        try:
            img_bgr = cv2.imread(str(full_path))

            if img_bgr is None:
                print(f"  ERROR: Could not read image")
                fail_count += 1
                continue

            # Get embedding from service (with alignment)
            embedding, method = get_embedding_from_service(img_bgr)

            if embedding is None:
                print(f"  ERROR: Service returned no embedding")
                fail_count += 1
                continue

            # Track alignment method
            if '5point' in method:
                alignment_stats['5point'] += 1
            elif '2point' in method:
                alignment_stats['2point'] += 1
            else:
                alignment_stats['direct'] += 1

            print(f"  Method: {method}, Embedding dim: {len(embedding)}")

            embedding_json = json.dumps(embedding.tolist())
            embedding_blob = embedding.astype(np.float32).tobytes()

            if args.dry_run:
                print(f"  DRY RUN: Would update embedding")
            else:
                cursor.execute("""
                    UPDATE inmate
                    SET face_encoding = ?,
                        face_encodings_json = ?
                    WHERE id = ?
                """, (embedding_blob, embedding_json, db_id))
                conn.commit()
                print(f"  Updated successfully")

            success_count += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            fail_count += 1

    conn.close()

    print()
    print("=" * 60)
    print("RE-ENCODING COMPLETE")
    print("=" * 60)
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(inmates)}")
    print()
    print("Alignment methods used:")
    print(f"  5-point alignment: {alignment_stats['5point']}")
    print(f"  2-point alignment: {alignment_stats['2point']}")
    print(f"  Direct (no alignment): {alignment_stats['direct']}")

    if args.dry_run:
        print()
        print("[DRY RUN] No changes were made.")


if __name__ == '__main__':
    main()
