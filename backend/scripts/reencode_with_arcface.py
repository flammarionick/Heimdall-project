#!/usr/bin/env python3
"""
Re-encode All Inmates with ArcFace Model

This script re-generates face embeddings for all existing inmates using
InsightFace's ArcFace model (buffalo_l), which is trained on 600K+ identities
with much better noise robustness than FaceNet.

Usage:
    cd backend
    python scripts/reencode_with_arcface.py

WARNING: This will update all face_encoding fields in the database.
         A backup is automatically created before making changes.
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
import cv2
from PIL import Image

# Suppress NumPy warnings
import warnings
warnings.filterwarnings('ignore')

try:
    import onnxruntime as ort
except ImportError:
    print("Error: onnxruntime not installed")
    print("Run: pip install onnxruntime")
    sys.exit(1)


def backup_database(db_path: str) -> str:
    """Create backup of database."""
    backup_path = db_path.replace('.db', f'_backup_arcface_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def preprocess_face_for_arcface(img_bgr, target_size=(112, 112)):
    """
    Preprocess a face image for ArcFace embedding extraction.
    ArcFace expects 112x112 RGB images normalized to [-1, 1].
    """
    # Resize to 112x112
    img_resized = cv2.resize(img_bgr, target_size)

    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)

    # Transpose to CHW format
    img_transposed = img_rgb.transpose(2, 0, 1)

    # Normalize to [-1, 1] (ArcFace uses (pixel - 127.5) / 127.5)
    img_normalized = (img_transposed.astype(np.float32) - 127.5) / 127.5

    # Add batch dimension
    img_batch = np.expand_dims(img_normalized, axis=0)

    return img_batch


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Re-encode inmates with ArcFace model')
    parser.add_argument('--db', type=str, default='instance/heimdall.db',
                        help='Path to database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--inmate-id', type=int, default=None,
                        help='Re-encode specific inmate only')

    args = parser.parse_args()

    print("=" * 60)
    print("HEIMDALL FACE RECOGNITION - ARCFACE RE-ENCODING")
    print("=" * 60)
    print()

    # Load ArcFace recognition model directly (skip face detection)
    print("Loading ArcFace recognition model...")
    print("This model is trained on 600K+ identities with superior noise robustness.")
    print()

    # Path to the ArcFace recognition model
    model_path = os.path.expanduser("~/.insightface/models/buffalo_l/w600k_r50.onnx")

    if not os.path.exists(model_path):
        print(f"ArcFace model not found at: {model_path}")
        print("Downloading model...")
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0)
        del app

    # Load ONNX model directly for embedding extraction
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    print(f"ArcFace model loaded: {model_path}")
    print(f"Input shape: {session.get_inputs()[0].shape}")
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

    # Get all inmates
    if args.inmate_id:
        cursor.execute("SELECT id, name, mugshot_path FROM inmate WHERE id = ?", (args.inmate_id,))
    else:
        cursor.execute("SELECT id, name, mugshot_path FROM inmate")

    inmates = cursor.fetchall()
    print(f"Found {len(inmates)} inmates to re-encode")
    print()

    # Process each inmate
    success_count = 0
    fail_count = 0

    for inmate_id, name, mugshot_path in inmates:
        print(f"Processing: {name} (ID: {inmate_id})")

        if not mugshot_path:
            print(f"  WARNING: No mugshot path, skipping")
            fail_count += 1
            continue

        # Load image - mugshot_path is like "/static/inmate_images/XX-123456_1.jpg"
        clean_path = mugshot_path.lstrip('/')

        # Try multiple possible locations
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
            # Load image using OpenCV
            img_bgr = cv2.imread(str(full_path))

            if img_bgr is None:
                print(f"  ERROR: Could not read image: {full_path}")
                fail_count += 1
                continue

            # Preprocess face image for ArcFace (112x112 normalized)
            # Since these are already cropped face images, we skip face detection
            img_input = preprocess_face_for_arcface(img_bgr)

            # Extract embedding using ONNX model
            embedding = session.run([output_name], {input_name: img_input})[0][0]

            # Normalize embedding (L2 normalization)
            embedding = embedding / np.linalg.norm(embedding)

            print(f"  Image processed: {img_bgr.shape}")
            print(f"  Embedding dimension: {len(embedding)}")

            # Convert to JSON format
            embedding_json = json.dumps(embedding.tolist())
            embedding_blob = embedding.astype(np.float32).tobytes()

            if args.dry_run:
                print(f"  DRY RUN: Would update embedding")
            else:
                # Update database
                cursor.execute("""
                    UPDATE inmate
                    SET face_encoding = ?,
                        face_encodings_json = ?
                    WHERE id = ?
                """, (embedding_blob, embedding_json, inmate_id))
                conn.commit()
                print(f"  Updated embedding successfully")

            success_count += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1

    conn.close()

    # Summary
    print()
    print("=" * 60)
    print("RE-ENCODING COMPLETE")
    print("=" * 60)
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(inmates)}")

    if args.dry_run:
        print()
        print("[DRY RUN] No changes were made to the database.")
    else:
        print()
        print("Database updated with ArcFace embeddings!")
        print()
        print("IMPORTANT NEXT STEPS:")
        print("  1. Update embedding_service.py to use ArcFace for queries")
        print("  2. Test noise accuracy with the new embeddings")


if __name__ == '__main__':
    main()
