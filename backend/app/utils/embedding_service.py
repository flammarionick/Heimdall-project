# embedding_service.py  (standalone microservice)
# Enhanced with MTCNN face detection and robust preprocessing
from flask import Flask, request, jsonify
import base64
import io
import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from PIL import Image

app = Flask(__name__)

# Load models once at startup
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Embedding service using device: {device}")

# FaceNet model for embeddings
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# MTCNN for robust face detection (handles rotation, poses, partial occlusion)
mtcnn = MTCNN(
    image_size=160,
    margin=20,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7],  # Detection thresholds for 3 stages
    factor=0.709,
    post_process=True,
    select_largest=True,  # Select largest face if multiple detected
    keep_all=False,
    device=device
)


def apply_clahe(image_bgr):
    """Apply CLAHE for contrast enhancement."""
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def normalize_exposure(image_bgr):
    """Normalize image brightness."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    current_brightness = np.mean(v)

    if current_brightness < 50:
        alpha = 1.5
        beta = 30
    elif current_brightness > 200:
        alpha = 0.7
        beta = -20
    else:
        alpha = 127 / max(current_brightness, 1)
        alpha = np.clip(alpha, 0.7, 1.5)
        beta = 0

    v = cv2.convertScaleAbs(v, alpha=alpha, beta=beta)
    hsv = cv2.merge([h, s, v])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def preprocess_image(image_bytes):
    """
    Preprocess image with robust handling for distortions.
    Returns PIL Image in RGB format ready for MTCNN.
    """
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return None

    # Handle grayscale images
    if len(img_bgr.shape) == 2:
        img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)

    # Apply preprocessing
    img_bgr = normalize_exposure(img_bgr)
    img_bgr = apply_clahe(img_bgr)

    # Convert to RGB for MTCNN
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)


def extract_face_mtcnn(pil_image):
    """
    Use MTCNN to detect and align face.
    Returns face tensor ready for FaceNet, or None if no face detected.
    """
    # MTCNN returns aligned face tensor directly
    face_tensor = mtcnn(pil_image)
    return face_tensor


def preprocess_fallback(pil_image):
    """
    Fallback preprocessing when MTCNN fails to detect a face.
    Assumes the image is already a face crop.
    """
    img = pil_image.resize((160, 160))
    arr = np.array(img).astype(np.float32)

    # Normalize to [-1, 1] range (FaceNet expects this)
    arr = (arr - 127.5) / 128.0

    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # 1x3x160x160
    return tensor.to(device)


@app.post("/encode")
def encode():
    """
    Encode a face image to a 512-dimensional embedding.
    Handles multipart file upload or base64 JSON.
    """
    # Get image data
    if "image" in request.files:
        raw = request.files["image"].read()
        source = "multipart"
    else:
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

    # Preprocess image
    pil_image = preprocess_image(raw)
    if pil_image is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    # Try MTCNN face detection first
    try:
        face_tensor = extract_face_mtcnn(pil_image)

        if face_tensor is not None:
            # MTCNN succeeded - use aligned face
            face_tensor = face_tensor.unsqueeze(0).to(device)
            with torch.no_grad():
                emb = model(face_tensor).cpu().numpy()[0]
            return jsonify(embedding=emb.tolist(), method="mtcnn"), 200
        else:
            # MTCNN failed - use fallback (assume image is already face crop)
            face_tensor = preprocess_fallback(pil_image)
            with torch.no_grad():
                emb = model(face_tensor).cpu().numpy()[0]
            return jsonify(embedding=emb.tolist(), method="fallback"), 200

    except Exception as e:
        return jsonify(error=f"Embedding failed: {e}"), 500


@app.post("/encode_multiple")
def encode_multiple():
    """
    Encode multiple augmented versions of a face.
    Expects JSON with 'images' array of base64 encoded images.
    Returns array of embeddings.
    """
    data = request.get_json(silent=True) or {}
    images_b64 = data.get("images", [])

    if not images_b64:
        return jsonify(error="No images provided. Expect 'images' array of base64 strings."), 400

    embeddings = []

    for i, img_b64 in enumerate(images_b64):
        try:
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            raw = base64.b64decode(img_b64)

            pil_image = preprocess_image(raw)
            if pil_image is None:
                embeddings.append(None)
                continue

            face_tensor = extract_face_mtcnn(pil_image)
            if face_tensor is not None:
                face_tensor = face_tensor.unsqueeze(0).to(device)
            else:
                face_tensor = preprocess_fallback(pil_image)

            with torch.no_grad():
                emb = model(face_tensor).cpu().numpy()[0]
            embeddings.append(emb.tolist())

        except Exception as e:
            print(f"Error encoding image {i}: {e}")
            embeddings.append(None)

    return jsonify(embeddings=embeddings), 200


@app.get("/health")
def health():
    """Health check endpoint."""
    return jsonify(status="ok", device=str(device)), 200


if __name__ == "__main__":
    print("Starting embedding service with MTCNN face detection...")
    app.run(host="127.0.0.1", port=5001)