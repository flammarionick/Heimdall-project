# app/routes/recognition_api.py
from flask import Blueprint, request, jsonify
from app.utils.auth_helpers import login_or_jwt_required
from app import socketio
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.active_recognition import ActiveRecognition
from app.extensions import db
from app.utils.embedding_client import (
    extract_embedding_from_frame,
    extract_full_embeddings,
    extract_periocular_embedding,
    compute_fusion_score,
    detect_all_faces
)
from app.utils.geolocation import find_nearby_facilities, get_detection_location, haversine_distance
from app.utils.image_preprocessing import (
    aggressive_denoise, deblur_image, strong_deblur,
    remove_salt_pepper_noise, deblur_motion_horizontal, deblur_motion_multi_direction
)
from scipy.spatial.distance import cosine
from datetime import datetime, timedelta

import numpy as np
import cv2
import os
import sys

# Enable/disable periocular fusion matching
ENABLE_PERIOCULAR_FUSION = True

def log(msg):
    """Log to both stdout and a file for debugging."""
    print(msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    with open("recognition_debug.log", "a") as f:
        f.write(msg + "\n")


def should_create_alert(inmate_id, camera_id, detection_lat, detection_lng):
    """
    Check if we should create a new alert or skip (deduplication).

    Returns:
        tuple: (should_create: bool, existing_active: ActiveRecognition or None)

    Rules:
        - Create alert if no active recognition for this inmate in last hour
        - Create alert if detection is at different location (50m+ away)
        - Skip alert if same inmate, same location, within 1 hour
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Find active recognition for this inmate within the last hour
    active = ActiveRecognition.query.filter(
        ActiveRecognition.inmate_id == inmate_id,
        ActiveRecognition.first_detected_at > one_hour_ago
    ).order_by(ActiveRecognition.first_detected_at.desc()).first()

    if not active:
        log(f"[dedup] No active recognition for inmate {inmate_id} - will create alert")
        return True, None  # No active recognition, create alert

    # Check location difference (50m threshold)
    if active.latitude and active.longitude and detection_lat and detection_lng:
        try:
            distance_km = haversine_distance(
                active.latitude, active.longitude,
                detection_lat, detection_lng
            )
            if distance_km > 0.05:  # 50 meters = 0.05 km
                log(f"[dedup] Different location ({distance_km:.3f}km away) - will create new alert")
                return True, active  # Different location, create new alert
        except Exception as e:
            log(f"[dedup] Error calculating distance: {e}")

    # Update last_detected_at and skip alert
    try:
        active.last_detected_at = datetime.utcnow()
        db.session.commit()
        log(f"[dedup] Same location within 1 hour - skipping alert, updated last_detected_at")
    except Exception as e:
        log(f"[dedup] Error updating active recognition: {e}")
        db.session.rollback()

    return False, active  # Skip, same location within 1 hour


def create_active_recognition(inmate_id, camera_id, detection_lat, detection_lng, alert_id):
    """Create a new ActiveRecognition record to track this detection."""
    try:
        active = ActiveRecognition(
            inmate_id=inmate_id,
            camera_id=camera_id,
            latitude=detection_lat,
            longitude=detection_lng,
            alert_id=alert_id,
            first_detected_at=datetime.utcnow(),
            last_detected_at=datetime.utcnow()
        )
        db.session.add(active)
        db.session.commit()
        log(f"[dedup] Created ActiveRecognition for inmate {inmate_id}")
        return active
    except Exception as e:
        log(f"[dedup] Error creating ActiveRecognition: {e}")
        db.session.rollback()
        return None


recognition_api_bp = Blueprint('recognition_api', __name__, url_prefix='/api/recognition')

# Similarity threshold for matching (lower = stricter)
# FaceNet embeddings are more robust - can use higher threshold
SIMILARITY_THRESHOLD = 0.45   # Cosine distance threshold for FaceNet (40%+ similarity)
MIN_CONFIDENCE = 50  # Minimum confidence percentage to show match

# Cache for inmate encodings (loaded once per request cycle)
_inmate_cache = None
_cache_timestamp = None

# Load face cascade detector once
_face_cascade = None

def _get_face_cascade():
    """Load and cache the face cascade detector."""
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def _detect_and_crop_face(frame, use_detection=True):
    """
    Detect face in frame and return cropped face image.
    Returns the cropped face or None if no face detected.

    Args:
        frame: BGR image
        use_detection: If False, skip face detection and just resize (for upload matching)
    """
    if frame is None:
        return None

    h, w = frame.shape[:2]

    # If detection is disabled or image is small, just resize directly
    # This ensures consistent processing between registration and recognition
    if not use_detection or max(h, w) < 300:
        return cv2.resize(frame, (128, 128))

    # For live camera, use face detection to find face in larger frame
    face_cascade = _get_face_cascade()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = []
    for min_neighbors in [3, 2, 1]:
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=min_neighbors,
            minSize=(30, 30)
        )
        if len(faces) > 0:
            break

    if len(faces) == 0:
        # No face found - just resize the whole image
        return cv2.resize(frame, (128, 128))

    # Take the largest face
    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, fw, fh = largest_face

    padding = int(max(fw, fh) * 0.2)
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(frame.shape[1], x + fw + padding)
    y2 = min(frame.shape[0], y + fh + padding)

    face_crop = frame[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, (128, 128))

    return face_resized


def _detect_all_faces(frame):
    """
    Detect ALL faces in a frame and return list of cropped face images with bounding boxes.

    Args:
        frame: BGR image

    Returns:
        List of tuples: [(face_crop, bbox), ...] where bbox is (x, y, w, h)
    """
    if frame is None:
        return []

    h, w = frame.shape[:2]

    # Use face detection
    face_cascade = _get_face_cascade()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = []
    for min_neighbors in [5, 4, 3, 2]:
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=min_neighbors,
            minSize=(30, 30)
        )
        if len(faces) > 0:
            break

    if len(faces) == 0:
        log(f"[multi-face] No faces detected in image {w}x{h}")
        return []

    log(f"[multi-face] Detected {len(faces)} faces in image")

    # Process each face
    face_crops = []
    for i, (x, y, fw, fh) in enumerate(faces):
        padding = int(max(fw, fh) * 0.2)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(frame.shape[1], x + fw + padding)
        y2 = min(frame.shape[0], y + fh + padding)

        face_crop = frame[y1:y2, x1:x2]
        face_resized = cv2.resize(face_crop, (128, 128))

        bbox = (int(x), int(y), int(fw), int(fh))
        face_crops.append((face_resized, bbox))
        log(f"[multi-face] Face {i+1}: bbox={bbox}, crop size={face_crop.shape}")

    return face_crops

def _load_inmate_encodings():
    """
    Load all inmate face and periocular encodings from database.
    Supports both legacy single encoding and multi-embeddings.
    Returns list of (inmate_data, [face_encodings], [periocular_encodings]) tuples.
    """
    global _inmate_cache, _cache_timestamp
    import time
    import json

    # Refresh cache every 30 seconds (reduced for faster updates after new inmates)
    current_time = time.time()
    if _inmate_cache is None or _cache_timestamp is None or (current_time - _cache_timestamp) > 30:
        try:
            # Use a fresh query and extract data immediately
            # Select columns including multi-embeddings and periocular
            inmates = db.session.query(
                Inmate.id,
                Inmate.inmate_id,
                Inmate.name,
                Inmate.status,
                Inmate.mugshot_path,
                Inmate.risk_level,
                Inmate.crime,
                Inmate.face_encoding,
                Inmate.face_encodings_json,
                Inmate.periocular_encoding,
                Inmate.periocular_encodings_json,
                Inmate.has_glasses_in_mugshot
            ).filter(
                db.or_(
                    Inmate.face_encoding.isnot(None),
                    Inmate.face_encodings_json.isnot(None)
                )
            ).all()

            # Cache as plain data with list of all encodings per inmate
            new_cache = []
            total_face_encodings = 0
            total_periocular_encodings = 0

            for row in inmates:
                face_encodings = []
                periocular_encodings = []

                # Add legacy single face encoding if exists
                if row.face_encoding is not None:
                    face_encodings.append(np.array(row.face_encoding, dtype=np.float32))

                # Add multi face embeddings if exists
                if row.face_encodings_json:
                    try:
                        multi_enc = json.loads(row.face_encodings_json)
                        for enc in multi_enc:
                            if enc is not None:
                                face_encodings.append(np.array(enc, dtype=np.float32))
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Add legacy single periocular encoding if exists
                if row.periocular_encoding is not None:
                    periocular_encodings.append(np.array(row.periocular_encoding, dtype=np.float32))

                # Add multi periocular embeddings if exists
                if row.periocular_encodings_json:
                    try:
                        multi_peri = json.loads(row.periocular_encodings_json)
                        for enc in multi_peri:
                            if enc is not None:
                                periocular_encodings.append(np.array(enc, dtype=np.float32))
                    except (json.JSONDecodeError, TypeError):
                        pass

                if face_encodings:
                    inmate_data = {
                        "id": row.id,
                        "inmate_id": row.inmate_id,
                        "name": row.name,
                        "status": row.status,
                        "mugshot_path": row.mugshot_path,
                        "risk_level": row.risk_level,
                        "crime": row.crime,
                        "has_glasses_in_mugshot": row.has_glasses_in_mugshot or False,
                    }
                    new_cache.append((inmate_data, face_encodings, periocular_encodings))
                    total_face_encodings += len(face_encodings)
                    total_periocular_encodings += len(periocular_encodings)

            _inmate_cache = new_cache
            _cache_timestamp = current_time
            print(f"[recognition_api] Loaded {len(_inmate_cache)} inmates: {total_face_encodings} face + {total_periocular_encodings} periocular encodings")
        except Exception as e:
            print(f"[recognition_api] Error loading cache: {e}")
            import traceback
            traceback.print_exc()

    return _inmate_cache

def _decode_frame_from_request(req) -> np.ndarray:
    """
    Expect multipart/form-data with key 'frame' containing an image file.
    Returns a BGR OpenCV image array or None.
    """
    if 'frame' not in req.files:
        return None
    frame_file = req.files['frame']
    npimg = np.frombuffer(frame_file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    return img

def _decode_image_from_file_field(req, field_name='frame') -> np.ndarray:
    """
    Decode image from a file field in the request.
    Returns a BGR OpenCV image array or None.
    """
    if field_name not in req.files:
        return None
    file = req.files[field_name]
    npimg = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    return img


def _generate_query_augmentations(face_crop):
    """
    Generate augmented versions of query image for robust matching.
    Optimized to prevent memory exhaustion - max ~15 augmentations.
    """
    augmentations = [face_crop]
    h, w = face_crop.shape[:2]
    center = (w // 2, h // 2)

    # CLAHE normalization (used multiple times below)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    # === Essential rotations (reduced from 7 to 3) ===
    for angle in [-15, 15, 180]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(face_crop, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append(rotated)

    # === Grayscale ===
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmentations.append(gray_bgr)

    # === Exposure corrections ===
    bright = cv2.convertScaleAbs(face_crop, alpha=1.3, beta=30)
    augmentations.append(bright)

    # === CLAHE normalization ===
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    clahe_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    augmentations.append(clahe_img)

    # === Gaussian noise removal (NL means) ===
    try:
        denoised = aggressive_denoise(face_crop)
        augmentations.append(denoised)
    except Exception:
        pass

    # === General deblurring ===
    try:
        sharpened = strong_deblur(face_crop)
        augmentations.append(sharpened)
    except Exception:
        pass

    # === Salt & pepper noise removal (median filter) ===
    try:
        sp_denoised = remove_salt_pepper_noise(face_crop, kernel_size=5)
        augmentations.append(sp_denoised)
    except Exception:
        pass

    # === Motion blur handling (horizontal) ===
    try:
        motion_h = deblur_motion_horizontal(face_crop, kernel_size=11)
        augmentations.append(motion_h)
    except Exception:
        pass

    # === Combined: denoised + sharpened (for combined distortions) ===
    try:
        combined = aggressive_denoise(face_crop)
        combined = strong_deblur(combined)
        augmentations.append(combined)
    except Exception:
        pass

    return augmentations


def _run_recognition(frame, use_detection=True) -> dict:
    """
    Run the recognition pipeline on a frame using similarity matching.
    Uses query-time augmentation for robust matching with distorted images.
    Supports periocular fusion matching for glasses/occlusion robustness.
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

        # Extract face embeddings for all augmentations
        query_embeddings = []
        for aug_img in query_augmentations:
            emb = extract_embedding_from_frame(aug_img)
            if emb is not None:
                query_embeddings.append(np.array(emb, dtype=np.float32))

        if not query_embeddings:
            return {"error": "Embedding service unavailable. Is it running on port 5001?", "status_code": 503}

        input_features = query_embeddings[0]  # Keep first for compatibility
        log(f"[recognition_api] Got {len(query_embeddings)} query face embeddings (FaceNet 512-dim)")

        # === PERIOCULAR FUSION: Extract periocular embedding and detect glasses ===
        query_periocular_emb = None
        glasses_detected = False
        glasses_confidence = 0.0

        if ENABLE_PERIOCULAR_FUSION:
            try:
                # Try to get periocular embedding from the original frame (not face crop)
                peri_result = extract_periocular_embedding(frame)
                if peri_result and peri_result.get('embedding'):
                    query_periocular_emb = np.array(peri_result['embedding'], dtype=np.float32)
                    glasses_detected = peri_result.get('glasses_detected', False)
                    glasses_confidence = peri_result.get('glasses_confidence', 0.0)
                    log(f"[recognition_api] Periocular embedding extracted. Glasses: {glasses_detected} ({glasses_confidence:.2f})")
                else:
                    log("[recognition_api] Periocular extraction failed, using face-only matching")
            except Exception as e:
                log(f"[recognition_api] Periocular extraction error: {e}")
                # Continue with face-only matching

        # Load cached inmate encodings (now includes periocular)
        inmate_encodings = _load_inmate_encodings()

        if not inmate_encodings:
            return {"error": "No inmate face encodings in database", "status_code": 500}

        log(f"[recognition_api] Comparing against {len(inmate_encodings)} cached inmates")

        # Find best match using cosine distance with optional periocular fusion
        best_match = None
        best_distance = float('inf')
        best_match_method = 'face_only'
        top_3_matches = []

        for inmate, face_encodings_list, periocular_encodings_list in inmate_encodings:
            try:
                # Compare ALL query embeddings against ALL inmate face embeddings
                min_face_dist = float('inf')
                for query_emb in query_embeddings:
                    for encoding in face_encodings_list:
                        dist = cosine(query_emb, encoding)
                        if dist < min_face_dist:
                            min_face_dist = dist

                # === PERIOCULAR FUSION ===
                # If we have periocular embeddings for both query and inmate, use fusion
                final_distance = min_face_dist
                match_method = 'face_only'

                if (ENABLE_PERIOCULAR_FUSION and
                    query_periocular_emb is not None and
                    periocular_encodings_list):

                    # Find best periocular match
                    min_peri_dist = float('inf')
                    for peri_enc in periocular_encodings_list:
                        peri_dist = cosine(query_periocular_emb, peri_enc)
                        if peri_dist < min_peri_dist:
                            min_peri_dist = peri_dist

                    # Compute fusion score with adaptive weighting
                    fused_dist, face_weight = compute_fusion_score(
                        min_face_dist,
                        min_peri_dist,
                        glasses_detected,
                        glasses_confidence
                    )
                    final_distance = fused_dist
                    match_method = f'fusion(face:{face_weight:.2f})'
                    log(f"[recognition_api] {inmate['inmate_id']}: face={min_face_dist:.4f}, peri={min_peri_dist:.4f}, fused={fused_dist:.4f}")

                elif ENABLE_PERIOCULAR_FUSION and glasses_detected and query_periocular_emb is not None:
                    # Glasses detected but inmate has no periocular encodings
                    # Boost face distance slightly since glasses may interfere
                    final_distance = min_face_dist * 0.95  # Slight forgiveness
                    match_method = 'face_only(glasses_boost)'

                top_3_matches.append((inmate['inmate_id'], final_distance, len(face_encodings_list), match_method))

                if final_distance < best_distance:
                    best_distance = final_distance
                    best_match = inmate
                    best_match_method = match_method
            except Exception as e:
                print(f"[recognition_api] Error comparing with {inmate['inmate_id']}: {e}")
                continue

        # Sort and show top 3 matches for debugging
        top_3_matches.sort(key=lambda x: x[1])
        log(f"[recognition_api] Top 3 matches: {[(m[0], f'{m[1]:.4f}', m[3]) for m in top_3_matches[:3]]}")
        log(f"[recognition_api] Best match: {best_match['inmate_id'] if best_match else 'None'}, distance: {best_distance:.4f}, method: {best_match_method}, threshold: {SIMILARITY_THRESHOLD}")

        # Check if match is above threshold
        if best_match and best_distance < SIMILARITY_THRESHOLD:
            confidence = float(round((1 - best_distance) * 100, 1))

            # Only show match if confidence is high enough
            if confidence >= MIN_CONFIDENCE:
                # best_match is already a dictionary from the cache
                inmate_payload = {
                    "id": best_match["id"],
                    "inmate_id": best_match["inmate_id"],
                    "name": best_match["name"],
                    "status": best_match["status"],
                    "mugshot_path": best_match["mugshot_path"],
                    "risk_level": best_match["risk_level"],
                    "crime": best_match["crime"],
                    "confidence": confidence,
                }

                # Check if inmate is ESCAPED - trigger critical alarm
                is_escaped = str(inmate_payload.get("status", "")).lower() == "escaped"

                # Get camera_id and detection location early for deduplication
                camera_id = None
                detection_lat, detection_lng = None, None
                try:
                    camera_id = request.form.get('camera_id') if hasattr(request, 'form') else None
                    if camera_id:
                        camera_id = int(camera_id)
                    detection_lat, detection_lng = get_detection_location(camera_id)
                except Exception as e:
                    log(f"[recognition_api] Error getting location: {e}")

                # DEDUPLICATION CHECK - prevent multiple alerts for same inmate
                should_create, existing_active = should_create_alert(
                    inmate_id=best_match["id"],
                    camera_id=camera_id,
                    detection_lat=detection_lat,
                    detection_lng=detection_lng
                )

                if not should_create:
                    # Detection logged but no new alert needed
                    log(f"[recognition_api] Skipping duplicate alert for {inmate_payload['name']}")
                    return {
                        "status": "escaped_inmate_detected" if is_escaped else "match_found",
                        "inmate": inmate_payload,
                        "is_escaped": is_escaped,
                        "deduplicated": True,
                        "message": "Detection logged. Alert already active for this inmate at this location.",
                        "existing_alert_id": existing_active.alert_id if existing_active else None,
                        "status_code": 200
                    }

                # Create Alert record with confidence score for tracking
                alert_id = None
                try:
                    alert_level = "danger" if is_escaped else "warning"
                    alert_message = (
                        f"ESCAPED INMATE DETECTED: {inmate_payload['name']} ({confidence}% confidence)"
                        if is_escaped
                        else f"Match found: {inmate_payload['name']} ({confidence}% confidence)"
                    )

                    alert = Alert(
                        message=alert_message,
                        level=alert_level,
                        confidence=confidence,
                        inmate_id=best_match["id"],
                        camera_id=camera_id,
                        resolved=False
                    )
                    db.session.add(alert)
                    db.session.commit()
                    alert_id = alert.id
                    print(f"[recognition_api] Alert created with confidence {confidence}% - Escaped: {is_escaped}")

                    # Create ActiveRecognition record for future deduplication
                    create_active_recognition(
                        inmate_id=best_match["id"],
                        camera_id=camera_id,
                        detection_lat=detection_lat,
                        detection_lng=detection_lng,
                        alert_id=alert_id
                    )
                except Exception as e:
                    print(f"[recognition_api] Failed to create alert: {e}")
                    db.session.rollback()
                    alert_id = None

                # Real-time event for dashboards
                try:
                    socketio.emit('match_found', {
                        'inmate_name': inmate_payload["name"],
                        'inmate_id': inmate_payload["id"],
                        'confidence': inmate_payload["confidence"],
                        'is_escaped': is_escaped
                    })
                except Exception as e:
                    print("[recognition_api] Socket emit failed:", e)

                # ESCAPED INMATE ALARM - send critical alert to all connected clients
                if is_escaped:
                    try:

                        # Emit escaped inmate alarm to ALL connected clients
                        socketio.emit('escaped_inmate_alarm', {
                            'inmate': inmate_payload,
                            'alert_id': alert_id,
                            'detection_location': {
                                'lat': detection_lat,
                                'lng': detection_lng
                            } if detection_lat and detection_lng else None,
                            'timestamp': datetime.utcnow().isoformat(),
                            'requires_acknowledgment': True
                        })
                        print(f"[recognition_api] ESCAPED INMATE ALARM triggered for {inmate_payload['name']}")

                        # Find and notify nearby facilities if location is known
                        if detection_lat and detection_lng:
                            nearby = find_nearby_facilities(detection_lat, detection_lng, radius_km=50)
                            for facility in nearby:
                                # Emit to specific user room (using user_id from dictionary)
                                socketio.emit('escaped_inmate_alarm', {
                                    'inmate': inmate_payload,
                                    'alert_id': alert_id,
                                    'distance_km': facility['distance_km'],
                                    'timestamp': datetime.utcnow().isoformat()
                                }, room=f"user_{facility['user_id']}")
                            print(f"[recognition_api] Notified {len(nearby)} nearby facilities")
                    except Exception as e:
                        print(f"[recognition_api] Failed to emit escaped alarm: {e}")

                return {
                    "status": "escaped_inmate_detected" if is_escaped else "match_found",
                    "inmate": inmate_payload,
                    "is_escaped": is_escaped,
                    "status_code": 200
                }
            else:
                # Low confidence match - not reliable enough to show
                return {
                    "status": "low_confidence",
                    "message": f"Possible match ({confidence}% confidence) but below {MIN_CONFIDENCE}% threshold",
                    "confidence": confidence,
                    "status_code": 200
                }

        # No match above threshold - include debug info to diagnose issue
        return {
            "status": "no_match",
            "best_distance": float(round(best_distance, 4)) if best_distance != float('inf') else None,
            "threshold": SIMILARITY_THRESHOLD,
            "num_inmates_compared": len(inmate_encodings),
            "top_3_matches": [
                {"inmate_id": m[0], "distance": float(round(m[1], 4))}
                for m in top_3_matches[:3]
            ] if top_3_matches else [],
            "input_feature_dim": len(input_features) if input_features is not None else 0,
            "debug_message": f"Best distance {best_distance:.4f} >= threshold {SIMILARITY_THRESHOLD}. Need distance < {SIMILARITY_THRESHOLD} for match.",
            "status_code": 200
        }

    except Exception as e:
        print("[recognition_api] ERROR during recognition:", e)
        import traceback
        traceback.print_exc()
        return {"error": str(e), "status_code": 500}


def _match_single_face(face_crop, inmate_encodings, original_frame=None):
    """
    Match a single face crop against inmate database.
    Supports periocular fusion matching for glasses/occlusion robustness.
    Returns match result dict or None.

    Args:
        face_crop: Cropped face image (128x128)
        inmate_encodings: List of (inmate_data, face_encodings, periocular_encodings) tuples
        original_frame: Original full frame for periocular extraction (optional)
    """
    try:
        # Generate query augmentations for robust matching
        query_augmentations = _generate_query_augmentations(face_crop)

        # Extract face embeddings for all augmentations
        query_embeddings = []
        for aug_img in query_augmentations:
            emb = extract_embedding_from_frame(aug_img)
            if emb is not None:
                query_embeddings.append(np.array(emb, dtype=np.float32))

        if not query_embeddings:
            return None

        # Try to extract periocular embedding
        query_periocular_emb = None
        glasses_detected = False
        glasses_confidence = 0.0

        if ENABLE_PERIOCULAR_FUSION:
            try:
                # Use face_crop for periocular (or original_frame if provided)
                img_for_periocular = original_frame if original_frame is not None else face_crop
                peri_result = extract_periocular_embedding(img_for_periocular)
                if peri_result and peri_result.get('embedding'):
                    query_periocular_emb = np.array(peri_result['embedding'], dtype=np.float32)
                    glasses_detected = peri_result.get('glasses_detected', False)
                    glasses_confidence = peri_result.get('glasses_confidence', 0.0)
            except Exception:
                pass

        # Find best match using cosine distance with optional periocular fusion
        best_match = None
        best_distance = float('inf')
        best_match_method = 'face_only'

        for inmate, face_encodings_list, periocular_encodings_list in inmate_encodings:
            try:
                # Compare query embeddings against inmate face embeddings
                min_face_dist = float('inf')
                for query_emb in query_embeddings:
                    for encoding in face_encodings_list:
                        dist = cosine(query_emb, encoding)
                        if dist < min_face_dist:
                            min_face_dist = dist

                # Apply periocular fusion if available
                final_distance = min_face_dist

                if (ENABLE_PERIOCULAR_FUSION and
                    query_periocular_emb is not None and
                    periocular_encodings_list):

                    min_peri_dist = float('inf')
                    for peri_enc in periocular_encodings_list:
                        peri_dist = cosine(query_periocular_emb, peri_enc)
                        if peri_dist < min_peri_dist:
                            min_peri_dist = peri_dist

                    fused_dist, _ = compute_fusion_score(
                        min_face_dist, min_peri_dist, glasses_detected, glasses_confidence
                    )
                    final_distance = fused_dist

                if final_distance < best_distance:
                    best_distance = final_distance
                    best_match = inmate
            except Exception:
                continue

        # Check if match is above threshold
        if best_match and best_distance < SIMILARITY_THRESHOLD:
            confidence = float(round((1 - best_distance) * 100, 1))
            if confidence >= MIN_CONFIDENCE:
                return {
                    "id": best_match["id"],
                    "inmate_id": best_match["inmate_id"],
                    "name": best_match["name"],
                    "status": best_match["status"],
                    "mugshot_path": best_match["mugshot_path"],
                    "risk_level": best_match["risk_level"],
                    "crime": best_match["crime"],
                    "confidence": confidence,
                    "distance": float(round(best_distance, 4)),
                    "glasses_detected": glasses_detected
                }

        return None

    except Exception as e:
        log(f"[multi-face] Error matching face: {e}")
        return None


def _match_face_with_precomputed_embeddings(face_embedding, periocular_embedding, glasses_detected, glasses_confidence, inmate_encodings):
    """
    Match a face against the inmate database using pre-computed embeddings.
    Supports periocular fusion for better accuracy with glasses/occlusion.

    Args:
        face_embedding: 512-dim face embedding (list or None)
        periocular_embedding: 512-dim periocular embedding (list or None)
        glasses_detected: Whether glasses were detected
        glasses_confidence: Confidence of glasses detection
        inmate_encodings: List of (inmate_data, face_encodings, periocular_encodings) tuples

    Returns:
        Match result dict or None
    """
    if face_embedding is None:
        return None

    query_face_emb = np.array(face_embedding, dtype=np.float32)
    query_peri_emb = np.array(periocular_embedding, dtype=np.float32) if periocular_embedding else None

    best_match = None
    best_distance = float('inf')
    match_method = 'face_only'

    for inmate, face_encodings_list, periocular_encodings_list in inmate_encodings:
        try:
            # Find minimum face distance
            min_face_dist = float('inf')
            for encoding in face_encodings_list:
                dist = cosine(query_face_emb, encoding)
                if dist < min_face_dist:
                    min_face_dist = dist

            # Apply periocular fusion if available
            final_distance = min_face_dist
            current_method = 'face_only'

            if (ENABLE_PERIOCULAR_FUSION and
                query_peri_emb is not None and
                periocular_encodings_list):

                min_peri_dist = float('inf')
                for peri_enc in periocular_encodings_list:
                    peri_dist = cosine(query_peri_emb, peri_enc)
                    if peri_dist < min_peri_dist:
                        min_peri_dist = peri_dist

                fused_dist, _ = compute_fusion_score(
                    min_face_dist, min_peri_dist, glasses_detected, glasses_confidence
                )
                final_distance = fused_dist
                current_method = 'fusion'

            if final_distance < best_distance:
                best_distance = final_distance
                best_match = inmate
                match_method = current_method

        except Exception:
            continue

    # Check if match is above threshold
    if best_match and best_distance < SIMILARITY_THRESHOLD:
        confidence = float(round((1 - best_distance) * 100, 1))
        if confidence >= MIN_CONFIDENCE:
            return {
                "id": best_match["id"],
                "inmate_id": best_match["inmate_id"],
                "name": best_match["name"],
                "status": best_match["status"],
                "mugshot_path": best_match["mugshot_path"],
                "risk_level": best_match["risk_level"],
                "crime": best_match["crime"],
                "confidence": confidence,
                "distance": float(round(best_distance, 4)),
                "glasses_detected": glasses_detected,
                "match_method": match_method
            }

    return None


def _run_multi_recognition(frame) -> dict:
    """
    Run recognition pipeline on ALL faces detected in frame using MTCNN.
    Uses periocular fusion for robust matching with glasses/occlusion.
    Returns a dict with list of all matched persons.

    Args:
        frame: BGR image
    """
    if frame is None:
        return {"error": "No valid image provided", "status_code": 400}

    try:
        # Use MTCNN multi-face detection via embedding service
        log("[multi-face] Calling MTCNN multi-face detection...")
        detection_result = detect_all_faces(frame)

        if detection_result is None:
            log("[multi-face] Embedding service unavailable, falling back to Haar Cascade")
            # Fallback to old Haar Cascade method
            face_data = _detect_all_faces(frame)
            if not face_data:
                log("[multi-face] No faces detected, falling back to single-face mode")
                return _run_recognition(frame, use_detection=False)
            # Process with old method (will use _match_single_face)
            return _run_multi_recognition_legacy(frame, face_data)

        if not detection_result.get('success', False):
            log(f"[multi-face] Detection failed: {detection_result.get('error', 'Unknown error')}")
            return _run_recognition(frame, use_detection=False)

        faces = detection_result.get('faces', [])
        total_detected = detection_result.get('total_faces', 0)

        if total_detected == 0:
            log("[multi-face] MTCNN detected no faces, falling back to single-face mode")
            return _run_recognition(frame, use_detection=False)

        log(f"[multi-face] MTCNN detected {total_detected} faces with embeddings")

        # Load cached inmate encodings
        inmate_encodings = _load_inmate_encodings()

        if not inmate_encodings:
            return {"error": "No inmate face encodings in database", "status_code": 500}

        # Process each detected face
        matches = []
        unmatched_faces = []
        escaped_inmates = []

        for face_data in faces:
            face_idx = face_data.get('face_index', 0)
            bbox = face_data.get('bbox', {})
            face_embedding = face_data.get('face_embedding')
            periocular_embedding = face_data.get('periocular_embedding')
            glasses_detected = face_data.get('glasses_detected', False)
            glasses_confidence = face_data.get('glasses_confidence', 0.0)
            detection_confidence = face_data.get('confidence', 0.0)

            log(f"[multi-face] Processing face {face_idx}: bbox={bbox}, glasses={glasses_detected}, periocular={'yes' if periocular_embedding else 'no'}")

            face_info = {
                "face_index": face_idx,
                "bbox": bbox,
                "detection_confidence": detection_confidence
            }

            # Match using pre-computed embeddings with periocular fusion
            match = _match_face_with_precomputed_embeddings(
                face_embedding,
                periocular_embedding,
                glasses_detected,
                glasses_confidence,
                inmate_encodings
            )

            if match:
                match["face_info"] = face_info
                matches.append(match)

                # Track escaped inmates
                if str(match.get("status", "")).lower() == "escaped":
                    escaped_inmates.append(match)
                    log(f"[multi-face] Face {face_idx}: ESCAPED INMATE - {match['name']} ({match['confidence']}%) [{match.get('match_method', 'unknown')}]")
                else:
                    log(f"[multi-face] Face {face_idx}: Match - {match['name']} ({match['confidence']}%) [{match.get('match_method', 'unknown')}]")
            else:
                unmatched_faces.append(face_info)
                log(f"[multi-face] Face {face_idx}: No match")

        # Determine overall status
        if escaped_inmates:
            status = "escaped_inmates_detected"
        elif matches:
            status = "matches_found"
        else:
            status = "no_matches"

        # Create alerts for escaped inmates
        for escaped in escaped_inmates:
            try:
                alert = Alert(
                    message=f"ESCAPED INMATE DETECTED: {escaped['name']} ({escaped['confidence']}% confidence)",
                    level="danger",
                    confidence=escaped['confidence'],
                    inmate_id=escaped["id"],
                    resolved=False
                )
                db.session.add(alert)
                db.session.commit()

                # Emit socket event
                socketio.emit('escaped_inmate_alarm', {
                    'inmate': escaped,
                    'alert_id': alert.id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'multi_face_detection': True,
                    'detection_method': 'mtcnn_periocular_fusion'
                })
            except Exception as e:
                log(f"[multi-face] Failed to create alert: {e}")
                db.session.rollback()

        # Emit general match event if any matches found
        if matches:
            try:
                socketio.emit('multi_face_match', {
                    'total_faces': total_detected,
                    'matched_count': len(matches),
                    'escaped_count': len(escaped_inmates),
                    'matches': [{'name': m['name'], 'confidence': m['confidence'], 'method': m.get('match_method', 'unknown')} for m in matches],
                    'detection_method': 'mtcnn_periocular_fusion'
                })
            except Exception as e:
                log(f"[multi-face] Socket emit failed: {e}")

        return {
            "status": status,
            "total_faces_detected": total_detected,
            "matched_count": len(matches),
            "unmatched_count": len(unmatched_faces),
            "matches": matches,
            "unmatched_faces": unmatched_faces,
            "has_escaped_inmates": len(escaped_inmates) > 0,
            "escaped_count": len(escaped_inmates),
            "detection_method": "mtcnn_periocular_fusion",
            "status_code": 200
        }

    except Exception as e:
        print("[recognition_api] ERROR during multi-recognition:", e)
        import traceback
        traceback.print_exc()
        return {"error": str(e), "status_code": 500}


def _run_multi_recognition_legacy(frame, face_data) -> dict:
    """
    Legacy multi-face recognition using Haar Cascade detected faces.
    Used as fallback when embedding service is unavailable.
    """
    log(f"[multi-face-legacy] Processing {len(face_data)} detected faces")

    inmate_encodings = _load_inmate_encodings()
    if not inmate_encodings:
        return {"error": "No inmate face encodings in database", "status_code": 500}

    matches = []
    unmatched_faces = []
    escaped_inmates = []

    for i, (face_crop, bbox) in enumerate(face_data):
        log(f"[multi-face-legacy] Processing face {i+1}/{len(face_data)}")

        match = _match_single_face(face_crop, inmate_encodings)

        face_info = {
            "face_index": i + 1,
            "bbox": {"x": bbox[0], "y": bbox[1], "width": bbox[2], "height": bbox[3]}
        }

        if match:
            match["face_info"] = face_info
            matches.append(match)

            if str(match.get("status", "")).lower() == "escaped":
                escaped_inmates.append(match)
                log(f"[multi-face-legacy] Face {i+1}: ESCAPED INMATE - {match['name']} ({match['confidence']}%)")
            else:
                log(f"[multi-face-legacy] Face {i+1}: Match - {match['name']} ({match['confidence']}%)")
        else:
            unmatched_faces.append(face_info)
            log(f"[multi-face-legacy] Face {i+1}: No match")

    if escaped_inmates:
        status = "escaped_inmates_detected"
    elif matches:
        status = "matches_found"
    else:
        status = "no_matches"

    for escaped in escaped_inmates:
        try:
            alert = Alert(
                message=f"ESCAPED INMATE DETECTED: {escaped['name']} ({escaped['confidence']}% confidence)",
                level="danger",
                confidence=escaped['confidence'],
                inmate_id=escaped["id"],
                resolved=False
            )
            db.session.add(alert)
            db.session.commit()
            socketio.emit('escaped_inmate_alarm', {
                'inmate': escaped,
                'alert_id': alert.id,
                'timestamp': datetime.utcnow().isoformat(),
                'multi_face_detection': True,
                'detection_method': 'haar_cascade_legacy'
            })
        except Exception as e:
            log(f"[multi-face-legacy] Failed to create alert: {e}")
            db.session.rollback()

    if matches:
        try:
            socketio.emit('multi_face_match', {
                'total_faces': len(face_data),
                'matched_count': len(matches),
                'escaped_count': len(escaped_inmates),
                'matches': [{'name': m['name'], 'confidence': m['confidence']} for m in matches],
                'detection_method': 'haar_cascade_legacy'
            })
        except Exception as e:
            log(f"[multi-face-legacy] Socket emit failed: {e}")

    return {
        "status": status,
        "total_faces_detected": len(face_data),
        "matched_count": len(matches),
        "unmatched_count": len(unmatched_faces),
        "matches": matches,
        "unmatched_faces": unmatched_faces,
        "has_escaped_inmates": len(escaped_inmates) > 0,
        "escaped_count": len(escaped_inmates),
        "detection_method": "haar_cascade_legacy",
        "status_code": 200
    }


@recognition_api_bp.route('/match', methods=['POST'])
@login_or_jwt_required
def recognize_face():
    """
    Accepts: multipart/form-data with file field 'frame'
    Predicts inmate ID with XGBoost using 3060-dim HOG features.
    Emits 'match_found' on success.
    """
    print("[recognition_api] /match endpoint called")
    frame = _decode_frame_from_request(request)
    print(f"[recognition_api] Frame decoded: {frame is not None}, shape: {frame.shape if frame is not None else 'None'}")
    result = _run_recognition(frame)
    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code


@recognition_api_bp.route('/upload', methods=['POST'])
@login_or_jwt_required
def upload_recognition():
    """
    Accepts: multipart/form-data with file field 'file'
    Alternative endpoint for the upload UI.

    Optional form field 'multi_face':
      - If 'true' or '1': Detect and match ALL faces in the image
      - Otherwise: Single-face mode (legacy behavior)
    """
    import os
    log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'upload_requests.log')
    with open(log_path, 'a') as f:
        f.write(f"\n[{datetime.now()}] /upload endpoint HIT\n")
        f.write(f"  Files in request: {list(request.files.keys())}\n")

    log("[recognition_api] /upload endpoint called")

    # Try 'file' first, then 'frame' as fallback
    frame = _decode_image_from_file_field(request, 'file')
    log(f"[recognition_api] Frame from 'file': {frame is not None}")
    if frame is None:
        frame = _decode_frame_from_request(request)

    if frame is None:
        return jsonify({"error": "No image uploaded (use 'file' or 'frame' field)"}), 400

    # Check for multi-face mode
    multi_face = request.form.get('multi_face', 'false').lower() in ('true', '1', 'yes')

    if multi_face:
        log("[recognition_api] Multi-face mode enabled")
        result = _run_multi_recognition(frame)
    else:
        # use_detection=False: Just resize, don't detect face (consistent with mugshot storage)
        result = _run_recognition(frame, use_detection=False)

    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code


@recognition_api_bp.route('/upload-multi', methods=['POST'])
@login_or_jwt_required
def upload_multi_recognition():
    """
    Multi-face recognition endpoint.
    Accepts: multipart/form-data with file field 'file'
    Detects ALL faces in the image and matches each against the database.

    Returns:
        {
            "status": "matches_found" | "escaped_inmates_detected" | "no_matches",
            "total_faces_detected": int,
            "matched_count": int,
            "unmatched_count": int,
            "matches": [
                {
                    "inmate_id": str,
                    "name": str,
                    "confidence": float,
                    "status": str,
                    "face_info": {"face_index": int, "bbox": {x, y, width, height}}
                },
                ...
            ],
            "unmatched_faces": [{"face_index": int, "bbox": {...}}, ...],
            "has_escaped_inmates": bool,
            "escaped_count": int
        }
    """
    log("[recognition_api] /upload-multi endpoint called")

    # Try 'file' first, then 'frame' as fallback
    frame = _decode_image_from_file_field(request, 'file')
    if frame is None:
        frame = _decode_frame_from_request(request)

    if frame is None:
        return jsonify({"error": "No image uploaded (use 'file' or 'frame' field)"}), 400

    log(f"[recognition_api] Multi-face recognition on image {frame.shape}")
    result = _run_multi_recognition(frame)
    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code