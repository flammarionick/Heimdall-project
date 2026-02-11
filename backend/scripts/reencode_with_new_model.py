#!/usr/bin/env python3
"""
Re-encode All Inmates with New Model

This script re-generates face embeddings for all existing inmates using
the newly trained model. This is REQUIRED after deploying a retrained model
because embeddings from different models are not compatible.

Usage:
    cd backend
    python scripts/reencode_with_new_model.py --model models/heimdall_facenet_retrained.pt

WARNING: This will update all face_encoding fields in the database.
         A backup is automatically created before making changes.
"""

import os
import sys
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

try:
    from facenet_pytorch import MTCNN
except ImportError:
    print("Error: facenet_pytorch not installed")
    sys.exit(1)


def load_model(model_path: str, device: torch.device):
    """Load the retrained model."""
    print(f"Loading model: {model_path}")

    if model_path.endswith('.pt'):
        # TorchScript model
        model = torch.jit.load(model_path, map_location=device)
    else:
        # State dict
        from facenet_pytorch import InceptionResnetV1
        model = InceptionResnetV1(pretrained=None, classify=False)
        model.load_state_dict(torch.load(model_path, map_location=device))
        model = model.to(device)

    model.eval()
    return model


def get_embedding(model, face_image: np.ndarray, device: torch.device) -> np.ndarray:
    """Generate embedding for a face image."""
    # Preprocess
    if isinstance(face_image, Image.Image):
        face_image = np.array(face_image)

    # Ensure RGB
    if len(face_image.shape) == 2:
        face_image = np.stack([face_image] * 3, axis=-1)
    elif face_image.shape[-1] == 4:
        face_image = face_image[:, :, :3]

    # Resize to 160x160
    from PIL import Image as PILImage
    img = PILImage.fromarray(face_image)
    img = img.resize((160, 160), PILImage.BILINEAR)
    face_image = np.array(img)

    # Normalize
    face_tensor = torch.from_numpy(face_image).permute(2, 0, 1).float()
    face_tensor = (face_tensor - 127.5) / 128.0
    face_tensor = face_tensor.unsqueeze(0).to(device)

    # Get embedding
    with torch.no_grad():
        embedding = model(face_tensor)
        embedding = F.normalize(embedding, p=2, dim=1)

    return embedding.cpu().numpy()[0]


def backup_database(db_path: str) -> str:
    """Create backup of database."""
    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def main():
    parser = argparse.ArgumentParser(description='Re-encode inmates with new model')
    parser.add_argument('--model', type=str, required=True,
                        help='Path to retrained model')
    parser.add_argument('--db', type=str, default='instance/heimdall.db',
                        help='Path to database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--inmate-id', type=int, default=None,
                        help='Re-encode specific inmate only')

    args = parser.parse_args()

    # Setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Load model
    model = load_model(args.model, device)

    # Initialize MTCNN for face detection
    mtcnn = MTCNN(
        image_size=160,
        margin=20,
        min_face_size=20,
        thresholds=[0.6, 0.7, 0.7],
        device=device
    )

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
    print(f"\nFound {len(inmates)} inmates to re-encode")

    # Process each inmate
    success_count = 0
    fail_count = 0

    for inmate_id, name, mugshot_path in inmates:
        print(f"\nProcessing: {name} (ID: {inmate_id})")

        if not mugshot_path:
            print(f"  WARNING: No mugshot path, skipping")
            fail_count += 1
            continue

        # Load image - mugshot_path is like "/static/inmate_images/XX-123456_1.jpg"
        # The actual file is at backend/app/static/inmate_images/...
        clean_path = mugshot_path.lstrip('/')

        # Try multiple possible locations
        possible_paths = [
            backend_dir / 'app' / clean_path,  # backend/app/static/inmate_images/...
            backend_dir / clean_path,          # backend/static/inmate_images/...
            backend_dir / 'app' / 'static' / 'inmate_images' / Path(mugshot_path).name,  # Just filename
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
            # Load and detect face
            img = Image.open(full_path).convert('RGB')

            # Detect face
            face, prob = mtcnn(img, return_prob=True)

            if face is None:
                print(f"  WARNING: No face detected, using full image")
                face_img = np.array(img)
            else:
                print(f"  Face detected with confidence: {prob:.2%}")
                # Convert tensor back to numpy for embedding
                face_img = ((face.permute(1, 2, 0).numpy() * 128) + 127.5).astype(np.uint8)

            # Generate embedding
            embedding = get_embedding(model, face_img, device)

            # Convert to JSON format
            embedding_json = json.dumps(embedding.tolist())
            embedding_blob = embedding.tobytes()

            if args.dry_run:
                print(f"  DRY RUN: Would update embedding (dim={len(embedding)})")
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
            fail_count += 1

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("RE-ENCODING COMPLETE")
    print("=" * 60)
    print(f"  Successful: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(inmates)}")

    if args.dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
    else:
        print("\nDatabase updated. Backup saved.")
        print("\nIMPORTANT: Restart the embedding service to use the new model.")


if __name__ == '__main__':
    main()
