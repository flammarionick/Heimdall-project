from flask import Blueprint, request, jsonify
from flask_socketio import emit
from app import socketio
import numpy as np
import cv2
import base64

recognition_bp = Blueprint('recognition_api', __name__, url_prefix='/api/recognition')

@recognition_bp.route('/match', methods=['POST'])
def recognize_face():
    if 'frame' not in request.files:
        return jsonify({"error": "No frame uploaded"}), 400

    frame_file = request.files['frame']
    npimg = np.frombuffer(frame_file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # 🚨 TODO: replace with real face recognition logic
    fake_match = True
    inmate_info = {
        "full_name": "John Doe",
        "camera_location": "Main Entrance"
    }

    if fake_match:
        socketio.emit('match_found', {
            'inmate_name': inmate_info['full_name'],
            'camera_location': inmate_info['camera_location']
        })

        return jsonify({"status": "match_found", "inmate": inmate_info}), 200
    else:
        return jsonify({"status": "no_match"}), 200

# app/routes/recognition_routes.py

from flask import Blueprint, render_template

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

@recognition_bp.route('/live')
def live_recognition():
    return render_template('recognition/live.html')


# app/routes/recognition_routes.py

from flask import Blueprint, render_template, request

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

@recognition_bp.route('/live')
def live_recognition():
    return render_template('recognition/live.html')

@recognition_bp.route('/upload', methods=['GET', 'POST'])
def upload_recognition():
    if request.method == 'POST':
        # Later: Handle uploaded file and do recognition here
        pass
    return render_template('recognition/upload.html')
