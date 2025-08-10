# embedding_service.py  (standalone microservice)
from flask import Flask, request, jsonify
import base64
import io
import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1
from PIL import Image

app = Flask(__name__)

# Load FaceNet backbone once
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def preprocess_image_bytes(image_bytes):
    """Return a 160x160 tensor batch on the correct device."""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = img.resize((160, 160))
    arr = np.array(img).astype(np.float32) / 255.0  # HWC [0,1]
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # 1x3x160x160
    return tensor.to(device)

@app.post("/encode")
def encode():
    # Multipart first
    if "image" in request.files:
        raw = request.files["image"].read()
        source = "multipart"
    else:
        # JSON: {"image": "data:image/jpeg;base64,..."} or pure base64
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(error="No image provided. Expect 'image' as multipart file or base64 JSON."), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(error="Invalid base64 image."), 400
        source = "json"

    # Sanity check
    nparr = np.frombuffer(raw, np.uint8)
    if cv2.imdecode(nparr, cv2.IMREAD_COLOR) is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    # Forward pass
    try:
        x = preprocess_image_bytes(raw)
        with torch.no_grad():
            emb = model(x).cpu().numpy()[0]   # (512,)
    except Exception as e:
        return jsonify(error=f"Embedding failed: {e}"), 500

    return jsonify(embedding=emb.tolist()), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)