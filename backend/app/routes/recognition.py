# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.models import Inmate
from app.forms import UploadFaceForm
from app.utils.embedding import extract_embedding_from_frame
from app.models.facial_embedding import FacialEmbedding
import numpy as np
import cv2
import pickle
import base64

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

# === Load XGBoost model once ===
with open('app/models/best_xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)


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
            # Read and decode image
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            # Extract embedding using FaceNet
            embedding = extract_embedding_from_frame(img)
            if embedding is None:
                flash('Embedding extraction failed.', 'danger')
                return redirect(request.url)

            # Predict ID
            predicted_id = xgb_model.predict([embedding])[0]

            # Match inmate
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


# === Web Route: Live recognition placeholder ===
@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')


# === API Endpoint: base64 image -> embedding -> identity prediction + save ===
@recognition_bp.route('/api/predict', methods=['POST'])
def predict_identity_api():
    data = request.get_json()
    if 'image' not in data:
        return jsonify({"error": "No image provided"}), 400

    try:
        # Decode base64 image
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"error": "Invalid image format", "details": str(e)}), 400

    # Extract embedding
    embedding = extract_embedding_from_frame(frame)
    if embedding is None:
        return jsonify({"error": "Failed to extract embedding"}), 500

    try:
        # Predict identity
        pred_id = xgb_model.predict([embedding])[0]

        # Save to DB
        embedding_record = FacialEmbedding(
            embedding=embedding,
            predicted_id=pred_id,
            camera_id=data.get('camera_id')  # Optional: React frontend should send this if available
        )
        db.session.add(embedding_record)
        db.session.commit()

        return jsonify({"predicted_id": int(pred_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
