#!/usr/bin/env python3
"""
1000 Test Recognition Performance Assessment

This script tests the facial recognition system's robustness by running 1000 tests
with varying levels of noise, distortions, and degradations.

Usage:
    cd backend
    python scripts/test_recognition_performance.py
"""

import os
import sys
import cv2
import numpy as np
import random
import requests
import json
import time
from io import BytesIO
from datetime import datetime
from collections import defaultdict

# Fix Windows console encoding and force unbuffered output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "http://127.0.0.1:5002"
LOGIN_API = f"{BASE_URL}/auth/api/login"
RECOGNITION_API = f"{BASE_URL}/api/recognition/upload"
TOTAL_TESTS = 500  # Reduced to avoid memory issues; can run twice for 1000 total
RESULTS_FILE = "recognition_performance_results.json"

# Default credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

# Global session for authenticated requests
_session = None


def get_authenticated_session():
    """Login and return an authenticated session."""
    global _session
    if _session is not None:
        return _session

    _session = requests.Session()

    try:
        # Login to get session cookie
        login_data = {
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD
        }
        response = _session.post(LOGIN_API, json=login_data, timeout=10)

        if response.status_code == 200:
            print(f"  [OK] Logged in as {DEFAULT_USERNAME}")
            return _session
        else:
            print(f"  [ERROR] Login failed: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"  [ERROR] Login error: {e}")
        return None


# Noise levels to test (0 = none, 1 = light, 2 = medium, 3 = heavy, 4 = extreme)
NOISE_LEVELS = {
    0: "none",
    1: "light",
    2: "medium",
    3: "heavy",
    4: "extreme"
}


def add_gaussian_noise(image, level):
    """Add Gaussian noise with varying intensity."""
    if level == 0:
        return image.copy()

    # Scale noise based on level (5, 15, 30, 50, 80)
    sigma = [0, 5, 15, 30, 50, 80][min(level, 5)]
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def add_salt_pepper_noise(image, level):
    """Add salt and pepper noise with varying density."""
    if level == 0:
        return image.copy()

    # Probability of noise (0.01, 0.03, 0.07, 0.12, 0.20)
    prob = [0, 0.01, 0.03, 0.07, 0.12, 0.20][min(level, 5)]
    noisy = image.copy()

    # Salt
    num_salt = int(prob * image.size / 2)
    coords = [np.random.randint(0, i, num_salt) for i in image.shape[:2]]
    noisy[coords[0], coords[1]] = 255

    # Pepper
    coords = [np.random.randint(0, i, num_salt) for i in image.shape[:2]]
    noisy[coords[0], coords[1]] = 0

    return noisy


def add_blur(image, level):
    """Add blur with varying kernel size."""
    if level == 0:
        return image.copy()

    # Kernel sizes: 3, 5, 9, 13, 19
    kernel_sizes = [1, 3, 5, 9, 13, 19]
    k = kernel_sizes[min(level, 5)]
    return cv2.GaussianBlur(image, (k, k), 0)


def add_motion_blur(image, level):
    """Add motion blur with varying intensity."""
    if level == 0:
        return image.copy()

    # Kernel sizes: 5, 10, 15, 25, 35
    sizes = [0, 5, 10, 15, 25, 35]
    size = sizes[min(level, 5)]

    kernel = np.zeros((size, size))
    kernel[size // 2, :] = np.ones(size)
    kernel /= size

    return cv2.filter2D(image, -1, kernel)


def adjust_brightness(image, level, direction='random'):
    """Adjust brightness (darker or brighter)."""
    if level == 0:
        return image.copy()

    if direction == 'random':
        direction = np.random.choice(['darker', 'brighter'])

    # Adjustment values
    adjustments = [0, 20, 40, 70, 100, 140]
    adj = adjustments[min(level, 5)]

    if direction == 'darker':
        return cv2.convertScaleAbs(image, alpha=1.0, beta=-adj)
    else:
        return cv2.convertScaleAbs(image, alpha=1.0, beta=adj)


def adjust_contrast(image, level):
    """Adjust contrast with varying intensity."""
    if level == 0:
        return image.copy()

    # Contrast multipliers: 0.8, 0.6, 0.4, 1.5, 2.0
    if level <= 2:
        alpha = [1.0, 0.8, 0.6, 0.4][level]
    else:
        alpha = [1.0, 1.0, 1.0, 1.5, 2.0, 2.5][min(level, 5)]

    return cv2.convertScaleAbs(image, alpha=alpha, beta=0)


def add_rotation(image, level):
    """Add rotation with varying angles."""
    if level == 0:
        return image.copy()

    # Angles: 5, 15, 25, 40, 60
    max_angles = [0, 5, 15, 25, 40, 60]
    max_angle = max_angles[min(level, 5)]
    angle = np.random.uniform(-max_angle, max_angle)

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def add_jpeg_artifacts(image, level):
    """Add JPEG compression artifacts."""
    if level == 0:
        return image.copy()

    # Quality: 80, 50, 30, 15, 5
    qualities = [100, 80, 50, 30, 15, 5]
    quality = qualities[min(level, 5)]

    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def add_occlusion(image, level):
    """Add random occlusion (simulating partial face blocking)."""
    if level == 0:
        return image.copy()

    result = image.copy()
    h, w = image.shape[:2]

    # Occlusion sizes: 5%, 10%, 15%, 25%, 35%
    percentages = [0, 0.05, 0.10, 0.15, 0.25, 0.35]
    pct = percentages[min(level, 5)]

    # Add random black rectangles
    num_blocks = level
    for _ in range(num_blocks):
        block_w = int(w * pct)
        block_h = int(h * pct)
        x = np.random.randint(0, w - block_w)
        y = np.random.randint(0, h - block_h)
        result[y:y+block_h, x:x+block_w] = 0

    return result


def apply_combined_distortions(image, noise_level):
    """Apply a combination of distortions based on noise level."""
    result = image.copy()

    # Randomly select which distortions to apply
    distortion_funcs = [
        ('gaussian', add_gaussian_noise),
        ('salt_pepper', add_salt_pepper_noise),
        ('blur', add_blur),
        ('brightness', lambda img, lvl: adjust_brightness(img, lvl)),
        ('contrast', adjust_contrast),
        ('rotation', add_rotation),
        ('jpeg', add_jpeg_artifacts),
    ]

    # Apply random subset of distortions
    num_distortions = min(noise_level + 1, len(distortion_funcs))
    selected = np.random.choice(len(distortion_funcs), size=num_distortions, replace=False)

    applied = []
    for idx in selected:
        name, func = distortion_funcs[idx]
        # Vary the individual level slightly
        individual_level = max(1, min(5, noise_level + np.random.randint(-1, 2)))
        result = func(result, individual_level)
        applied.append(name)

    return result, applied


def test_recognition(image_bgr, expected_inmate_id):
    """Send image to recognition API and check results."""
    try:
        session = get_authenticated_session()
        if session is None:
            return {
                'success': False,
                'in_top_3': False,
                'in_results': False,
                'top_id': None,
                'confidence': 0,
                'all_matches': [],
                'response_time': 0,
                'error': 'not_authenticated'
            }

        _, buffer = cv2.imencode('.jpg', image_bgr)
        jpg_bytes = buffer.tobytes()

        # Use 'file' field as expected by the upload endpoint
        files = {'file': ('test.jpg', BytesIO(jpg_bytes), 'image/jpeg')}
        start_time = time.time()
        response = session.post(RECOGNITION_API, files=files, timeout=60)
        response_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            status = data.get('status', '')

            # Handle match found
            if status in ['match_found', 'escaped_inmate_detected']:
                inmate = data.get('inmate', {})
                top_id = inmate.get('inmate_id', '')
                confidence = inmate.get('confidence', 0)

                # Check if expected inmate matches
                exact_match = (top_id == expected_inmate_id)

                return {
                    'success': exact_match,
                    'in_top_3': exact_match,  # Single match returned
                    'in_results': exact_match,
                    'top_id': top_id,
                    'confidence': confidence,
                    'all_matches': [inmate] if inmate else [],
                    'response_time': response_time,
                    'error': None
                }

            # Handle no match - check top_3_matches for potential matches
            elif status == 'no_match':
                top_3 = data.get('top_3_matches', [])
                top_id = top_3[0].get('inmate_id', '') if top_3 else None
                best_distance = data.get('best_distance', 1.0)
                confidence = (1 - best_distance) * 100 if best_distance else 0

                # Check if expected inmate is in top 3
                top_3_ids = [m.get('inmate_id', '') for m in top_3]
                in_top_3 = expected_inmate_id in top_3_ids

                return {
                    'success': False,
                    'in_top_3': in_top_3,
                    'in_results': in_top_3,
                    'top_id': top_id,
                    'confidence': confidence,
                    'all_matches': top_3,
                    'response_time': response_time,
                    'error': None
                }

            # Handle low confidence
            elif status == 'low_confidence':
                confidence = data.get('confidence', 0)
                return {
                    'success': False,
                    'in_top_3': False,
                    'in_results': False,
                    'top_id': None,
                    'confidence': confidence,
                    'all_matches': [],
                    'response_time': response_time,
                    'error': 'low_confidence'
                }

            # Handle no face detected or other status
            else:
                return {
                    'success': False,
                    'in_top_3': False,
                    'in_results': False,
                    'top_id': None,
                    'confidence': 0,
                    'all_matches': [],
                    'response_time': response_time,
                    'error': status or 'unknown_status'
                }
        else:
            return {
                'success': False,
                'in_top_3': False,
                'in_results': False,
                'top_id': None,
                'confidence': 0,
                'all_matches': [],
                'response_time': response_time,
                'error': f'api_error_{response.status_code}'
            }

    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'in_top_3': False,
            'in_results': False,
            'top_id': None,
            'confidence': 0,
            'all_matches': [],
            'response_time': 0,
            'error': 'connection_error'
        }
    except Exception as e:
        return {
            'success': False,
            'in_top_3': False,
            'in_results': False,
            'top_id': None,
            'confidence': 0,
            'all_matches': [],
            'response_time': 0,
            'error': str(e)
        }


def get_distortion_type():
    """Randomly select a distortion type."""
    types = [
        'gaussian_noise',
        'salt_pepper',
        'blur',
        'motion_blur',
        'brightness',
        'contrast',
        'rotation',
        'jpeg_compression',
        'occlusion',
        'combined'
    ]
    return np.random.choice(types)


def apply_single_distortion(image, distortion_type, noise_level):
    """Apply a specific distortion type."""
    if distortion_type == 'gaussian_noise':
        return add_gaussian_noise(image, noise_level)
    elif distortion_type == 'salt_pepper':
        return add_salt_pepper_noise(image, noise_level)
    elif distortion_type == 'blur':
        return add_blur(image, noise_level)
    elif distortion_type == 'motion_blur':
        return add_motion_blur(image, noise_level)
    elif distortion_type == 'brightness':
        return adjust_brightness(image, noise_level)
    elif distortion_type == 'contrast':
        return adjust_contrast(image, noise_level)
    elif distortion_type == 'rotation':
        return add_rotation(image, noise_level)
    elif distortion_type == 'jpeg_compression':
        return add_jpeg_artifacts(image, noise_level)
    elif distortion_type == 'occlusion':
        return add_occlusion(image, noise_level)
    elif distortion_type == 'combined':
        result, _ = apply_combined_distortions(image, noise_level)
        return result
    else:
        return image.copy()


def main():
    print("=" * 80)
    print("FACIAL RECOGNITION PERFORMANCE TEST - 1000 TESTS")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check API availability
    print("Checking services...")
    try:
        # Try the recognition upload endpoint to verify backend is working
        response = requests.get("http://127.0.0.1:5002/", timeout=5)
        print("  [OK] Recognition API (port 5002)")
    except:
        print("  [ERROR] Backend API not running on port 5002!")
        print("  Start it with: cd backend && python run.py")
        sys.exit(1)

    try:
        response = requests.get("http://127.0.0.1:5001/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Embedding Service (port 5001)")
        else:
            raise Exception("Bad status")
    except:
        print("  [ERROR] Embedding service not running on port 5001!")
        print("  Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    # Authenticate
    print("\nAuthenticating...")
    session = get_authenticated_session()
    if session is None:
        print("  [ERROR] Failed to authenticate!")
        sys.exit(1)

    # Find test images
    static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'static')
    inmate_images_dir = os.path.join(static_folder, 'inmate_images')

    if not os.path.exists(inmate_images_dir):
        print(f"ERROR: Inmate images directory not found: {inmate_images_dir}")
        sys.exit(1)

    # Load all inmate images
    image_files = [f for f in os.listdir(inmate_images_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    if not image_files:
        print("ERROR: No inmate images found!")
        sys.exit(1)

    print(f"\nFound {len(image_files)} inmate images")
    print(f"Running {TOTAL_TESTS} tests...")
    print()

    # Load images into memory
    images = {}
    for img_file in image_files:
        inmate_id = img_file.rsplit('_', 1)[0]
        img_path = os.path.join(inmate_images_dir, img_file)
        img = cv2.imread(img_path)
        if img is not None:
            if inmate_id not in images:
                images[inmate_id] = []
            images[inmate_id].append(img)

    inmate_ids = list(images.keys())
    print(f"Loaded images for {len(inmate_ids)} inmates")
    print()

    # Results tracking
    results = {
        'metadata': {
            'total_tests': TOTAL_TESTS,
            'start_time': datetime.now().isoformat(),
            'num_inmates': len(inmate_ids),
            'num_images': len(image_files)
        },
        'by_noise_level': defaultdict(lambda: {'total': 0, 'exact': 0, 'top3': 0, 'detected': 0, 'avg_confidence': [], 'avg_time': []}),
        'by_distortion': defaultdict(lambda: {'total': 0, 'exact': 0, 'top3': 0, 'detected': 0, 'avg_confidence': [], 'avg_time': []}),
        'individual_tests': []
    }

    # Distortion types
    distortion_types = [
        'gaussian_noise', 'salt_pepper', 'blur', 'motion_blur',
        'brightness', 'contrast', 'rotation', 'jpeg_compression',
        'occlusion', 'combined'
    ]

    # Run tests
    tests_run = 0
    exact_matches = 0
    top3_matches = 0
    detected = 0

    print("-" * 80)
    print(f"{'Test':<6} | {'Inmate':<12} | {'Distortion':<18} | {'Level':<8} | {'Result':<10} | {'Conf':>6} | {'Time':>6}")
    print("-" * 80)

    start_time = time.time()

    while tests_run < TOTAL_TESTS:
        # Select random inmate and image
        inmate_id = random.choice(inmate_ids)
        image = random.choice(images[inmate_id])

        # Select random distortion type and level
        distortion_type = random.choice(distortion_types)
        noise_level = random.randint(0, 4)  # 0-4

        # Apply distortion
        distorted = apply_single_distortion(image, distortion_type, noise_level)

        # Test recognition
        result = test_recognition(distorted, inmate_id)

        tests_run += 1

        # Track results
        if result['success']:
            exact_matches += 1
            status = "EXACT"
        elif result['in_top_3']:
            top3_matches += 1
            status = "TOP-3"
        elif result['in_results']:
            detected += 1
            status = "FOUND"
        elif result['error']:
            status = f"ERR:{result['error'][:5]}"
        else:
            status = "MISS"

        # Update stats by noise level
        level_key = NOISE_LEVELS[noise_level]
        results['by_noise_level'][level_key]['total'] += 1
        if result['success']:
            results['by_noise_level'][level_key]['exact'] += 1
        if result['in_top_3']:
            results['by_noise_level'][level_key]['top3'] += 1
        if result['in_results']:
            results['by_noise_level'][level_key]['detected'] += 1
        results['by_noise_level'][level_key]['avg_confidence'].append(result['confidence'])
        results['by_noise_level'][level_key]['avg_time'].append(result['response_time'])

        # Update stats by distortion type
        results['by_distortion'][distortion_type]['total'] += 1
        if result['success']:
            results['by_distortion'][distortion_type]['exact'] += 1
        if result['in_top_3']:
            results['by_distortion'][distortion_type]['top3'] += 1
        if result['in_results']:
            results['by_distortion'][distortion_type]['detected'] += 1
        results['by_distortion'][distortion_type]['avg_confidence'].append(result['confidence'])
        results['by_distortion'][distortion_type]['avg_time'].append(result['response_time'])

        # Store individual test
        results['individual_tests'].append({
            'test_num': tests_run,
            'inmate_id': inmate_id,
            'distortion': distortion_type,
            'noise_level': noise_level,
            'success': result['success'],
            'in_top_3': result['in_top_3'],
            'in_results': result['in_results'],
            'top_match': result['top_id'],
            'confidence': result['confidence'],
            'response_time': result['response_time'],
            'error': result['error']
        })

        # Print progress every test
        print(f"{tests_run:<6} | {inmate_id:<12} | {distortion_type:<18} | {level_key:<8} | {status:<10} | {result['confidence']:>5.1f}% | {result['response_time']:>5.2f}s")

        # Progress update every 100 tests
        if tests_run % 100 == 0:
            elapsed = time.time() - start_time
            rate = tests_run / elapsed
            remaining = (TOTAL_TESTS - tests_run) / rate if rate > 0 else 0
            print(f"\n>>> Progress: {tests_run}/{TOTAL_TESTS} ({tests_run/TOTAL_TESTS*100:.1f}%) | "
                  f"Exact: {exact_matches} | Top-3: {exact_matches + top3_matches} | "
                  f"ETA: {remaining:.0f}s\n")

    total_time = time.time() - start_time

    # Calculate final statistics
    print()
    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(f"\nOverall Performance:")
    print(f"  Total tests:     {tests_run}")
    print(f"  Exact matches:   {exact_matches} ({exact_matches/tests_run*100:.1f}%)")
    print(f"  Top-3 matches:   {exact_matches + top3_matches} ({(exact_matches + top3_matches)/tests_run*100:.1f}%)")
    print(f"  Detected:        {exact_matches + top3_matches + detected} ({(exact_matches + top3_matches + detected)/tests_run*100:.1f}%)")
    print(f"  Total time:      {total_time:.1f}s ({tests_run/total_time:.2f} tests/sec)")

    print(f"\nPerformance by Noise Level:")
    print(f"  {'Level':<10} | {'Tests':>6} | {'Exact':>8} | {'Top-3':>8} | {'Detected':>8} | {'Avg Conf':>8} | {'Avg Time':>8}")
    print("-" * 75)
    for level in ['none', 'light', 'medium', 'heavy', 'extreme']:
        stats = results['by_noise_level'][level]
        if stats['total'] > 0:
            avg_conf = np.mean(stats['avg_confidence']) if stats['avg_confidence'] else 0
            avg_time = np.mean(stats['avg_time']) if stats['avg_time'] else 0
            print(f"  {level:<10} | {stats['total']:>6} | {stats['exact']/stats['total']*100:>7.1f}% | "
                  f"{stats['top3']/stats['total']*100:>7.1f}% | {stats['detected']/stats['total']*100:>7.1f}% | "
                  f"{avg_conf:>7.1f}% | {avg_time:>7.2f}s")

    print(f"\nPerformance by Distortion Type:")
    print(f"  {'Distortion':<18} | {'Tests':>6} | {'Exact':>8} | {'Top-3':>8} | {'Avg Conf':>8}")
    print("-" * 65)
    for dist_type in distortion_types:
        stats = results['by_distortion'][dist_type]
        if stats['total'] > 0:
            avg_conf = np.mean(stats['avg_confidence']) if stats['avg_confidence'] else 0
            print(f"  {dist_type:<18} | {stats['total']:>6} | {stats['exact']/stats['total']*100:>7.1f}% | "
                  f"{stats['top3']/stats['total']*100:>7.1f}% | {avg_conf:>7.1f}%")

    # Save results to file
    results['metadata']['end_time'] = datetime.now().isoformat()
    results['metadata']['total_time_seconds'] = total_time
    results['summary'] = {
        'exact_match_rate': exact_matches / tests_run * 100,
        'top3_match_rate': (exact_matches + top3_matches) / tests_run * 100,
        'detection_rate': (exact_matches + top3_matches + detected) / tests_run * 100,
        'tests_per_second': tests_run / total_time
    }

    # Convert defaultdicts to regular dicts and calculate averages
    results['by_noise_level'] = {
        k: {
            'total': v['total'],
            'exact': v['exact'],
            'top3': v['top3'],
            'detected': v['detected'],
            'avg_confidence': np.mean(v['avg_confidence']) if v['avg_confidence'] else 0,
            'avg_time': np.mean(v['avg_time']) if v['avg_time'] else 0
        }
        for k, v in results['by_noise_level'].items()
    }

    results['by_distortion'] = {
        k: {
            'total': v['total'],
            'exact': v['exact'],
            'top3': v['top3'],
            'detected': v['detected'],
            'avg_confidence': np.mean(v['avg_confidence']) if v['avg_confidence'] else 0,
            'avg_time': np.mean(v['avg_time']) if v['avg_time'] else 0
        }
        for k, v in results['by_distortion'].items()
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = os.path.join(script_dir, RESULTS_FILE)

    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
    print("=" * 80)

    # Assessment
    exact_rate = exact_matches / tests_run * 100
    top3_rate = (exact_matches + top3_matches) / tests_run * 100

    print("\nMODEL ASSESSMENT:")
    if exact_rate >= 80:
        print("  EXCELLENT: Model shows strong recognition accuracy (80%+ exact match)")
    elif exact_rate >= 60:
        print("  GOOD: Model has reasonable accuracy, some room for improvement")
    elif exact_rate >= 40:
        print("  FAIR: Model needs improvement, consider retraining or tuning thresholds")
    else:
        print("  POOR: Model struggles with noisy inputs, significant improvement needed")

    if top3_rate >= 90:
        print("  Top-3 accuracy is excellent - model reliably identifies correct person in results")
    elif top3_rate >= 70:
        print("  Top-3 accuracy is good - model usually includes correct person in results")
    else:
        print("  Top-3 accuracy needs work - model often misses the correct person entirely")

    print("=" * 80)


if __name__ == "__main__":
    main()
