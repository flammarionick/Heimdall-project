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
# Single-face detector (for backward compatibility)
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

# Multi-face detector (detects ALL faces in an image)
mtcnn_multi = MTCNN(
    image_size=160,
    margin=20,
    min_face_size=40,
    thresholds=[0.5, 0.6, 0.6],  # Slightly lower thresholds for better detection
    factor=0.709,
    post_process=True,
    select_largest=False,
    keep_all=True,  # Return ALL detected faces
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


def remove_salt_pepper_noise(image_bgr, kernel_size=5):
    """Remove salt & pepper noise using median filter.

    Median filter is optimal for impulse noise because it replaces
    outlier pixels with the median of neighbors.
    """
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.medianBlur(image_bgr, kernel_size)


def detect_salt_pepper_level(image_bgr):
    """Detect the level of salt & pepper noise in an image."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    total_pixels = gray.size

    # Use morphological operations to detect isolated bright/dark pixels
    kernel = np.ones((3, 3), np.uint8)

    # Detect isolated salt (white) pixels
    inv = 255 - gray
    eroded_inv = cv2.erode(inv, kernel, iterations=1)
    isolated_salt = np.sum((gray == 255) & (eroded_inv < 255))

    # Detect isolated pepper (black) pixels
    eroded = cv2.erode(gray, kernel, iterations=1)
    isolated_pepper = np.sum((gray == 0) & (eroded > 0))

    return (isolated_salt + isolated_pepper) / total_pixels


def deblur_motion(image_bgr, kernel_size=11):
    """Counter horizontal motion blur with directional sharpening."""
    # Create horizontal sharpening kernel
    kernel = np.zeros((3, kernel_size), dtype=np.float32)
    kernel[1, :] = -1.0 / kernel_size
    kernel[1, kernel_size // 2] = 2.0
    kernel = kernel / np.abs(kernel).sum() * 2

    result = np.zeros_like(image_bgr)
    for i in range(3):
        result[:, :, i] = cv2.filter2D(image_bgr[:, :, i], -1, kernel)
    return np.clip(result, 0, 255).astype(np.uint8)


def detect_blur_level(image_bgr):
    """Detect blur level using Laplacian variance."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


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

    # NOTE: Heavy preprocessing here can degrade clean images.
    # The query-time augmentations in recognition_api.py handle noisy inputs
    # by generating multiple preprocessed versions and comparing all.
    # Only apply very conservative preprocessing here.

    # Apply standard preprocessing
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


# =============================================================================
# PERIOCULAR EMBEDDING ENDPOINTS
# =============================================================================

# Lazy-load periocular extractor to avoid startup delay
_periocular_extractor = None

def get_periocular_extractor():
    """Lazy-load the periocular extractor."""
    global _periocular_extractor
    if _periocular_extractor is None:
        try:
            from app.utils.periocular_extractor import PeriocularExtractor
            _periocular_extractor = PeriocularExtractor()
            print("Periocular extractor initialized successfully")
        except Exception as e:
            print(f"Failed to initialize periocular extractor: {e}")
            _periocular_extractor = False  # Mark as failed
    return _periocular_extractor if _periocular_extractor else None


@app.post("/encode_periocular")
def encode_periocular():
    """
    Extract periocular region and generate embedding.

    Accepts: multipart file 'image' or JSON with base64 'image'

    Returns:
        {
            "embedding": [512 floats],  # Periocular embedding
            "glasses_detected": bool,
            "glasses_confidence": float,
            "glasses_type": str,
            "method": "periocular"
        }
    """
    # Get image data (same as /encode)
    if "image" in request.files:
        raw = request.files["image"].read()
        source = "multipart"
    else:
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(error="No image provided."), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(error="Invalid base64 image."), 400
        source = "json"

    # Decode image
    nparr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    # Get periocular extractor
    extractor = get_periocular_extractor()
    if extractor is None:
        return jsonify(error="Periocular extractor not available. Is MediaPipe installed?"), 500

    # Process image to get periocular region and glasses detection
    result = extractor.process_image(img_bgr)

    if not result['success']:
        return jsonify(
            error=result.get('error', 'Failed to extract periocular region'),
            fallback_to_face=True
        ), 200  # Return 200 so caller can fallback to full-face

    # Get the combined periocular region
    periocular_image = result['periocular']['combined']

    if periocular_image is None:
        return jsonify(
            error="No periocular region extracted",
            fallback_to_face=True
        ), 200

    # Convert periocular region to PIL for FaceNet
    # Resize to 160x160 (FaceNet input size)
    periocular_resized = cv2.resize(periocular_image, (160, 160))
    periocular_rgb = cv2.cvtColor(periocular_resized, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(periocular_rgb)

    # Generate embedding using FaceNet (transfer learning on periocular region)
    try:
        # Use fallback preprocessing (no MTCNN face detection - we already have the eye region)
        face_tensor = preprocess_fallback(pil_image)

        with torch.no_grad():
            emb = model(face_tensor).cpu().numpy()[0]

        # Get glasses info
        glasses_info = result.get('glasses', {})

        return jsonify(
            embedding=emb.tolist(),
            glasses_detected=glasses_info.get('glasses_detected', False),
            glasses_confidence=glasses_info.get('confidence', 0.0),
            glasses_type=glasses_info.get('type', 'none'),
            method="periocular"
        ), 200

    except Exception as e:
        return jsonify(error=f"Periocular embedding failed: {e}"), 500


@app.post("/encode_full")
def encode_full():
    """
    Generate both full-face and periocular embeddings in one call.

    Returns:
        {
            "face_embedding": [512 floats],
            "periocular_embedding": [512 floats] or null,
            "glasses_detected": bool,
            "glasses_confidence": float,
            "glasses_type": str
        }
    """
    # Get image data
    if "image" in request.files:
        raw = request.files["image"].read()
    else:
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(error="No image provided."), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(error="Invalid base64 image."), 400

    # Decode image
    nparr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify(error="Could not decode image."), 400

    result = {
        'face_embedding': None,
        'periocular_embedding': None,
        'glasses_detected': False,
        'glasses_confidence': 0.0,
        'glasses_type': 'none'
    }

    # 1. Generate full-face embedding
    try:
        pil_image = preprocess_image(raw)
        if pil_image is not None:
            face_tensor = extract_face_mtcnn(pil_image)
            if face_tensor is not None:
                face_tensor = face_tensor.unsqueeze(0).to(device)
            else:
                face_tensor = preprocess_fallback(pil_image)

            with torch.no_grad():
                face_emb = model(face_tensor).cpu().numpy()[0]
            result['face_embedding'] = face_emb.tolist()
    except Exception as e:
        print(f"Face embedding failed: {e}")

    # 2. Generate periocular embedding
    extractor = get_periocular_extractor()
    if extractor is not None:
        try:
            peri_result = extractor.process_image(img_bgr)

            if peri_result['success'] and peri_result['periocular']['combined'] is not None:
                periocular_image = peri_result['periocular']['combined']
                periocular_resized = cv2.resize(periocular_image, (160, 160))
                periocular_rgb = cv2.cvtColor(periocular_resized, cv2.COLOR_BGR2RGB)
                pil_periocular = Image.fromarray(periocular_rgb)

                peri_tensor = preprocess_fallback(pil_periocular)
                with torch.no_grad():
                    peri_emb = model(peri_tensor).cpu().numpy()[0]
                result['periocular_embedding'] = peri_emb.tolist()

            # Get glasses info
            if peri_result.get('glasses'):
                result['glasses_detected'] = peri_result['glasses'].get('glasses_detected', False)
                result['glasses_confidence'] = peri_result['glasses'].get('confidence', 0.0)
                result['glasses_type'] = peri_result['glasses'].get('type', 'none')

        except Exception as e:
            print(f"Periocular embedding failed: {e}")

    if result['face_embedding'] is None and result['periocular_embedding'] is None:
        return jsonify(error="Failed to generate any embeddings."), 500

    return jsonify(result), 200


@app.post("/detect_glasses")
def detect_glasses():
    """
    Detect if glasses are present in an image.

    Returns:
        {
            "glasses_detected": bool,
            "confidence": float,
            "type": "clear" | "tinted" | "sunglasses" | "none"
        }
    """
    # Get image data
    if "image" in request.files:
        raw = request.files["image"].read()
    else:
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(error="No image provided."), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(error="Invalid base64 image."), 400

    # Decode image
    nparr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify(error="Could not decode image."), 400

    extractor = get_periocular_extractor()
    if extractor is None:
        return jsonify(error="Periocular extractor not available."), 500

    glasses_result = extractor.detect_glasses(img_bgr)
    return jsonify(glasses_result), 200


# =============================================================================
# MULTI-FACE DETECTION WITH PERIOCULAR SUPPORT
# =============================================================================

@app.post("/detect_all_faces")
def detect_all_faces():
    """
    Detect ALL faces in an image using MTCNN and generate embeddings for each.
    Also extracts periocular embeddings for occlusion-robust matching.

    Accepts: multipart file 'image' or JSON with base64 'image'

    Returns:
        {
            "success": true,
            "total_faces": 4,
            "faces": [
                {
                    "face_index": 0,
                    "bbox": {"x": 100, "y": 50, "width": 80, "height": 80},
                    "confidence": 0.9987,
                    "face_embedding": [512 floats],
                    "periocular_embedding": [512 floats] or null,
                    "glasses_detected": false
                },
                ...
            ]
        }
    """
    # Get image data
    if "image" in request.files:
        raw = request.files["image"].read()
        source = "multipart"
    else:
        data = request.get_json(silent=True) or {}
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify(success=False, error="No image provided."), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify(success=False, error="Invalid base64 image."), 400
        source = "json"

    # Decode image
    nparr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify(success=False, error=f"Could not decode image from {source}."), 400

    # Preprocess image
    img_bgr_processed = normalize_exposure(img_bgr)
    img_bgr_processed = apply_clahe(img_bgr_processed)
    img_rgb = cv2.cvtColor(img_bgr_processed, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(img_rgb)

    # Detect all faces using MTCNN multi-face detector
    try:
        # Returns: (boxes, probs) when landmarks=False
        boxes, probs = mtcnn_multi.detect(pil_image, landmarks=False)

        if boxes is None or len(boxes) == 0:
            return jsonify(
                success=True,
                total_faces=0,
                faces=[],
                message="No faces detected in image"
            ), 200

        print(f"[multi-face] MTCNN detected {len(boxes)} faces")

    except Exception as e:
        return jsonify(success=False, error=f"Face detection failed: {e}"), 500

    # Get periocular extractor (may be None if not available)
    extractor = get_periocular_extractor()

    # Process each detected face
    face_results = []
    h, w = img_bgr.shape[:2]

    for i, (box, prob) in enumerate(zip(boxes, probs)):
        if prob is None or prob < 0.5:
            continue

        # Extract bounding box (MTCNN returns [x1, y1, x2, y2])
        x1, y1, x2, y2 = [int(coord) for coord in box]

        # Ensure bounds are within image
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        bbox_width = x2 - x1
        bbox_height = y2 - y1

        face_data = {
            "face_index": i,
            "bbox": {
                "x": x1,
                "y": y1,
                "width": bbox_width,
                "height": bbox_height
            },
            "confidence": float(prob),
            "face_embedding": None,
            "periocular_embedding": None,
            "glasses_detected": False,
            "glasses_confidence": 0.0
        }

        # Extract face crop with padding for embedding
        padding = int(max(bbox_width, bbox_height) * 0.2)
        crop_x1 = max(0, x1 - padding)
        crop_y1 = max(0, y1 - padding)
        crop_x2 = min(w, x2 + padding)
        crop_y2 = min(h, y2 + padding)

        face_crop_bgr = img_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

        if face_crop_bgr.size == 0:
            continue

        # Generate face embedding
        try:
            face_crop_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
            face_pil = Image.fromarray(face_crop_rgb)

            # Try MTCNN on the crop first (for better alignment)
            face_tensor = mtcnn(face_pil)

            if face_tensor is not None:
                face_tensor = face_tensor.unsqueeze(0).to(device)
            else:
                # Fallback: resize and normalize directly
                face_tensor = preprocess_fallback(face_pil)

            with torch.no_grad():
                face_emb = model(face_tensor).cpu().numpy()[0]
            face_data["face_embedding"] = face_emb.tolist()

        except Exception as e:
            print(f"[multi-face] Face {i} embedding failed: {e}")

        # Generate periocular embedding
        if extractor is not None:
            try:
                peri_result = extractor.process_image(face_crop_bgr)

                if peri_result['success'] and peri_result['periocular']['combined'] is not None:
                    periocular_image = peri_result['periocular']['combined']
                    periocular_resized = cv2.resize(periocular_image, (160, 160))
                    periocular_rgb = cv2.cvtColor(periocular_resized, cv2.COLOR_BGR2RGB)
                    pil_periocular = Image.fromarray(periocular_rgb)

                    peri_tensor = preprocess_fallback(pil_periocular)
                    with torch.no_grad():
                        peri_emb = model(peri_tensor).cpu().numpy()[0]
                    face_data["periocular_embedding"] = peri_emb.tolist()

                # Get glasses info
                if peri_result.get('glasses'):
                    face_data["glasses_detected"] = peri_result['glasses'].get('glasses_detected', False)
                    face_data["glasses_confidence"] = peri_result['glasses'].get('confidence', 0.0)

            except Exception as e:
                print(f"[multi-face] Face {i} periocular extraction failed: {e}")

        # Only add face if we got at least the face embedding
        if face_data["face_embedding"] is not None:
            face_results.append(face_data)
            print(f"[multi-face] Face {i}: bbox=({x1},{y1},{bbox_width}x{bbox_height}), conf={prob:.3f}, periocular={'yes' if face_data['periocular_embedding'] else 'no'}")

    return jsonify(
        success=True,
        total_faces=len(face_results),
        faces=face_results
    ), 200


if __name__ == "__main__":
    print("Starting embedding service with MTCNN face detection and periocular support...")
    app.run(host="127.0.0.1", port=5001)