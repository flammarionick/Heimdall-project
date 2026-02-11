#!/usr/bin/env python3
"""
Test ArcFace model noise robustness.

This script directly tests whether the ArcFace model can match
noisy images to clean database embeddings.

Usage:
    cd backend
    python scripts/test_arcface_noise.py
"""

import os
import sys
import cv2
import numpy as np
import json
from datetime import datetime
from scipy.spatial.distance import cosine

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

import onnxruntime as ort

# Load ArcFace model
ARCFACE_MODEL_PATH = os.path.expanduser("~/.insightface/models/buffalo_l/w600k_r50.onnx")
session = ort.InferenceSession(ARCFACE_MODEL_PATH, providers=['CPUExecutionProvider'])
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def preprocess_for_arcface(img_bgr):
    """Preprocess image for ArcFace."""
    img_resized = cv2.resize(img_bgr, (112, 112))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_transposed = img_rgb.transpose(2, 0, 1)
    img_normalized = (img_transposed.astype(np.float32) - 127.5) / 127.5
    return np.expand_dims(img_normalized, axis=0)


def estimate_noise_level(img_bgr):
    """Estimate noise level using high-pass filter."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    high_pass = gray.astype(np.float64) - blur.astype(np.float64)
    return np.std(high_pass)


def denoise_image_aggressive(img_bgr):
    """Apply multiple passes of aggressive denoising."""
    # Pass 1: Heavy non-local means
    denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 20, 20, 7, 21)
    # Pass 2: Bilateral filter to preserve edges
    denoised = cv2.bilateralFilter(denoised, 11, 100, 100)
    # Pass 3: Light median blur
    denoised = cv2.medianBlur(denoised, 3)
    return denoised


def get_arcface_embedding(img_bgr, apply_denoising=False):
    """Get embedding using ArcFace model."""
    img_input = preprocess_for_arcface(img_bgr)
    embedding = session.run([output_name], {input_name: img_input})[0][0]
    embedding = embedding / np.linalg.norm(embedding)
    return embedding


def get_arcface_embedding_ensemble(img_bgr):
    """
    Get ensemble embedding by trying multiple preprocessing approaches.
    Returns the average of different preprocessing results.
    """
    embeddings = []

    # Original image
    emb1 = get_arcface_embedding(img_bgr)
    embeddings.append(emb1)

    # Aggressively denoised
    denoised = denoise_image_aggressive(img_bgr)
    emb2 = get_arcface_embedding(denoised)
    embeddings.append(emb2)

    # CLAHE enhanced
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    emb3 = get_arcface_embedding(enhanced)
    embeddings.append(emb3)

    # Average ensemble
    avg_emb = np.mean(embeddings, axis=0)
    avg_emb = avg_emb / np.linalg.norm(avg_emb)

    return avg_emb


def add_gaussian_noise(image, sigma):
    """Add Gaussian noise to an image."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float64)
    noisy = image.astype(np.float64) + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    return noisy


def main():
    print("=" * 60)
    print("ARCFACE NOISE ROBUSTNESS TEST")
    print("=" * 60)
    print(f"Model: {ARCFACE_MODEL_PATH}")
    print()

    # Connect to database
    import sqlite3
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, 'instance', 'heimdall.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all inmates with their stored embeddings
    cursor.execute("""
        SELECT id, inmate_id, name, mugshot_path, face_encodings_json
        FROM inmate
        WHERE face_encodings_json IS NOT NULL
    """)
    inmates = cursor.fetchall()

    print(f"Testing with {len(inmates)} inmates")
    print()

    # Load stored embeddings (now supports multiple embeddings per inmate)
    inmate_embeddings = {}
    for db_id, inmate_id, name, mugshot_path, encodings_json in inmates:
        try:
            encodings = json.loads(encodings_json)
            # Check if it's a list of embeddings or a single embedding
            if isinstance(encodings[0], list):
                # Multiple embeddings - store all of them
                inmate_embeddings[inmate_id] = {
                    'name': name,
                    'mugshot_path': mugshot_path,
                    'embeddings': [np.array(e) for e in encodings]  # List of embeddings
                }
            else:
                # Single embedding
                inmate_embeddings[inmate_id] = {
                    'name': name,
                    'mugshot_path': mugshot_path,
                    'embeddings': [np.array(encodings)]  # Wrap in list
                }
        except:
            continue

    print(f"Loaded {len(inmate_embeddings)} embeddings")
    print()

    # Test noise levels
    noise_levels = [0, 10, 20, 30, 50]
    results = {level: {'correct': 0, 'wrong': 0, 'total': 0} for level in noise_levels}

    # Test all inmates for accurate accuracy measurement
    test_inmates = list(inmate_embeddings.keys())

    print(f"Testing {len(test_inmates)} inmates with noise levels: {noise_levels}")
    print("-" * 60)

    for inmate_id in test_inmates:
        data = inmate_embeddings[inmate_id]
        mugshot_path = data['mugshot_path']

        if not mugshot_path:
            continue

        # Load image
        clean_path = mugshot_path.lstrip('/')
        full_path = os.path.join(backend_dir, 'app', clean_path)

        if not os.path.exists(full_path):
            full_path = os.path.join(backend_dir, 'app', 'static', 'inmate_images',
                                     os.path.basename(mugshot_path))

        if not os.path.exists(full_path):
            continue

        image = cv2.imread(full_path)
        if image is None:
            continue

        status_line = f"{inmate_id}: "

        for sigma in noise_levels:
            # Add noise
            if sigma == 0:
                noisy_image = image.copy()
            else:
                noisy_image = add_gaussian_noise(image, sigma)

            # Get embedding for noisy image (no preprocessing - match noisy to noisy)
            query_emb = get_arcface_embedding(noisy_image)

            # Find best match against all stored embeddings
            best_match = None
            best_distance = float('inf')

            for other_id, other_data in inmate_embeddings.items():
                # Compare against ALL embeddings for this inmate
                for emb in other_data['embeddings']:
                    dist = cosine(query_emb, emb)
                    if dist < best_distance:
                        best_distance = dist
                        best_match = other_id

            results[sigma]['total'] += 1

            # Check if match is correct (distance threshold of 0.4)
            if best_match == inmate_id and best_distance < 0.4:
                results[sigma]['correct'] += 1
                status_line += "+"
            else:
                results[sigma]['wrong'] += 1
                status_line += "-"

        print(status_line)

    # Print results
    print()
    print("=" * 60)
    print("RESULTS BY NOISE LEVEL (sigma)")
    print("=" * 60)

    for sigma in noise_levels:
        r = results[sigma]
        if r['total'] > 0:
            accuracy = (r['correct'] / r['total']) * 100
            bar = "#" * int(accuracy / 5) + "." * (20 - int(accuracy / 5))
            print(f"sigma={sigma:3d}: {bar} {accuracy:5.1f}% ({r['correct']}/{r['total']})")

    print()
    print("=" * 60)

    # Check if we hit 97% target
    sigma_30 = results[30]
    if sigma_30['total'] > 0:
        accuracy_30 = (sigma_30['correct'] / sigma_30['total']) * 100
        if accuracy_30 >= 97:
            print("SUCCESS: ArcFace achieves 97%+ accuracy at sigma=30!")
        else:
            print(f"CURRENT: sigma=30 accuracy is {accuracy_30:.1f}%")
            print("TARGET: 97% accuracy at sigma=30")

    conn.close()


if __name__ == '__main__':
    main()
