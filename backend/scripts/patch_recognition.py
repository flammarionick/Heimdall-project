#!/usr/bin/env python3
"""Patch recognition_api.py with query-time augmentation."""
import os

file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'app', 'routes', 'recognition_api.py')

with open(file_path, 'r') as f:
    content = f.read()

# Add query augmentation function before _run_recognition
old_text = '''def _run_recognition(frame, use_detection=True) -> dict:
    """
    Run the recognition pipeline on a frame using similarity matching.
    Detects face first (for live camera), then compares HOG features against stored inmate encodings.
    Returns a dict with status and result.

    Args:
        frame: BGR image
        use_detection: If True (live camera), detect face first. If False (upload), just resize.
    """
    if frame is None:
        return {"error": "No valid image provided", "status_code": 400}

    try:
        # For uploads: just resize (consistent with how mugshots are stored)
        # For live camera: detect face in larger frame first
        face_crop = _detect_and_crop_face(frame, use_detection=use_detection)

        if face_crop is None:
            return {
                "status": "no_face_detected",
                "error": "No face detected in image. Please ensure a face is visible.",
                "status_code": 200
            }

        # Extract FaceNet embedding from cropped face
        input_features = extract_embedding_from_frame(face_crop)
        if input_features is None:
            return {"error": "Embedding service unavailable. Is it running on port 5001?", "status_code": 503}
        input_features = np.array(input_features, dtype=np.float32)
        log(f"[recognition_api] Input features shape: {len(input_features)} (FaceNet 512-dim)")'''

new_text = '''def _generate_query_augmentations(face_crop):
    """
    Generate augmented versions of query image for robust matching.
    Returns list of augmented images.
    """
    augmentations = [face_crop]  # Original first
    h, w = face_crop.shape[:2]
    center = (w // 2, h // 2)

    # Slight rotations
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(face_crop, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append(rotated)

    # Brightness adjustments
    bright = cv2.convertScaleAbs(face_crop, alpha=1.2, beta=20)
    dark = cv2.convertScaleAbs(face_crop, alpha=0.8, beta=-20)
    augmentations.append(bright)
    augmentations.append(dark)

    return augmentations


def _run_recognition(frame, use_detection=True) -> dict:
    """
    Run the recognition pipeline on a frame using similarity matching.
    Uses query-time augmentation for robust matching with distorted images.
    Returns a dict with status and result.

    Args:
        frame: BGR image
        use_detection: If True (live camera), detect face first. If False (upload), just resize.
    """
    if frame is None:
        return {"error": "No valid image provided", "status_code": 400}

    try:
        # For uploads: just resize (consistent with how mugshots are stored)
        # For live camera: detect face in larger frame first
        face_crop = _detect_and_crop_face(frame, use_detection=use_detection)

        if face_crop is None:
            return {
                "status": "no_face_detected",
                "error": "No face detected in image. Please ensure a face is visible.",
                "status_code": 200
            }

        # Generate query augmentations for robust matching
        query_augmentations = _generate_query_augmentations(face_crop)
        log(f"[recognition_api] Generated {len(query_augmentations)} query augmentations")

        # Extract embeddings for all augmentations
        query_embeddings = []
        for aug_img in query_augmentations:
            emb = extract_embedding_from_frame(aug_img)
            if emb is not None:
                query_embeddings.append(np.array(emb, dtype=np.float32))

        if not query_embeddings:
            return {"error": "Embedding service unavailable. Is it running on port 5001?", "status_code": 503}

        input_features = query_embeddings[0]  # Keep first for compatibility
        log(f"[recognition_api] Got {len(query_embeddings)} query embeddings (FaceNet 512-dim)")'''

if old_text in content:
    content = content.replace(old_text, new_text)
    print("Replaced _run_recognition function")
else:
    print("Could not find target text to replace")
    # Try alternative approach
    exit(1)

# Now update the matching loop to use all query embeddings
old_matching = '''        for inmate, encodings_list in inmate_encodings:
            try:
                # Compare against ALL embeddings for this inmate
                # Use minimum distance (best match across augmentations)
                min_dist_for_inmate = float('inf')
                for encoding in encodings_list:
                    dist = cosine(input_features, encoding)
                    if dist < min_dist_for_inmate:
                        min_dist_for_inmate = dist

                top_3_matches.append((inmate['inmate_id'], min_dist_for_inmate, len(encodings_list)))

                if min_dist_for_inmate < best_distance:
                    best_distance = min_dist_for_inmate
                    best_match = inmate'''

new_matching = '''        for inmate, encodings_list in inmate_encodings:
            try:
                # Compare ALL query embeddings against ALL inmate embeddings
                # Use minimum distance (best match across all combinations)
                min_dist_for_inmate = float('inf')
                for query_emb in query_embeddings:
                    for encoding in encodings_list:
                        dist = cosine(query_emb, encoding)
                        if dist < min_dist_for_inmate:
                            min_dist_for_inmate = dist

                top_3_matches.append((inmate['inmate_id'], min_dist_for_inmate, len(encodings_list)))

                if min_dist_for_inmate < best_distance:
                    best_distance = min_dist_for_inmate
                    best_match = inmate'''

if old_matching in content:
    content = content.replace(old_matching, new_matching)
    print("Updated matching loop to use all query embeddings")
else:
    print("Could not find matching loop to update")

with open(file_path, 'w') as f:
    f.write(content)

print("Patch applied successfully!")
