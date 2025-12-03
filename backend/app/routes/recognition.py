# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models.inmate import Inmate
from app.forms import UploadFaceForm
from app import db

import numpy as np
import cv2
import pickle
import base64
import logging
from typing import Optional, Tuple

from app.utils.hog_features import extract_hog_3060

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

# === Load XGBoost model once ===
with open('app/models/best_xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

EXPECTED_DIM = getattr(xgb_model, 'n_features_in_', 3060)  # should be 3060

# Try to discover label mapping (index -> actual label)
CLASSES = getattr(xgb_model, 'classes_', None)

# Face detector (OpenCV’s Haar cascade)
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


def _adapt_vector_dim(vec: np.ndarray, target_dim: int) -> np.ndarray:
    v = np.asarray(vec, dtype=float).ravel()
    if v.size == target_dim:
        return v
    if v.size < target_dim:
        out = np.zeros(target_dim, dtype=float)
        out[:v.size] = v
        return out
    return v[:target_dim]


def _detect_face_crop(bgr: np.ndarray) -> np.ndarray:
    """
    Return a face-cropped region (BGR). If no face found, fall back to a centered crop.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    if len(faces) > 0:
        # pick the largest face
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        pad = int(0.15 * max(w, h))
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(bgr.shape[1], x + w + pad)
        y2 = min(bgr.shape[0], y + h + pad)
        crop = bgr[y1:y2, x1:x2]
        if crop.size > 0:
            return crop

    # fallback: centered square crop
    h, w = bgr.shape[:2]
    side = min(h, w)
    cy, cx = h // 2, w // 2
    half = side // 2
    return bgr[cy - half:cy + half, cx - half:cx + half]


def _preprocess_for_hog(bgr: np.ndarray) -> np.ndarray:
    """
    Crop to face, normalize, equalize, then HOG.
    """
    face = _detect_face_crop(bgr)

    # light normalization
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.equalizeHist(face)
    face = cv2.cvtColor(face, cv2.COLOR_GRAY2BGR)

    feat = extract_hog_3060(face)  # returns float32 length 3060
    feat = _adapt_vector_dim(feat, EXPECTED_DIM)
    return feat


def _predict_with_conf(
    feature_vec: np.ndarray, proba_threshold: float = 0.35
) -> Tuple[Optional[int], Optional[float]]:
    """
    Return (mapped_inmate_id_or_class, confidence). If below threshold, return (None, conf).
    """
    X = feature_vec.reshape(1, -1)

    conf = None
    try:
        proba = xgb_model.predict_proba(X)
        conf = float(np.max(proba))
        pred_idx = int(np.argmax(proba))
        pred_label = int(CLASSES[pred_idx]) if CLASSES is not None else int(pred_idx)
        if conf < proba_threshold:
            return None, conf
        return pred_label, conf
    except Exception:
        pred = xgb_model.predict(X)[0]
        pred_label = int(pred)
        return pred_label, None


# === Web Route: Upload image and predict identity ===
@recognition_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recognition():
    form = UploadFaceForm()

    if request.method == 'POST' and form.validate_on_submit():
        file = form.file.data
        if not file:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)

        try:
            file.stream.seek(0)
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None:
                flash('Could not decode image.', 'danger')
                return redirect(request.url)

            feat = _preprocess_for_hog(img)
            predicted_id, conf = _predict_with_conf(feat, proba_threshold=0.35)

            if predicted_id is None:
                flash('No confident match found.', 'warning')
                return redirect(url_for('recognition.upload_recognition'))

            matched_inmate = Inmate.query.get(predicted_id)
            if matched_inmate:
                display_name = (
                    getattr(matched_inmate, "full_name", None)
                    or getattr(matched_inmate, "name", f"ID {predicted_id}")
                )
                if conf is not None:
                    flash(f'Match: {display_name} (confidence {conf:.2f})', 'success')
                else:
                    flash(f'Match: {display_name}', 'success')
            else:
                flash(
                    f'Predicted ID {predicted_id}, but no inmate with that DB id.',
                    'warning',
                )

        except Exception as e:
            logging.exception("[ERROR during recognition]: %s", e)
            flash('Recognition failed. Please try again.', 'danger')

        return redirect(url_for('recognition.upload_recognition'))

    return render_template('recognition/upload.html', form=form)


# === Web Route: Live recognition page (used by layout.html menu) ===
@recognition_bp.route('/live')
@login_required
def live_recognition():
    """
    Simple page shell; your React or JS client can consume /recognition/api/predict etc.
    """
    return render_template('recognition/live.html')


# === API Endpoint: base64 image -> prediction ===
@recognition_bp.route('/api/predict', methods=['POST'])
def predict_identity_api():
    data = request.get_json() or {}
    if 'image' not in data:
        return jsonify({"error": "No image provided"}), 400

    try:
        image_b64 = data['image']
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        image_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "Invalid image content"}), 400
    except Exception as e:
        return jsonify({"error": "Invalid image format", "details": str(e)}), 400

    try:
        feat = _preprocess_for_hog(frame)
        predicted_id, conf = _predict_with_conf(feat, proba_threshold=0.35)
        if predicted_id is None:
            return jsonify({"status": "no_confident_match", "confidence": conf}), 200

        return jsonify({"predicted_id": predicted_id, "confidence": conf})
    except Exception as e:
        logging.exception("Prediction error: %s", e)
        return jsonify({"error": str(e)}), 500