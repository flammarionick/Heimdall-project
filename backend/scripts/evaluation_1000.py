#!/usr/bin/env python3
"""
1000-Test Recognition Model Evaluation.
Runs comprehensive tests with varying distortions to find breaking points.

Usage:
    cd backend
    python scripts/evaluation_1000.py
"""

import os
import sys
import cv2
import numpy as np
import requests
import json
import time
from datetime import datetime
from io import BytesIO
from scipy.spatial.distance import cosine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate
from app.utils.image_preprocessing import aggressive_denoise, deblur_image, selective_preprocess

# Configuration
EMBEDDING_URL = "http://127.0.0.1:5001/encode"
APPLY_PREPROCESSING = False  # DISABLED - preprocessing degrades accuracy, fix is noise augmentation at enrollment
USE_SELECTIVE_PREPROCESSING = False  # DISABLED - selective preprocessing also degrades accuracy
SIMILARITY_THRESHOLD = 0.45
BREAKING_POINT_THRESHOLD = 70  # Accuracy below this = breaking point
RANDOM_SEED = 42

np.random.seed(RANDOM_SEED)


def get_embedding(image_bgr, apply_preprocessing=True):
    """Get embedding from service with optional selective preprocessing."""
    img_to_encode = image_bgr
    preprocess_info = None

    if apply_preprocessing and APPLY_PREPROCESSING:
        try:
            if USE_SELECTIVE_PREPROCESSING:
                # SELECTIVE: Only preprocess if noise/blur detected
                img_to_encode, preprocess_info = selective_preprocess(image_bgr)
            else:
                # BLANKET: Always apply (degrades clean images!)
                img_to_encode = aggressive_denoise(image_bgr)
                img_to_encode = deblur_image(img_to_encode)
        except Exception:
            img_to_encode = image_bgr

    _, buffer = cv2.imencode('.jpg', img_to_encode)
    files = {'image': ('face.jpg', BytesIO(buffer.tobytes()), 'image/jpeg')}
    try:
        resp = requests.post(EMBEDDING_URL, files=files, timeout=30)
        if resp.status_code == 200:
            emb = resp.json().get('embedding')
            if emb:
                return np.array(emb), preprocess_info
    except Exception as e:
        print(f"  [WARN] Embedding failed: {e}")
    return None, preprocess_info


def add_gaussian_noise(image, sigma):
    """Add Gaussian noise to image."""
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def apply_occlusion(image, percentage, location="random"):
    """Apply partial occlusion with black rectangles."""
    h, w = image.shape[:2]
    result = image.copy()

    occ_size = int(np.sqrt(percentage / 100) * min(h, w))

    if location == "random":
        x = np.random.randint(0, max(1, w - occ_size))
        y = np.random.randint(0, max(1, h - occ_size))
    elif location == "center":
        x = (w - occ_size) // 2
        y = (h - occ_size) // 2
    elif location == "bottom":
        x = (w - occ_size) // 2
        y = h - occ_size
    else:
        x, y = 0, 0

    result[y:y+occ_size, x:x+occ_size] = 0
    return result


def reduce_resolution(image, target_size):
    """Reduce resolution then upscale back."""
    original_size = (image.shape[1], image.shape[0])
    small = cv2.resize(image, (target_size, target_size), interpolation=cv2.INTER_AREA)
    upscaled = cv2.resize(small, original_size, interpolation=cv2.INTER_LINEAR)
    return upscaled


def generate_distortions_extended(image_bgr):
    """Generate extended set of distortions for 1000 tests."""
    distortions = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    # === CORE DISTORTIONS (8 per inmate = 840 tests for 105 inmates) ===

    # 1. Original
    distortions.append(('original', image_bgr.copy(), 1))

    # 2. Rotation 30 degrees
    M = cv2.getRotationMatrix2D(center, 30, 1.0)
    rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    distortions.append(('rotation_30', rotated, 2))

    # 3. Dark exposure
    dark = cv2.convertScaleAbs(image_bgr, alpha=0.5, beta=-30)
    distortions.append(('dark', dark, 3))

    # 4. Blur (kernel 11x11)
    blurred = cv2.GaussianBlur(image_bgr, (11, 11), 0)
    distortions.append(('blur_11', blurred, 4))

    # 5. Noise (sigma=30)
    noisy = add_gaussian_noise(image_bgr, 30)
    distortions.append(('noise_30', noisy, 5))

    # 6. Resolution (48x48 upscaled)
    low_res = reduce_resolution(image_bgr, 48)
    distortions.append(('resolution_48', low_res, 6))

    # 7. Grayscale
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    distortions.append(('grayscale', gray_bgr, 7))

    # 8. Combined (20 rotation + slight exposure + noise)
    M = cv2.getRotationMatrix2D(center, 20, 1.0)
    combined = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    combined = cv2.convertScaleAbs(combined, alpha=0.8, beta=-10)
    combined = add_gaussian_noise(combined, 15)
    distortions.append(('combined', combined, 8))

    return distortions


def generate_breaking_point_tests(image_bgr, distortion_type):
    """Generate progressive distortion levels for breaking point analysis."""
    tests = []
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)

    if distortion_type == 'rotation':
        angles = [0, 10, 20, 30, 45, 60, 90, 120, 150, 180]
        for angle in angles:
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            tests.append((f'rotation_{angle}', rotated, angle))

    elif distortion_type == 'blur':
        kernels = [3, 5, 7, 11, 15, 21, 31]
        for k in kernels:
            blurred = cv2.GaussianBlur(image_bgr, (k, k), 0)
            tests.append((f'blur_{k}', blurred, k))

    elif distortion_type == 'noise':
        sigmas = [5, 10, 20, 30, 50, 70, 100]
        for sigma in sigmas:
            noisy = add_gaussian_noise(image_bgr, sigma)
            tests.append((f'noise_{sigma}', noisy, sigma))

    elif distortion_type == 'resolution':
        sizes = [96, 80, 64, 48, 32, 24, 16]
        for size in sizes:
            low_res = reduce_resolution(image_bgr, size)
            tests.append((f'resolution_{size}', low_res, size))

    elif distortion_type == 'brightness':
        levels = [
            (1.0, 0, 'normal'),
            (1.2, 20, 'bright_1'),
            (1.5, 50, 'bright_2'),
            (0.8, -10, 'dark_1'),
            (0.5, -30, 'dark_2'),
            (0.3, -50, 'dark_3'),
            (2.0, 100, 'overexposed'),
        ]
        for alpha, beta, name in levels:
            adjusted = cv2.convertScaleAbs(image_bgr, alpha=alpha, beta=beta)
            tests.append((f'brightness_{name}', adjusted, beta))

    elif distortion_type == 'occlusion':
        percentages = [0, 10, 20, 30, 40, 50]
        for pct in percentages:
            if pct == 0:
                tests.append(('occlusion_0', image_bgr.copy(), 0))
            else:
                occluded = apply_occlusion(image_bgr, pct)
                tests.append((f'occlusion_{pct}', occluded, pct))

    return tests


def get_mugshot_path(inmate, static_folder):
    """Get full path to inmate's mugshot."""
    mugshot_path = inmate.mugshot_path
    if not mugshot_path:
        return None

    if mugshot_path.startswith('/static/'):
        full_path = os.path.join(static_folder, mugshot_path[8:])
    elif mugshot_path.startswith('static/'):
        full_path = os.path.join(static_folder, mugshot_path[7:])
    else:
        full_path = os.path.join(static_folder, mugshot_path)

    if os.path.exists(full_path):
        return full_path

    alt_paths = [
        os.path.join(static_folder, 'inmate_images', os.path.basename(mugshot_path)),
        os.path.join(static_folder, os.path.basename(mugshot_path)),
    ]
    for alt in alt_paths:
        if os.path.exists(alt):
            return alt

    return None


def match_against_database(query_embedding, inmate_encodings):
    """Find the best match for a query embedding."""
    best_match = None
    best_distance = float('inf')

    for inmate_id, encodings in inmate_encodings.items():
        for enc in encodings:
            dist = cosine(query_embedding, enc)
            if dist < best_distance:
                best_distance = dist
                best_match = inmate_id

    return best_match, best_distance


def main():
    print("=" * 70)
    print("HEIMDALL 1000-TEST RECOGNITION EVALUATION")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Similarity Threshold: {SIMILARITY_THRESHOLD}")
    print(f"Breaking Point Threshold: {BREAKING_POINT_THRESHOLD}% accuracy")

    # Check embedding service
    try:
        resp = requests.get("http://127.0.0.1:5001/health", timeout=5)
        print(f"Embedding service: OK")
    except:
        print("ERROR: Embedding service not running on port 5001!")
        print("Start it with: python app/utils/embedding_service.py")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        static_folder = os.path.join(app.root_path, 'static')
        scripts_folder = os.path.dirname(os.path.abspath(__file__))

        # Create failed_samples directory
        failed_samples_dir = os.path.join(scripts_folder, 'failed_samples')
        os.makedirs(failed_samples_dir, exist_ok=True)

        # Load all inmates with encodings
        inmates = Inmate.query.filter(
            db.or_(
                Inmate.face_encoding.isnot(None),
                Inmate.face_encodings_json.isnot(None)
            )
        ).all()

        print(f"Total inmates with encodings: {len(inmates)}")

        # Pre-load all encodings for faster matching
        inmate_encodings = {}
        for inmate in inmates:
            encodings = inmate.get_all_encodings()
            if encodings:
                inmate_encodings[inmate.inmate_id] = encodings

        print(f"Loaded encodings for {len(inmate_encodings)} inmates")
        print("=" * 70)

        # Results tracking
        results = {
            "test_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "config": {
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "breaking_point_threshold": BREAKING_POINT_THRESHOLD,
                "random_seed": RANDOM_SEED
            },
            "total_inmates": len(inmates),
            "total_tests": 0,
            "correct_matches": 0,
            "wrong_matches": 0,
            "no_matches": 0,
            "per_distortion": {},
            "failed_tests": [],
            "timing": {
                "inference_times_ms": [],
                "mean_inference_time_ms": 0,
                "max_inference_time_ms": 0
            },
            "breaking_points": {},
            "problem_inmates": []
        }

        # Initialize per-distortion tracking
        distortion_names = [
            'original', 'rotation_30', 'dark', 'blur_11',
            'noise_30', 'resolution_48', 'grayscale', 'combined'
        ]
        for name in distortion_names:
            results["per_distortion"][name] = {
                "correct": 0, "wrong": 0, "no_match": 0, "total": 0,
                "distances": [], "confidences": []
            }

        # Breaking point tracking
        bp_distortions = ['rotation', 'blur', 'noise', 'resolution', 'brightness', 'occlusion']
        for bp in bp_distortions:
            results["breaking_points"][bp] = {"levels": {}, "breaking_level": None}

        # ========== PHASE 1: Core 1000 Tests ==========
        print("\n[PHASE 1] Running core distortion tests...")
        print("-" * 70)

        for idx, inmate in enumerate(inmates):
            mugshot_path = get_mugshot_path(inmate, static_folder)
            if not mugshot_path:
                continue

            image = cv2.imread(mugshot_path)
            if image is None:
                continue

            # Generate core distortions
            distortions = generate_distortions_extended(image)
            inmate_failures = []
            test_results = []

            for dist_name, dist_img, level in distortions:
                results["total_tests"] += 1

                # Get base distortion name for tracking
                base_name = dist_name
                if base_name in results["per_distortion"]:
                    results["per_distortion"][base_name]["total"] += 1

                # Time the inference
                start_time = time.time()
                query_emb, preprocess_info = get_embedding(dist_img)
                inference_time = (time.time() - start_time) * 1000
                results["timing"]["inference_times_ms"].append(inference_time)

                if query_emb is None:
                    results["no_matches"] += 1
                    if base_name in results["per_distortion"]:
                        results["per_distortion"][base_name]["no_match"] += 1
                    test_results.append("X")
                    inmate_failures.append(f"{dist_name}: embedding failed")
                    continue

                # Find best match
                matched_id, distance = match_against_database(query_emb, inmate_encodings)
                confidence = (1 - distance) * 100 if distance < 1 else 0

                if distance >= SIMILARITY_THRESHOLD:
                    # No match
                    results["no_matches"] += 1
                    if base_name in results["per_distortion"]:
                        results["per_distortion"][base_name]["no_match"] += 1
                        results["per_distortion"][base_name]["distances"].append(distance)
                    test_results.append("-")
                    inmate_failures.append(f"{dist_name}: no match (dist={distance:.3f})")

                    # Save failed image
                    failed_path = os.path.join(failed_samples_dir, f"{inmate.inmate_id}_{dist_name}_nomatch.jpg")
                    cv2.imwrite(failed_path, dist_img)
                    results["failed_tests"].append({
                        "inmate_id": inmate.inmate_id,
                        "distortion": dist_name,
                        "result": "no_match",
                        "distance": distance,
                        "image_path": failed_path
                    })

                elif matched_id == inmate.inmate_id:
                    # Correct match
                    results["correct_matches"] += 1
                    if base_name in results["per_distortion"]:
                        results["per_distortion"][base_name]["correct"] += 1
                        results["per_distortion"][base_name]["distances"].append(distance)
                        results["per_distortion"][base_name]["confidences"].append(confidence)
                    test_results.append("+")
                else:
                    # Wrong match
                    results["wrong_matches"] += 1
                    if base_name in results["per_distortion"]:
                        results["per_distortion"][base_name]["wrong"] += 1
                        results["per_distortion"][base_name]["distances"].append(distance)
                    test_results.append("!")
                    inmate_failures.append(f"{dist_name}: WRONG (matched {matched_id})")

                    # Save failed image
                    failed_path = os.path.join(failed_samples_dir, f"{inmate.inmate_id}_{dist_name}_wrong.jpg")
                    cv2.imwrite(failed_path, dist_img)
                    results["failed_tests"].append({
                        "inmate_id": inmate.inmate_id,
                        "distortion": dist_name,
                        "result": "wrong_match",
                        "expected": inmate.inmate_id,
                        "matched": matched_id,
                        "distance": distance,
                        "confidence": confidence,
                        "image_path": failed_path
                    })

            # Print progress
            result_str = "".join(test_results)
            correct = result_str.count("+")
            print(f"[{idx+1:3}/{len(inmates)}] {inmate.inmate_id}: {result_str} ({correct}/8)")

            if inmate_failures:
                results["problem_inmates"].append({
                    "inmate_id": inmate.inmate_id,
                    "name": inmate.name,
                    "failures": inmate_failures
                })

        # ========== PHASE 2: Breaking Point Analysis ==========
        print("\n" + "=" * 70)
        print("[PHASE 2] Breaking Point Analysis (sample of 15 inmates)")
        print("-" * 70)

        # Sample 15 inmates for breaking point analysis
        sample_inmates = inmates[:15] if len(inmates) >= 15 else inmates

        for bp_type in bp_distortions:
            print(f"\nTesting {bp_type} breaking point...")
            level_results = {}

            for inmate in sample_inmates:
                mugshot_path = get_mugshot_path(inmate, static_folder)
                if not mugshot_path:
                    continue

                image = cv2.imread(mugshot_path)
                if image is None:
                    continue

                # Generate progressive tests
                bp_tests = generate_breaking_point_tests(image, bp_type)

                for test_name, test_img, level in bp_tests:
                    results["total_tests"] += 1

                    if level not in level_results:
                        level_results[level] = {"correct": 0, "wrong": 0, "no_match": 0, "total": 0}
                    level_results[level]["total"] += 1

                    query_emb, _ = get_embedding(test_img)
                    if query_emb is None:
                        level_results[level]["no_match"] += 1
                        results["no_matches"] += 1
                        continue

                    matched_id, distance = match_against_database(query_emb, inmate_encodings)

                    if distance >= SIMILARITY_THRESHOLD:
                        level_results[level]["no_match"] += 1
                        results["no_matches"] += 1
                    elif matched_id == inmate.inmate_id:
                        level_results[level]["correct"] += 1
                        results["correct_matches"] += 1
                    else:
                        level_results[level]["wrong"] += 1
                        results["wrong_matches"] += 1

            # Calculate accuracy per level and find breaking point
            breaking_level = None
            for level in sorted(level_results.keys()):
                data = level_results[level]
                if data["total"] > 0:
                    accuracy = (data["correct"] / data["total"]) * 100
                    level_results[level]["accuracy"] = round(accuracy, 1)

                    if accuracy < BREAKING_POINT_THRESHOLD and breaking_level is None:
                        breaking_level = level

            results["breaking_points"][bp_type]["levels"] = {
                str(k): v for k, v in level_results.items()
            }
            results["breaking_points"][bp_type]["breaking_level"] = breaking_level

            # Print breaking point result
            if breaking_level is not None:
                print(f"  {bp_type}: BREAKS at level {breaking_level}")
            else:
                print(f"  {bp_type}: ROBUST (no breaking point found)")

        # ========== PHASE 3: Calculate Final Statistics ==========
        print("\n" + "=" * 70)
        print("[PHASE 3] Calculating Final Statistics")
        print("-" * 70)

        # Calculate overall accuracy
        if results["total_tests"] > 0:
            results["overall_accuracy"] = round(
                (results["correct_matches"] / results["total_tests"]) * 100, 2
            )
            results["precision"] = round(
                (results["correct_matches"] / (results["correct_matches"] + results["wrong_matches"]) * 100)
                if (results["correct_matches"] + results["wrong_matches"]) > 0 else 0, 2
            )
            results["recall"] = round(
                (results["correct_matches"] / (results["correct_matches"] + results["no_matches"]) * 100)
                if (results["correct_matches"] + results["no_matches"]) > 0 else 0, 2
            )

        # Calculate per-distortion accuracy
        for dist_name in distortion_names:
            dist_data = results["per_distortion"][dist_name]
            if dist_data["total"] > 0:
                dist_data["accuracy"] = round(
                    (dist_data["correct"] / dist_data["total"]) * 100, 2
                )
                if dist_data["distances"]:
                    dist_data["mean_distance"] = round(np.mean(dist_data["distances"]), 4)
                if dist_data["confidences"]:
                    dist_data["mean_confidence"] = round(np.mean(dist_data["confidences"]), 2)

        # Timing statistics
        if results["timing"]["inference_times_ms"]:
            results["timing"]["mean_inference_time_ms"] = round(
                np.mean(results["timing"]["inference_times_ms"]), 2
            )
            results["timing"]["max_inference_time_ms"] = round(
                max(results["timing"]["inference_times_ms"]), 2
            )
        # Remove raw timing data to keep file small
        del results["timing"]["inference_times_ms"]

        # Remove raw distance/confidence arrays to keep file small
        for dist_name in distortion_names:
            if "distances" in results["per_distortion"][dist_name]:
                del results["per_distortion"][dist_name]["distances"]
            if "confidences" in results["per_distortion"][dist_name]:
                del results["per_distortion"][dist_name]["confidences"]

        # ========== PRINT SUMMARY ==========
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total tests: {results['total_tests']}")
        print(f"Correct matches: {results['correct_matches']}")
        print(f"Wrong matches: {results['wrong_matches']}")
        print(f"No matches: {results['no_matches']}")
        print(f"\nOVERALL ACCURACY: {results.get('overall_accuracy', 0)}%")
        print(f"Precision: {results.get('precision', 0)}%")
        print(f"Recall: {results.get('recall', 0)}%")
        print(f"Mean inference time: {results['timing']['mean_inference_time_ms']} ms")

        print("\n" + "-" * 70)
        print("ACCURACY BY DISTORTION TYPE")
        print("-" * 70)
        for dist_name in distortion_names:
            dist_data = results["per_distortion"][dist_name]
            acc = dist_data.get("accuracy", 0)
            bar = "#" * int(acc / 5) + "." * (20 - int(acc / 5))
            status = "OK" if acc >= BREAKING_POINT_THRESHOLD else "WEAK"
            print(f"{dist_name:15} {bar} {acc:5.1f}% ({dist_data['correct']}/{dist_data['total']}) [{status}]")

        print("\n" + "-" * 70)
        print("BREAKING POINTS")
        print("-" * 70)
        for bp_type, bp_data in results["breaking_points"].items():
            bl = bp_data.get("breaking_level")
            if bl is not None:
                print(f"  {bp_type:12}: BREAKS at level {bl}")
            else:
                print(f"  {bp_type:12}: ROBUST (no breaking point)")

        # Count wrong match inmates
        wrong_match_count = len([
            p for p in results["problem_inmates"]
            if any("WRONG" in f for f in p["failures"])
        ])
        print(f"\nInmates with wrong matches: {wrong_match_count}")
        print(f"Failed images saved to: {failed_samples_dir}")

        # Save results to JSON
        output_path = os.path.join(scripts_folder, 'evaluation_results.json')
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

        # Also save to .claude/plans for session memory
        claude_plans_dir = os.path.join(os.path.expanduser('~'), '.claude', 'plans')
        os.makedirs(claude_plans_dir, exist_ok=True)
        session_copy_path = os.path.join(claude_plans_dir, 'evaluation_results.json')
        with open(session_copy_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Session copy saved to: {session_copy_path}")

        print("\n" + "=" * 70)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return results


if __name__ == "__main__":
    main()
