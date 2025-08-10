# app/utils/embedding_client.py
import os
import cv2
import base64
import requests

EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://127.0.0.1:5001/encode")

def extract_embedding_from_frame(frame):
    """
    Takes a BGR OpenCV frame and returns an embedding list from the embedding service.
    Returns None if encoding/HTTP fails or the service returns no embedding.
    """
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return None

    b64 = base64.b64encode(buf).decode("ascii")
    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        resp = requests.post(EMBEDDING_URL, json=payload, timeout=40)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    data = resp.json()
    return data.get("embedding")