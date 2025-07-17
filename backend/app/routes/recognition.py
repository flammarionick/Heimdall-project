# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models import Inmate
from app.forms import UploadFaceForm
import numpy as np
import cv2
import pickle
import base64

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

# === Load the XGBoost model once ===
with open('models/best_xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

# === Utility to extract embedding from uploaded image (stub for now) ===
def extract_embedding_from_image(file_storage):
    # Read image
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # TODO: Replace this with actual embedding extraction logic
    # For now, return a dummy 128-dim vector for testing
    dummy_embedding = np.random.rand(128)
    return dummy_embedding

# === Web form route for uploading face image ===
@recognition_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recognition():
    form = UploadFaceForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            file = form.file.data
            if not file:
                flash('No file uploaded.', 'danger')
                return redirect(request.url)

            try:
                # Extract embedding from uploaded image
                embedding = extract_embedding_from_image(file)

                # Predict ID using model
                predicted_id = xgb_model.predict([embedding])[0]

                # Try to match with inmate info
                matched_inmate = Inmate.query.get(predicted_id)

                if matched_inmate:
                    flash(f'Match found: {matched_inmate.full_name}', 'success')
                else:
                    flash('No matching inmate found for predicted ID.', 'warning')

            except Exception as e:
                print("[ERROR during recognition]:", e)
                flash('Recognition failed. Please try again.', 'danger')

            return redirect(url_for('recognition.upload_recognition'))

    return render_template('recognition/upload.html', form=form)

# === Live recognition placeholder ===
@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')

# === API Endpoint for embedding-based prediction (for frontend/React use) ===
@recognition_bp.route('/api/predict', methods=['POST'])
def predict_identity_api():
    data = request.get_json()
    embedding = np.array(data.get('embedding'))

    if embedding is None:
        return jsonify({"error": "No embedding provided"}), 400

    try:
        pred_id = xgb_model.predict([embedding])[0]
        return jsonify({"predicted_id": int(pred_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
