# app/routes/recognition_api.py
from flask import Blueprint, request, jsonify
from app.utils.auth_helpers import login_or_jwt_required
from app import socketio
from app.models.inmate import Inmate
from app.extensions import db  # if you need DB in future
from app.utils.hog_features import extract_hog_3060

import numpy as np
import cv2
import os
import pickle

recognition_api_bp = Blueprint('recognition_api', __name__, url_prefix='/api/recognition')

# ---- Load XGBoost model once ----
MODEL_PATH = os.getenv("XGB_MODEL_PATH", "app/models/best_xgb_model.pkl")
try:
    with open(MODEL_PATH, "rb") as f:
        xgb_model = pickle.load(f)
    print(f"[recognition_api] Loaded XGBoost model from: {MODEL_PATH}")
except Exception as e:
    xgb_model = None
    print(f"[recognition_api] ERROR loading XGBoost model at {MODEL_PATH}: {e}")

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

@recognition_api_bp.route('/match', methods=['POST'])
@login_or_jwt_required
def recognize_face():
    """
    Accepts: multipart/form-data with file field 'frame'
    Predicts inmate ID with XGBoost using 3060-dim HOG features.
    Emits 'match_found' on success.
    """
    if xgb_model is None:
        return jsonify({"error": "Recognition model not loaded on server"}), 500

    frame = _decode_frame_from_request(request)
    if frame is None:
        return jsonify({"error": "No frame uploaded (multipart key 'frame' is required)"}), 400

    try:
        # 3060-dim features expected by your XGBoost model
        features = extract_hog_3060(frame)

        pred_id = int(xgb_model.predict([features])[0])
        inmate = Inmate.query.get(pred_id)

        if inmate:
            # Build a compact payload (adapt to your Inmate schema fields)
            inmate_payload = {
                "id": inmate.id,
                "name": getattr(inmate, "name", None) or getattr(inmate, "full_name", None),
                "prison_id": getattr(inmate, "prison_id", None),
                "status": getattr(inmate, "status", None),
                "mugshot_path": getattr(inmate, "mugshot_path", None),
            }

            # Real-time event for dashboards
            try:
                socketio.emit('match_found', {
                    'inmate_name': inmate_payload["name"],
                    'inmate_id': inmate_payload["id"]
                })
            except Exception as e:
                print("[recognition_api] Socket emit failed:", e)

            return jsonify({"status": "match_found", "inmate": inmate_payload}), 200

        # Predicted an ID that doesn't exist in DB
        return jsonify({"status": "no_match", "predicted_id": pred_id}), 200

    except Exception as e:
        print("[recognition_api] ERROR during recognition:", e)
        return jsonify({"error": str(e)}), 500