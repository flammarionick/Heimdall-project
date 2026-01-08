# app/routes/recognition_api.py
from flask import Blueprint, request, jsonify
from app.utils.auth_helpers import login_or_jwt_required
from app import socketio
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.active_recognition import ActiveRecognition
from app.extensions import db
from app.utils.embedding_client import extract_embedding_from_frame
from app.utils.geolocation import find_nearby_facilities, get_detection_location, haversine_distance
from app.utils.image_preprocessing import aggressive_denoise, deblur_image, strong_deblur
from scipy.spatial.distance import cosine
from datetime import datetime, timedelta

import numpy as np
import cv2
import os
import sys

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

def _load_inmate_encodings():
    """
    Load all inmate face encodings from database.
    Supports both legacy single encoding and multi-embeddings.
    Returns list of (inmate_data, [encodings]) tuples.
    """
    global _inmate_cache, _cache_timestamp
    import time
    import json

    # Refresh cache every 30 seconds (reduced for faster updates after new inmates)
    current_time = time.time()
    if _inmate_cache is None or _cache_timestamp is None or (current_time - _cache_timestamp) > 30:
        try:
            # Use a fresh query and extract data immediately
            # Select columns including multi-embeddings
            inmates = db.session.query(
                Inmate.id,
                Inmate.inmate_id,
                Inmate.name,
                Inmate.status,
                Inmate.mugshot_path,
                Inmate.risk_level,
                Inmate.crime,
                Inmate.face_encoding,
                Inmate.face_encodings_json
            ).filter(
                db.or_(
                    Inmate.face_encoding.isnot(None),
                    Inmate.face_encodings_json.isnot(None)
                )
            ).all()

            # Cache as plain data with list of all encodings per inmate
            new_cache = []
            total_encodings = 0
            for row in inmates:
                encodings = []

                # Add legacy single encoding if exists
                if row.face_encoding is not None:
                    encodings.append(np.array(row.face_encoding, dtype=np.float32))

                # Add multi-embeddings if exists
                if row.face_encodings_json:
                    try:
                        multi_enc = json.loads(row.face_encodings_json)
                        for enc in multi_enc:
                            if enc is not None:
                                encodings.append(np.array(enc, dtype=np.float32))
                    except (json.JSONDecodeError, TypeError):
                        pass

                if encodings:
                    inmate_data = {
                        "id": row.id,
                        "inmate_id": row.inmate_id,
                        "name": row.name,
                        "status": row.status,
                        "mugshot_path": row.mugshot_path,
                        "risk_level": row.risk_level,
                        "crime": row.crime,
                    }
                    new_cache.append((inmate_data, encodings))
                    total_encodings += len(encodings)

            _inmate_cache = new_cache
            _cache_timestamp = current_time
            print(f"[recognition_api] Loaded {len(_inmate_cache)} inmates with {total_encodings} total encodings into cache")
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
    Handles rotated, grayscale, exposure-changed, noisy, and blurred images.
    """
    augmentations = [face_crop]
    h, w = face_crop.shape[:2]
    center = (w // 2, h // 2)

    # Counter-rotations (including 180 for upside-down images)
    for angle in [-20, -10, 10, 20, 90, 180, 270]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(face_crop, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmentations.append(rotated)

    # Grayscale
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    augmentations.append(gray_bgr)

    # Exposure corrections
    bright = cv2.convertScaleAbs(face_crop, alpha=1.3, beta=30)
    dark = cv2.convertScaleAbs(face_crop, alpha=0.7, beta=-30)
    augmentations.append(bright)
    augmentations.append(dark)

    # CLAHE normalization
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    clahe_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    augmentations.append(clahe_img)

    # Grayscale + rotation
    M = cv2.getRotationMatrix2D(center, 15, 1.0)
    gray_rot = cv2.warpAffine(gray_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    augmentations.append(gray_rot)

    # === NEW: Noise reduction augmentations ===
    # Aggressive denoising for noisy images
    try:
        denoised = aggressive_denoise(face_crop)
        augmentations.append(denoised)

        # Denoised + CLAHE for noisy dark images
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        denoised_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        augmentations.append(denoised_clahe)
    except Exception:
        pass  # Skip if denoising fails

    # === NEW: Deblurring augmentations ===
    # Sharpening for blurred images
    try:
        sharpened = deblur_image(face_crop)
        augmentations.append(sharpened)

        # Strong sharpening for heavily blurred images
        strong_sharp = strong_deblur(face_crop)
        augmentations.append(strong_sharp)

        # Deblurred + denoised (for combined distortions)
        deblur_denoise = aggressive_denoise(sharpened)
        augmentations.append(deblur_denoise)
    except Exception:
        pass  # Skip if deblurring fails

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
        log(f"[recognition_api] Got {len(query_embeddings)} query embeddings (FaceNet 512-dim)")

        # Load cached inmate encodings
        inmate_encodings = _load_inmate_encodings()

        if not inmate_encodings:
            return {"error": "No inmate face encodings in database", "status_code": 500}

        log(f"[recognition_api] Comparing against {len(inmate_encodings)} cached inmates")

        # Find best match using cosine distance
        # Now supports multiple embeddings per inmate for robust matching
        best_match = None
        best_distance = float('inf')
        top_3_matches = []

        for inmate, encodings_list in inmate_encodings:
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
                    best_match = inmate
            except Exception as e:
                print(f"[recognition_api] Error comparing with {inmate['inmate_id']}: {e}")
                continue

        # Sort and show top 3 matches for debugging
        top_3_matches.sort(key=lambda x: x[1])
        log(f"[recognition_api] Top 3 matches (multi-embedding): {[(m[0], f'{m[1]:.4f}', f'{m[2]} enc') for m in top_3_matches[:3]]}")
        log(f"[recognition_api] Best match: {best_match['inmate_id'] if best_match else 'None'}, distance: {best_distance:.4f}, threshold: {SIMILARITY_THRESHOLD}")

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
    Uses use_detection=False to ensure consistent processing with stored mugshots.
    """
    # Write to file immediately to confirm request arrived
    import os
    log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'upload_requests.log')
    with open(log_path, 'a') as f:
        from datetime import datetime
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

    # use_detection=False: Just resize, don't detect face (consistent with mugshot storage)
    result = _run_recognition(frame, use_detection=False)
    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code