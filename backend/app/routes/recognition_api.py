from flask import Blueprint, request, jsonify
from flask_socketio import emit
from app import socketio
import numpy as np
import cv2

recognition_api_bp = Blueprint('recognition_api', __name__, url_prefix='/api/recognition')

@recognition_api_bp.route('/match', methods=['POST'])
def recognize_face():
    if 'frame' not in request.files:
        return jsonify({"error": "No frame uploaded"}), 400

    frame_file = request.files['frame']
    npimg = np.frombuffer(frame_file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # Replace this with real face recognition logic
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
