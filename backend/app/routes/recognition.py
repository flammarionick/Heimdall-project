# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models.inmate import Inmate
from app.forms import UploadFaceForm
from app.utils.embedding_client import extract_embedding_from_frame
from app import db

import numpy as np
import cv2
import pickle
import base64
import logging
from typing import Optional

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

# Marker so you can confirm the right file is loaded in logs.
logging.getLogger().warning("[recognition] Loaded: NO history-table version")

# === Load XGBoost model once ===
with open('app/models/best_xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

# Your older model wanted 3060 features; fall back to that if attribute not present.
DEFAULT_EXPECTED_DIM = 3060
EXPECTED_DIM = getattr(xgb_model, 'n_features_in_', DEFAULT_EXPECTED_DIM)


def _adapt_vector_dim(vec: np.ndarray, target_dim: int) -> np.ndarray:
    """
    Ensure 1D vector 'vec' is exactly 'target_dim' long:
      - If shorter: zero-pad at the end
      - If longer : truncate
    Returns shape (target_dim,)
    """
    v = np.asarray(vec, dtype=float).ravel()
    if v.size == target_dim:
        return v
    if v.size < target_dim:
        out = np.zeros(target_dim, dtype=float)
        out[:v.size] = v
        return out
    return v[:target_dim]


def _extract_embedding_from_upload(file_storage) -> Optional[np.ndarray]:
    """
    Reads uploaded image (FileStorage), decodes to BGR frame, calls embedding service,
    returns numpy array embedding (e.g., 512-d from FaceNet). Returns None on failure.
    """
    try:
        file_storage.stream.seek(0)
        file_bytes = np.frombuffer(file_storage.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        emb = extract_embedding_from_frame(frame)  # list[float] from /encode
        if emb is None:
            return None
        return np.array(emb, dtype=float)
    except Exception as e:
        logging.exception("Embedding extraction failed: %s", e)
        return None


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
            # 1) Extract embedding (typically 512-d)
            embedding = _extract_embedding_from_upload(file)
            if embedding is None:
                flash('Embedding extraction failed (no face detected?).', 'danger')
                return redirect(request.url)

            # 2) Adapt to model's expected dimension (e.g., 3060)
            emb_vec = _adapt_vector_dim(embedding, EXPECTED_DIM)

            # 3) Predict ID
            predicted_id = int(xgb_model.predict(emb_vec.reshape(1, -1))[0])

            # 4) Find inmate and save latest embedding directly on inmate.face_encoding
            matched_inmate = Inmate.query.get(predicted_id)
            if matched_inmate:
                try:
                    matched_inmate.face_encoding = embedding.tolist()  # store original 512-d vector
                    db.session.commit()
                except Exception as e:
                    logging.warning("Could not update Inmate.face_encoding: %s", e)
                    db.session.rollback()

                display_name = getattr(matched_inmate, "full_name", None) or getattr(matched_inmate, "name", f"ID {predicted_id}")
                flash(f'Match found: {display_name}', 'success')
            else:
                flash('No matching inmate found for predicted ID.', 'warning')

        except Exception as e:
            logging.exception("[ERROR during recognition]: %s", e)
            db.session.rollback()
            flash('Recognition failed. Please try again.', 'danger')

        return redirect(url_for('recognition.upload_recognition'))

    return render_template('recognition/upload.html', form=form)


# === Web Route: Live recognition placeholder ===
@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')


# === API Endpoint: base64 image -> embedding -> identity prediction (also save on inmate) ===
@recognition_bp.route('/api/predict', methods=['POST'])
def predict_identity_api():
    data = request.get_json() or {}
    if 'image' not in data:
        return jsonify({"error": "No image provided"}), 400

    # Accept data URLs and plain base64
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

    # 1) Extract embedding
    embedding_list = extract_embedding_from_frame(frame)
    if embedding_list is None:
        return jsonify({"error": "Failed to extract embedding"}), 500

    try:
        embedding = np.array(embedding_list, dtype=float)
        emb_vec = _adapt_vector_dim(embedding, EXPECTED_DIM)

        # 2) Predict identity
        pred_id = int(xgb_model.predict(emb_vec.reshape(1, -1))[0])

        # 3) Save/update embedding on the matched inmate (if exists)
        payload = {"predicted_id": pred_id, "inmate": None}
        inmate = Inmate.query.get(pred_id)
        if inmate:
            try:
                inmate.face_encoding = embedding.tolist()
                db.session.commit()
            except Exception as e:
                logging.warning("Could not update Inmate.face_encoding: %s", e)
                db.session.rollback()

            payload["inmate"] = {
                "id": inmate.id,
                "name": getattr(inmate, "full_name", None) or getattr(inmate, "name", None),
                "status": getattr(inmate, "status", None),
            }

        return jsonify(payload), 200

    except Exception as e:
        logging.exception("Prediction error: %s", e)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500