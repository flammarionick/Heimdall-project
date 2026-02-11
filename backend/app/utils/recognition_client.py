# utils/recognition_client.py
import base64
import requests
import cv2
import numpy as np

def send_frame_for_recognition(frame, camera_id=None):
    # Encode image to base64
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_image = base64.b64encode(buffer).decode('utf-8')
    payload = {
        "image": f"data:image/jpeg;base64,{encoded_image}",
        "camera_id": camera_id
    }

    try:
        response = requests.post("http://localhost:5000/recognition/api/predict", json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}
