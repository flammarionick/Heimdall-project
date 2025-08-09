# app/utils/embedding_client.py
import os
import cv2
import base64
import requests

EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://127.0.0.1:5001/encode")

def extract_embedding_from_frame(frame):
    """
    Takes a BGR OpenCV frame and returns a Python list embedding from the embedding service.
    Raises for HTTP errors. Returns None if embedding missing.
    """
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return None

    b64 = base64.b64encode(buf).decode("ascii")
    # Service expects { "image": "data:image/jpeg;base64,..." } (matches your register route usage)
    payload = {"image": f"data:image/jpeg;base64,{b64}"}
    resp = requests.post(EMBEDDING_URL, json=payload, timeout=40)
    resp.raise_for_status()
    data = resp.json()
    return data.get("embedding")