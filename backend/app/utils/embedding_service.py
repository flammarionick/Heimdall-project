from flask import Flask, request, jsonify
from facenet_pytorch import InceptionResnetV1
import torch
import numpy as np
from PIL import Image
import io
import cv2

app = Flask(__name__)

from app.utils.embedding import extract_embedding_from_frame  # if shared
# Load model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = np.array(img)
    img = cv2.resize(img, (160, 160)) / 255.0
    img = torch.tensor(img).permute(2, 0, 1).unsqueeze(0).float()
    return img.to(device)

@app.post("/encode")
def encode():
    # Try multipart first: files={"image": <file>}
    if "image" in request.files:
        raw = request.files["image"].read()
        nparr = np.frombuffer(raw, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        source = "multipart"
    else:
        # Then try JSON: {"image": "<base64 or data URL>"}
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(error="No image provided. Expect 'image' as multipart file or base64 JSON."), 400

        # Strip data URL header if present
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]

        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(error="Invalid base64 image."), 400

        nparr = np.frombuffer(raw, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        source = "json"

    if frame is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    embedding = extract_embedding_from_frame(frame)
    if embedding is None:
        return jsonify(error="No face detected or embedding failed."), 422

    return jsonify(embedding=embedding.tolist()), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)