from flask import Blueprint, request, jsonify
import base64
import cv2
import numpy as np

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/recognize', methods=['POST'])
def recognize():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"message": "No image provided."}), 400

    try:
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # TODO: Add OpenCV recognition here
        print("[API] Frame received:", frame.shape)
        return jsonify({"message": "Face processed (stub)", "status": "success"})
    except Exception as e:
        print("[API ERROR]", e)
        return jsonify({"message": "Error processing image"}), 500
