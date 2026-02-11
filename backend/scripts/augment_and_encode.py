#!/usr/bin/env python3
"""
Augment inmate mugshots and generate multiple embeddings for robust recognition.

This script:
1. Loads all inmates from the database
2. For each inmate's mugshot, generates augmented versions including:
   - Rotations (-30°, -15°, +15°, +30°)
   - Brightness variations (darker, brighter, high/low contrast)
   - Grayscale conversions
   - Gaussian noise at multiple levels (10, 20, 30, 50 sigma)
   - Combined distortions (noise+rotation, noise+grayscale, noise+dark)
   - Gaussian blur and blur+noise combinations
3. Encodes all augmented versions using the embedding service
4. Stores multiple embeddings in the database for robust matching

The noise augmentations are critical for improving recognition accuracy on
noisy surveillance camera feeds (previously only 3.81% accuracy on noise_30).

Usage:
    cd backend
    python scripts/augment_and_encode.py

Requirements:
    - Embedding service must be running on port 5001
    - Database must be accessible
"""

import os
import sys
import cv2
import numpy as np
import requests
import base64
import json
from io import BytesIO
from PIL import Image

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

# Embedding service URL
EMBEDDING_SERVICE_URL = "http://127.0.0.1:5001/encode"

# Augmentation settings
ROTATION_ANGLES = [-30, -15, 0, 15, 30]  # Degrees
BRIGHTNESS_VARIATIONS = [
    ('original', 1.0, 0),
    ('darker', 0.7, -20),
    ('brighter', 1.3, 30),
    ('high_contrast', 1.5, 0),
    ('low_contrast', 0.6, 50),
]

# Gaussian noise sigma levels (higher = more noise)
NOISE_LEVELS = [
    ('noise_light', 10),    # Light noise
    ('noise_medium', 20),   # Medium noise
    ('noise_heavy', 30),    # Heavy noise (matches test conditions)
    ('noise_extreme', 50),  # Extreme noise for robustness
]


def add_gaussian_noise(image_bgr, sigma):
    """
    Add Gaussian noise to an image.

    Args:
        image_bgr: BGR numpy array
        sigma: Standard deviation of the Gaussian noise

    Returns:
        Noisy image as BGR numpy array
    """
    noise = np.random.normal(0, sigma, image_bgr.shape).astype(np.float32)
    noisy = np.clip(image_bgr.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def generate_augmentations(image_bgr):
    """
    Generate augmented versions of an image.

    Args:
        image_bgr: BGR numpy array

    Returns:
        List of (augmented_image_bgr, name) tuples
    """
    augmentations = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    # Original
    augmentations.append((image_bgr.copy(), 'original'))

    # Rotations (skip 0 as it's already added as original)
    for angle in ROTATION_ANGLES:
        if angle == 0:
            continue
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append((rotated, f'rotate_{angle}'))

    # Brightness variations (skip original as already added)
    for name, alpha, beta in BRIGHTNESS_VARIATIONS:
        if name == 'original':
            continue
        adjusted = cv2.convertScaleAbs(image_bgr, alpha=alpha, beta=beta)
        augmentations.append((adjusted, name))

    # Grayscale (converted back to BGR)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmentations.append((gray_bgr, 'grayscale'))

    # Rotated + grayscale combinations for extreme robustness
    for angle in [-15, 15]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(gray_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append((rotated, f'gray_rotate_{angle}'))

    # Gaussian noise augmentations (critical for noisy image robustness)
    for name, sigma in NOISE_LEVELS:
        noisy = add_gaussian_noise(image_bgr, sigma)
        augmentations.append((noisy, name))

    # Combined: noise + rotation (common real-world scenario)
    for sigma in [20, 30]:
        noisy = add_gaussian_noise(image_bgr, sigma)
        for angle in [-15, 15]:
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            noisy_rotated = cv2.warpAffine(noisy, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            augmentations.append((noisy_rotated, f'noise_{sigma}_rotate_{angle}'))

    # Combined: noise + grayscale (surveillance camera scenario)
    for sigma in [20, 30]:
        noisy = add_gaussian_noise(gray_bgr, sigma)
        augmentations.append((noisy, f'gray_noise_{sigma}'))

    # Combined: noise + darker exposure (low-light noisy camera)
    dark_noisy = cv2.convertScaleAbs(image_bgr, alpha=0.7, beta=-20)
    dark_noisy = add_gaussian_noise(dark_noisy, 25)
    augmentations.append((dark_noisy, 'dark_noisy'))

    # Gaussian blur (soft focus / motion blur simulation)
    blurred = cv2.GaussianBlur(image_bgr, (7, 7), 0)
    augmentations.append((blurred, 'blur'))

    # Combined: blur + noise (degraded camera quality)
    blur_noisy = cv2.GaussianBlur(image_bgr, (5, 5), 0)
    blur_noisy = add_gaussian_noise(blur_noisy, 20)
    augmentations.append((blur_noisy, 'blur_noisy'))

    return augmentations


def encode_image(image_bgr):
    """
    Send image to embedding service and get 512-dim embedding.

    Args:
        image_bgr: BGR numpy array

    Returns:
        List of 512 floats, or None if encoding fails
    """
    try:
        # Convert to JPEG bytes
        _, buffer = cv2.imencode('.jpg', image_bgr)
        jpg_bytes = buffer.tobytes()

        # Send to embedding service
        files = {'image': ('face.jpg', BytesIO(jpg_bytes), 'image/jpeg')}
        response = requests.post(EMBEDDING_SERVICE_URL, files=files, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return data.get('embedding')
        else:
            print(f"    Encoding failed: {response.status_code} - {response.text[:100]}")
            return None

    except requests.exceptions.ConnectionError:
        print("    ERROR: Embedding service not running. Start it with: python app/utils/embedding_service.py")
        return None
    except Exception as e:
        print(f"    Encoding error: {e}")
        return None


def process_inmate(inmate, static_folder):
    """
    Process a single inmate: generate augmentations and encode them.

    Args:
        inmate: Inmate model instance
        static_folder: Path to static folder for mugshot images

    Returns:
        List of embeddings, or None if processing fails
    """
    # Find mugshot path
    mugshot_path = inmate.mugshot_path
    if not mugshot_path:
        print(f"  No mugshot path for {inmate.name}")
        return None

    # Handle different path formats
    if mugshot_path.startswith('/static/'):
        full_path = os.path.join(static_folder, mugshot_path[8:])  # Remove '/static/'
    elif mugshot_path.startswith('static/'):
        full_path = os.path.join(static_folder, mugshot_path[7:])  # Remove 'static/'
    else:
        full_path = os.path.join(static_folder, mugshot_path)

    if not os.path.exists(full_path):
        # Try alternative paths
        alt_paths = [
            os.path.join(static_folder, 'inmate_images', os.path.basename(mugshot_path)),
            os.path.join(static_folder, os.path.basename(mugshot_path)),
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                full_path = alt
                break
        else:
            print(f"  Mugshot not found: {mugshot_path}")
            return None

    # Load image
    image = cv2.imread(full_path)
    if image is None:
        print(f"  Failed to load image: {full_path}")
        return None

    # Generate augmentations
    augmentations = generate_augmentations(image)
    print(f"  Generated {len(augmentations)} augmentations")

    # Encode all augmentations
    embeddings = []
    for aug_image, aug_name in augmentations:
        embedding = encode_image(aug_image)
        if embedding:
            embeddings.append(embedding)
            print(f"    Encoded: {aug_name}")
        else:
            print(f"    Failed: {aug_name}")

    return embeddings if embeddings else None


def main():
    """Main function to re-encode all inmates with augmentations."""
    print("=" * 60)
    print("INMATE AUGMENTATION AND RE-ENCODING")
    print("=" * 60)

    # Check embedding service
    print("\nChecking embedding service...")
    try:
        response = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if response.status_code == 200:
            print(f"  Embedding service OK: {response.json()}")
        else:
            print(f"  WARNING: Embedding service returned {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("\nERROR: Embedding service not running!")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Get static folder path
        static_folder = os.path.join(app.root_path, 'static')
        print(f"\nStatic folder: {static_folder}")

        # Load all inmates
        inmates = Inmate.query.all()
        print(f"\nFound {len(inmates)} inmates to process")

        if not inmates:
            print("No inmates found in database.")
            return

        # Process each inmate
        success_count = 0
        fail_count = 0

        for i, inmate in enumerate(inmates):
            print(f"\n[{i+1}/{len(inmates)}] Processing: {inmate.name} ({inmate.inmate_id})")

            embeddings = process_inmate(inmate, static_folder)

            if embeddings:
                # Store multi-embeddings in database
                inmate.set_multi_encodings(embeddings)

                # Also keep first embedding as legacy single encoding
                if inmate.face_encoding is None:
                    inmate.face_encoding = np.array(embeddings[0])

                db.session.commit()
                print(f"  Stored {len(embeddings)} embeddings")
                success_count += 1
            else:
                print(f"  FAILED - no embeddings generated")
                fail_count += 1

            # Progress update every 10 inmates
            if (i + 1) % 10 == 0:
                print(f"\n--- Progress: {i+1}/{len(inmates)} processed ---\n")

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total inmates: {len(inmates)}")
        print(f"Successfully processed: {success_count}")
        print(f"Failed: {fail_count}")
        print("=" * 60)


if __name__ == "__main__":
    main()
