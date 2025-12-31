# app/routes/recognition_api.py
from flask import Blueprint, request, jsonify
from app.utils.auth_helpers import login_or_jwt_required
from app import socketio
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.extensions import db
from app.utils.hog_features import extract_hog_3060
from app.utils.geolocation import find_nearby_facilities, get_detection_location
from scipy.spatial.distance import cosine
from datetime import datetime

import numpy as np
import cv2
import os

recognition_api_bp = Blueprint('recognition_api', __name__, url_prefix='/api/recognition')

# Similarity threshold for matching (lower = stricter)
# CRITICAL: Very strict to prevent false identification of innocent people
SIMILARITY_THRESHOLD = 0.15  # Cosine distance threshold - only accept 85%+ similarity
MIN_CONFIDENCE = 85  # Minimum confidence percentage to show match

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


def _detect_and_crop_face(frame):
    """
    Detect face in frame and return cropped face image.
    Returns the cropped face or None if no face detected.
    For small images (likely mugshots), skip detection and use as-is.
    """
    if frame is None:
        return None

    # If image is small, assume it's already a face crop (like a mugshot)
    h, w = frame.shape[:2]
    if max(h, w) < 300:
        # Resize to standard size and return as-is
        return cv2.resize(frame, (128, 128))

    face_cascade = _get_face_cascade()

    # Convert to grayscale for detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Try multiple detection parameters for robustness (more lenient)
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
        return None

    # Take the largest face (closest to camera)
    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, fw, fh = largest_face

    # Add padding around face (20%)
    padding = int(max(fw, fh) * 0.2)
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(frame.shape[1], x + fw + padding)
    y2 = min(frame.shape[0], y + fh + padding)

    # Crop and resize to standard size (128x128 like mugshots)
    face_crop = frame[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, (128, 128))

    return face_resized

def _load_inmate_encodings():
    """Load all inmate face encodings from database."""
    global _inmate_cache, _cache_timestamp
    import time

    # Refresh cache every 60 seconds
    current_time = time.time()
    if _inmate_cache is None or _cache_timestamp is None or (current_time - _cache_timestamp) > 60:
        inmates = Inmate.query.filter(Inmate.face_encoding.isnot(None)).all()
        _inmate_cache = [(inmate, np.array(inmate.face_encoding)) for inmate in inmates if inmate.face_encoding is not None]
        _cache_timestamp = current_time
        print(f"[recognition_api] Loaded {len(_inmate_cache)} inmate encodings into cache")

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


def _run_recognition(frame) -> dict:
    """
    Run the recognition pipeline on a frame using similarity matching.
    Detects face first, then compares HOG features against stored inmate encodings.
    Returns a dict with status and result.
    """
    if frame is None:
        return {"error": "No valid image provided", "status_code": 400}

    try:
        # Detect and crop face first for better accuracy
        face_crop = _detect_and_crop_face(frame)

        if face_crop is None:
            return {
                "status": "no_face_detected",
                "error": "No face detected in image. Please ensure a face is visible.",
                "status_code": 200
            }

        # Extract HOG features from cropped face (not full image)
        input_features = extract_hog_3060(face_crop)

        # Load cached inmate encodings
        inmate_encodings = _load_inmate_encodings()

        if not inmate_encodings:
            return {"error": "No inmate face encodings in database", "status_code": 500}

        # Find best match using cosine distance
        best_match = None
        best_distance = float('inf')

        for inmate, encoding in inmate_encodings:
            try:
                dist = cosine(input_features, encoding)
                if dist < best_distance:
                    best_distance = dist
                    best_match = inmate
            except Exception:
                continue

        # Debug logging - shows best match distance for diagnosis
        print(f"[recognition_api] Best match: {best_match.inmate_id if best_match else 'None'}, distance: {best_distance:.4f}, threshold: {SIMILARITY_THRESHOLD}")

        # Check if match is above threshold
        if best_match and best_distance < SIMILARITY_THRESHOLD:
            confidence = float(round((1 - best_distance) * 100, 1))

            # Only show match if confidence is high enough
            if confidence >= MIN_CONFIDENCE:
                inmate_payload = {
                    "id": best_match.id,
                    "inmate_id": best_match.inmate_id,
                    "name": getattr(best_match, "name", None) or getattr(best_match, "full_name", None),
                    "status": getattr(best_match, "status", None),
                    "mugshot_path": getattr(best_match, "mugshot_path", None),
                    "risk_level": getattr(best_match, "risk_level", None),
                    "crime": getattr(best_match, "crime", None),
                    "confidence": confidence,
                }

                # Check if inmate is ESCAPED - trigger critical alarm
                is_escaped = str(inmate_payload.get("status", "")).lower() == "escaped"

                # Create Alert record with confidence score for tracking
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
                        inmate_id=best_match.id,
                        resolved=False
                    )
                    db.session.add(alert)
                    db.session.commit()
                    alert_id = alert.id
                    print(f"[recognition_api] Alert created with confidence {confidence}% - Escaped: {is_escaped}")
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
                        # Get camera_id from request if available
                        camera_id = request.form.get('camera_id') if hasattr(request, 'form') else None

                        # Get detection location
                        detection_lat, detection_lng = get_detection_location(camera_id)

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
                                # Emit to specific user room
                                socketio.emit('escaped_inmate_alarm', {
                                    'inmate': inmate_payload,
                                    'alert_id': alert_id,
                                    'distance_km': facility['distance_km'],
                                    'timestamp': datetime.utcnow().isoformat()
                                }, room=f"user_{facility['user'].id}")
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

        # No match above threshold
        return {
            "status": "no_match",
            "best_distance": float(round(best_distance, 3)) if best_distance != float('inf') else None,
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
    frame = _decode_frame_from_request(request)
    result = _run_recognition(frame)
    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code


@recognition_api_bp.route('/upload', methods=['POST'])
@login_or_jwt_required
def upload_recognition():
    """
    Accepts: multipart/form-data with file field 'file'
    Alternative endpoint for the upload UI.
    Predicts inmate ID with XGBoost using 3060-dim HOG features.
    """
    # Try 'file' first, then 'frame' as fallback
    frame = _decode_image_from_file_field(request, 'file')
    if frame is None:
        frame = _decode_frame_from_request(request)

    if frame is None:
        return jsonify({"error": "No image uploaded (use 'file' or 'frame' field)"}), 400

    result = _run_recognition(frame)
    status_code = result.pop("status_code", 200)
    return jsonify(result), status_code