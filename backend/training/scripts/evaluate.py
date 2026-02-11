#!/usr/bin/env python3
"""
Model Evaluation Script for Heimdall Face Recognition

Evaluates the trained model across all test conditions to verify
97% accuracy target is met.

Usage:
    cd backend/training
    python scripts/evaluate.py --model models/final/heimdall_facenet_retrained.pt

Conditions tested:
    - Original (clean images)
    - Rotation (15°, 30°, 45°)
    - Grayscale
    - Noise (σ=10, 30, 50)
    - Low light (0.3x brightness)
    - JPEG compression (Q=30, 50)
    - Blur (kernel 5, 7, 11)
    - Combined distortions
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import cv2
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent.parent))

from facenet_pytorch import InceptionResnetV1
from src.dataset import FaceDataset, get_validation_transform

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


# Test conditions configuration
TEST_CONDITIONS = {
    'original': {
        'name': 'Original',
        'transform': None,
        'target_accuracy': 1.00
    },
    'rotation_15': {
        'name': 'Rotation 15°',
        'transform': lambda img: rotate_image(img, 15),
        'target_accuracy': 0.97
    },
    'rotation_30': {
        'name': 'Rotation 30°',
        'transform': lambda img: rotate_image(img, 30),
        'target_accuracy': 0.97
    },
    'rotation_45': {
        'name': 'Rotation 45°',
        'transform': lambda img: rotate_image(img, 45),
        'target_accuracy': 0.97
    },
    'grayscale': {
        'name': 'Grayscale',
        'transform': lambda img: to_grayscale(img),
        'target_accuracy': 1.00
    },
    'noise_10': {
        'name': 'Noise σ=10',
        'transform': lambda img: add_noise(img, 10),
        'target_accuracy': 0.97
    },
    'noise_30': {
        'name': 'Noise σ=30',
        'transform': lambda img: add_noise(img, 30),
        'target_accuracy': 0.97  # Critical: was 13.3%
    },
    'noise_50': {
        'name': 'Noise σ=50',
        'transform': lambda img: add_noise(img, 50),
        'target_accuracy': 0.90
    },
    'low_light': {
        'name': 'Low Light (0.3x)',
        'transform': lambda img: adjust_brightness(img, 0.3),
        'target_accuracy': 0.97
    },
    'jpeg_30': {
        'name': 'JPEG Q=30',
        'transform': lambda img: jpeg_compress(img, 30),
        'target_accuracy': 0.97
    },
    'jpeg_50': {
        'name': 'JPEG Q=50',
        'transform': lambda img: jpeg_compress(img, 50),
        'target_accuracy': 0.97
    },
    'blur_5': {
        'name': 'Blur kernel=5',
        'transform': lambda img: blur_image(img, 5),
        'target_accuracy': 0.97
    },
    'blur_7': {
        'name': 'Blur kernel=7',
        'transform': lambda img: blur_image(img, 7),
        'target_accuracy': 0.95
    },
    'blur_11': {
        'name': 'Blur kernel=11',
        'transform': lambda img: blur_image(img, 11),
        'target_accuracy': 0.90
    },
    'combined': {
        'name': 'Combined (noise+rotation+jpeg)',
        'transform': lambda img: apply_combined(img),
        'target_accuracy': 0.97  # Critical: was 15.2%
    }
}


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by given angle."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale and back to 3 channels."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)


def add_noise(image: np.ndarray, sigma: float) -> np.ndarray:
    """Add Gaussian noise."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255)
    return noisy.astype(np.uint8)


def adjust_brightness(image: np.ndarray, factor: float) -> np.ndarray:
    """Adjust image brightness."""
    return np.clip(image * factor, 0, 255).astype(np.uint8)


def jpeg_compress(image: np.ndarray, quality: int) -> np.ndarray:
    """Apply JPEG compression."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encoded = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR), encode_param)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    return cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)


def blur_image(image: np.ndarray, kernel_size: int) -> np.ndarray:
    """Apply Gaussian blur."""
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def apply_combined(image: np.ndarray) -> np.ndarray:
    """Apply combined distortions: noise + rotation + JPEG compression."""
    img = add_noise(image, 20)
    img = rotate_image(img, 15)
    img = jpeg_compress(img, 50)
    return img


def load_model(model_path: str, device: torch.device) -> torch.nn.Module:
    """Load trained model."""
    print(f"Loading model from: {model_path}")

    if model_path.endswith('.pt'):
        # TorchScript model
        model = torch.jit.load(model_path, map_location=device)
    else:
        # State dict
        model = InceptionResnetV1(pretrained=None, classify=False)
        model.load_state_dict(torch.load(model_path, map_location=device))
        model = model.to(device)

    model.eval()
    return model


def build_gallery(
    model: torch.nn.Module,
    gallery_dataset: FaceDataset,
    device: torch.device
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build gallery embeddings for all identities.

    Args:
        model: Face recognition model
        gallery_dataset: Dataset containing gallery images
        device: Target device

    Returns:
        Tuple of (embeddings, labels)
    """
    print("Building gallery embeddings...")

    loader = DataLoader(gallery_dataset, batch_size=64, shuffle=False, num_workers=4)

    all_embeddings = []
    all_labels = []

    with torch.no_grad():
        iterator = tqdm(loader, desc="Gallery") if TQDM_AVAILABLE else loader
        for images, labels in iterator:
            images = images.to(device)
            embeddings = model(images)
            embeddings = F.normalize(embeddings, p=2, dim=1)

            all_embeddings.append(embeddings.cpu().numpy())
            all_labels.append(labels.numpy())

    embeddings = np.concatenate(all_embeddings, axis=0)
    labels = np.concatenate(all_labels, axis=0)

    print(f"Gallery size: {len(embeddings)} embeddings")
    return embeddings, labels


def evaluate_condition(
    model: torch.nn.Module,
    test_dataset: FaceDataset,
    gallery_embeddings: np.ndarray,
    gallery_labels: np.ndarray,
    condition_key: str,
    device: torch.device,
    threshold: float = 0.45
) -> Dict:
    """
    Evaluate model on a specific condition.

    Args:
        model: Face recognition model
        test_dataset: Test dataset
        gallery_embeddings: Gallery embeddings
        gallery_labels: Gallery labels
        condition_key: Key of condition to test
        device: Target device
        threshold: Cosine distance threshold

    Returns:
        Dictionary of metrics
    """
    condition = TEST_CONDITIONS[condition_key]
    transform_fn = condition['transform']

    correct = 0
    wrong = 0
    no_match = 0
    total = 0
    inference_times = []

    # Process each test image
    for idx in range(len(test_dataset)):
        # Get original image (before dataset transform)
        img_path, label = test_dataset.samples[idx]
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize
        image = cv2.resize(image, (160, 160))

        # Apply condition transform
        if transform_fn:
            image = transform_fn(image)

        # Normalize for model
        image = image.astype(np.float32) / 255.0
        image = (image - 0.5) / 0.5
        image = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0).float()

        # Get embedding
        start_time = time.time()
        with torch.no_grad():
            image = image.to(device)
            embedding = model(image)
            embedding = F.normalize(embedding, p=2, dim=1)
            embedding = embedding.cpu().numpy()[0]
        inference_time = time.time() - start_time
        inference_times.append(inference_time)

        # Match against gallery (cosine distance)
        distances = 1 - np.dot(gallery_embeddings, embedding)
        min_idx = np.argmin(distances)
        min_distance = distances[min_idx]
        predicted_label = gallery_labels[min_idx]

        # Evaluate
        if min_distance > threshold:
            no_match += 1
        elif predicted_label == label:
            correct += 1
        else:
            wrong += 1

        total += 1

    accuracy = correct / total if total > 0 else 0
    precision = correct / (correct + wrong) if (correct + wrong) > 0 else 0
    mean_inference_time = np.mean(inference_times) * 1000  # ms

    return {
        'condition': condition_key,
        'name': condition['name'],
        'total': total,
        'correct': correct,
        'wrong': wrong,
        'no_match': no_match,
        'accuracy': accuracy,
        'precision': precision,
        'target_accuracy': condition['target_accuracy'],
        'target_met': accuracy >= condition['target_accuracy'],
        'mean_inference_time_ms': mean_inference_time
    }


def run_full_evaluation(
    model: torch.nn.Module,
    test_dir: str,
    gallery_dir: str,
    device: torch.device,
    output_path: str = None
) -> Dict:
    """
    Run full evaluation across all conditions.

    Args:
        model: Face recognition model
        test_dir: Path to test data
        gallery_dir: Path to gallery data
        device: Target device
        output_path: Optional path to save results

    Returns:
        Dictionary of all results
    """
    print("\n" + "=" * 60)
    print("HEIMDALL MODEL EVALUATION")
    print("=" * 60)

    # Create datasets
    gallery_dataset = FaceDataset(
        gallery_dir,
        transform=get_validation_transform(),
        min_samples_per_class=1
    )

    test_dataset = FaceDataset(
        test_dir,
        transform=None,  # We'll apply transforms manually
        min_samples_per_class=1
    )

    # Build gallery
    gallery_embeddings, gallery_labels = build_gallery(model, gallery_dataset, device)

    # Run evaluation for each condition
    results = {
        'timestamp': datetime.now().isoformat(),
        'test_samples': len(test_dataset),
        'gallery_size': len(gallery_embeddings),
        'conditions': {}
    }

    print("\n" + "-" * 60)
    print("EVALUATING CONDITIONS")
    print("-" * 60)

    overall_correct = 0
    overall_total = 0
    all_targets_met = True

    for condition_key in TEST_CONDITIONS:
        print(f"\nTesting: {TEST_CONDITIONS[condition_key]['name']}...")

        condition_results = evaluate_condition(
            model, test_dataset, gallery_embeddings, gallery_labels,
            condition_key, device
        )

        results['conditions'][condition_key] = condition_results

        # Print results
        status = "PASS" if condition_results['target_met'] else "FAIL"
        status_color = "" if condition_results['target_met'] else "[!]"

        print(f"  Accuracy: {condition_results['accuracy']:.2%} "
              f"(target: {condition_results['target_accuracy']:.0%}) {status_color}{status}")

        overall_correct += condition_results['correct']
        overall_total += condition_results['total']

        if not condition_results['target_met']:
            all_targets_met = False

    # Overall metrics
    overall_accuracy = overall_correct / overall_total if overall_total > 0 else 0
    results['overall_accuracy'] = overall_accuracy
    results['all_targets_met'] = all_targets_met

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nOverall Accuracy: {overall_accuracy:.2%}")
    print(f"Target (97%): {'MET' if overall_accuracy >= 0.97 else 'NOT MET'}")
    print(f"All conditions passed: {'YES' if all_targets_met else 'NO'}")

    print("\n" + "-" * 40)
    print("CONDITION BREAKDOWN")
    print("-" * 40)
    print(f"{'Condition':<25} {'Accuracy':>10} {'Target':>10} {'Status':>10}")
    print("-" * 55)

    for key, cond in results['conditions'].items():
        status = "PASS" if cond['target_met'] else "FAIL"
        print(f"{cond['name']:<25} {cond['accuracy']:>9.1%} "
              f"{cond['target_accuracy']:>9.0%} {status:>10}")

    # Save results
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    return results


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description='Evaluate Heimdall face recognition model')
    parser.add_argument('--model', type=str, required=True,
                        help='Path to trained model')
    parser.add_argument('--test-dir', type=str, default='data/processed/test',
                        help='Path to test data')
    parser.add_argument('--gallery-dir', type=str, default='data/processed/train',
                        help='Path to gallery data')
    parser.add_argument('--output', type=str, default='evaluation_results_retrained.json',
                        help='Output file for results')
    parser.add_argument('--threshold', type=float, default=0.45,
                        help='Cosine distance threshold')

    args = parser.parse_args()

    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Load model
    model = load_model(args.model, device)

    # Run evaluation
    results = run_full_evaluation(
        model,
        args.test_dir,
        args.gallery_dir,
        device,
        args.output
    )

    # Exit code based on target
    if results['all_targets_met']:
        print("\n[SUCCESS] All accuracy targets met!")
        return 0
    else:
        print("\n[WARNING] Some accuracy targets not met.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
