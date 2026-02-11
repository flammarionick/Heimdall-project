# embedding_service.py  (standalone microservice)
# Enhanced with ArcFace model for superior noise robustness
from flask import Flask, request, jsonify
import base64
import io
import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN
from PIL import Image
import os

app = Flask(__name__)

# Load models once at startup
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Embedding service using device: {device}")

# ============================================================================
# ArcFace Model Setup (primary model for noise-robust embeddings)
# ============================================================================
ARCFACE_MODEL_PATH = os.path.expanduser("~/.insightface/models/buffalo_l/w600k_r50.onnx")
USE_ARCFACE = os.path.exists(ARCFACE_MODEL_PATH)
arcface_session = None

if USE_ARCFACE:
    try:
        import onnxruntime as ort
        arcface_session = ort.InferenceSession(ARCFACE_MODEL_PATH, providers=['CPUExecutionProvider'])
        arcface_input_name = arcface_session.get_inputs()[0].name
        arcface_output_name = arcface_session.get_outputs()[0].name
        print(f"ArcFace model loaded: {ARCFACE_MODEL_PATH}")
        print("Using ArcFace for embeddings (superior noise robustness)")
    except Exception as e:
        print(f"Failed to load ArcFace: {e}")
        USE_ARCFACE = False

# Fallback to FaceNet if ArcFace not available
if not USE_ARCFACE:
    from facenet_pytorch import InceptionResnetV1
    RETRAINED_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models', 'heimdall_facenet_retrained.pt')
    if os.path.exists(RETRAINED_MODEL_PATH):
        print(f"Loading RETRAINED FaceNet model: {RETRAINED_MODEL_PATH}")
        model = torch.jit.load(RETRAINED_MODEL_PATH, map_location=device).eval()
    else:
        print("Using default VGGFace2 pretrained FaceNet model")
        model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
else:
    model = None  # Not used when ArcFace is active


def preprocess_for_arcface(img_bgr):
    """Preprocess image for ArcFace (112x112, normalized to [-1,1])."""
    img_resized = cv2.resize(img_bgr, (112, 112))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_transposed = img_rgb.transpose(2, 0, 1)
    img_normalized = (img_transposed.astype(np.float32) - 127.5) / 127.5
    return np.expand_dims(img_normalized, axis=0)


# =============================================================================
# FACE ALIGNMENT FOR ARCFACE
# =============================================================================
# ArcFace expects faces to be aligned to a specific template with eyes horizontal.
# This is critical for rotation invariance.

# Standard ArcFace reference points for 112x112 input
ARCFACE_REF_POINTS = np.array([
    [38.2946, 51.6963],   # left eye
    [73.5318, 51.5014],   # right eye
    [56.0252, 71.7366],   # nose tip
    [41.5493, 92.3655],   # left mouth corner
    [70.7299, 92.2041]    # right mouth corner
], dtype=np.float32)


def estimate_similarity_transform(src_points, dst_points):
    """
    Estimate similarity transform (rotation, scale, translation) from src to dst points.
    Uses least squares to find the best transformation.

    Args:
        src_points: Source landmarks (Nx2)
        dst_points: Destination landmarks (Nx2)

    Returns:
        3x2 transformation matrix for cv2.warpAffine
    """
    num_points = src_points.shape[0]

    # Build the system of equations
    # For similarity transform: [x'] = [a -b] [x] + [tx]
    #                          [y']   [b  a] [y]   [ty]

    A = np.zeros((num_points * 2, 4))
    b = np.zeros(num_points * 2)

    for i in range(num_points):
        A[i * 2, 0] = src_points[i, 0]      # a * x
        A[i * 2, 1] = -src_points[i, 1]     # -b * y
        A[i * 2, 2] = 1                      # tx
        A[i * 2, 3] = 0

        A[i * 2 + 1, 0] = src_points[i, 1]  # b * y (actually a * y)
        A[i * 2 + 1, 1] = src_points[i, 0]  # a * x (actually b * x)
        A[i * 2 + 1, 2] = 0
        A[i * 2 + 1, 3] = 1                  # ty

        b[i * 2] = dst_points[i, 0]
        b[i * 2 + 1] = dst_points[i, 1]

    # Solve using least squares
    params, _, _, _ = np.linalg.lstsq(A, b, rcond=None)

    a, b_param, tx, ty = params

    # Build transformation matrix
    M = np.array([
        [a, -b_param, tx],
        [b_param, a, ty]
    ], dtype=np.float32)

    return M


def align_face_for_arcface(img_bgr, landmarks):
    """
    Align face using 5-point landmarks for ArcFace.

    Args:
        img_bgr: BGR image (any size)
        landmarks: 5 facial landmarks [left_eye, right_eye, nose, left_mouth, right_mouth]
                   Each is (x, y) coordinates

    Returns:
        Aligned face image (112x112 BGR), or None if alignment fails
    """
    if landmarks is None or len(landmarks) < 5:
        return None

    try:
        src_points = np.array(landmarks[:5], dtype=np.float32)

        # Estimate similarity transform
        M = estimate_similarity_transform(src_points, ARCFACE_REF_POINTS)

        # Apply transformation
        aligned = cv2.warpAffine(img_bgr, M, (112, 112), borderMode=cv2.BORDER_REPLICATE)

        return aligned

    except Exception as e:
        print(f"[align] Face alignment failed: {e}")
        return None


def align_face_simple(img_bgr, left_eye, right_eye):
    """
    Simple face alignment using only eye positions.
    Rotates image to make eyes horizontal, then crops.

    Args:
        img_bgr: BGR image
        left_eye: (x, y) of left eye
        right_eye: (x, y) of right eye

    Returns:
        Aligned face image (112x112 BGR)
    """
    h, w = img_bgr.shape[:2]

    # Calculate angle between eyes
    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    angle = np.degrees(np.arctan2(dy, dx))

    # Eye center
    eye_center = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)

    # Rotation matrix
    M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)

    # Rotate image
    rotated = cv2.warpAffine(img_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    # Calculate crop region based on eye distance
    eye_dist = np.sqrt(dx**2 + dy**2)

    # Face crop: eyes should be at ~35% from top, face width ~2.2x eye distance
    face_width = int(eye_dist * 2.5)
    face_height = int(face_width * 1.2)  # Slightly taller than wide

    # Center below eyes (face center is lower than eye center)
    center_x = int(eye_center[0])
    center_y = int(eye_center[1] + eye_dist * 0.4)

    # Crop coordinates
    x1 = max(0, center_x - face_width // 2)
    y1 = max(0, center_y - int(face_height * 0.45))  # Eyes at ~35% from top
    x2 = min(w, x1 + face_width)
    y2 = min(h, y1 + face_height)

    face_crop = rotated[y1:y2, x1:x2]

    if face_crop.size == 0:
        return None

    # Resize to 112x112 for ArcFace
    return cv2.resize(face_crop, (112, 112))


# MTCNN detector that returns landmarks (for alignment)
mtcnn_with_landmarks = MTCNN(
    image_size=160,
    margin=20,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=False,  # Don't post-process, we need raw output
    select_largest=True,
    keep_all=False,
    device=device
)


def estimate_noise_level(img_bgr):
    """Estimate noise level using Laplacian variance method."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Calculate Laplacian variance (lower = more blur/noise)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # High-pass filter to isolate noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    high_pass = gray.astype(np.float64) - blur.astype(np.float64)
    noise_std = np.std(high_pass)

    return noise_std


def estimate_blur_level(img_bgr):
    """
    Estimate blur level using Laplacian variance.
    Lower values indicate more blur.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


def detect_motion_blur(img_bgr):
    """
    Detect if image has motion blur by analyzing directional gradients.
    Returns (is_motion_blur, dominant_direction) where direction is 'horizontal' or 'vertical'.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Compute gradients in x and y directions
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    # Calculate gradient magnitudes
    mag_x = np.abs(grad_x).mean()
    mag_y = np.abs(grad_y).mean()

    # Motion blur creates stronger gradients perpendicular to motion direction
    # Horizontal motion blur -> weak horizontal gradients, strong vertical
    ratio = mag_x / (mag_y + 1e-6)

    if ratio < 0.5:
        return True, 'horizontal'
    elif ratio > 2.0:
        return True, 'vertical'
    else:
        return False, None


def sharpen_image(img_bgr, strength=1.5):
    """
    Sharpen blurry image using unsharp masking.
    """
    # Create Gaussian blur
    blurred = cv2.GaussianBlur(img_bgr, (0, 0), 3)

    # Unsharp mask: original + strength * (original - blurred)
    sharpened = cv2.addWeighted(img_bgr, 1 + strength, blurred, -strength, 0)

    return np.clip(sharpened, 0, 255).astype(np.uint8)


def deblur_wiener(img_bgr, kernel_size=15, noise_var=0.01):
    """
    Apply Wiener deconvolution for motion blur.
    This is a simplified version using frequency domain filtering.
    """
    # Convert to float
    img_float = img_bgr.astype(np.float64) / 255.0

    result = np.zeros_like(img_float)

    for c in range(3):
        channel = img_float[:, :, c]

        # Apply sharpening kernel as approximation
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) / 1.0

        # Apply kernel
        sharpened = cv2.filter2D(channel, -1, kernel)
        result[:, :, c] = sharpened

    result = np.clip(result * 255, 0, 255).astype(np.uint8)
    return result


def correct_motion_blur(img_bgr, direction='horizontal'):
    """
    Correct motion blur using directional sharpening.
    """
    if direction == 'horizontal':
        # Horizontal sharpening kernel
        kernel = np.array([[-1, -2, -1],
                          [ 2,  4,  2],
                          [-1, -2, -1]]) / 2.0
    else:
        # Vertical sharpening kernel
        kernel = np.array([[-1,  2, -1],
                          [-2,  4, -2],
                          [-1,  2, -1]]) / 2.0

    result = cv2.filter2D(img_bgr, -1, kernel)
    return np.clip(result, 0, 255).astype(np.uint8)


def enhance_blurry_image(img_bgr):
    """
    Enhance a blurry image using multiple techniques.
    """
    # Step 1: Bilateral filter to reduce noise while preserving edges
    denoised = cv2.bilateralFilter(img_bgr, 5, 50, 50)

    # Step 2: CLAHE for contrast enhancement
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Step 3: Unsharp masking
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

    return np.clip(sharpened, 0, 255).astype(np.uint8)


def extreme_denoise(img_bgr):
    """
    Aggressive denoising for extremely noisy images (sigma > 40).
    Uses multiple passes and edge-aware filtering.
    """
    # Pass 1: Non-local means with high strength
    denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 20, 20, 7, 21)

    # Pass 2: Bilateral to preserve edges
    denoised = cv2.bilateralFilter(denoised, 9, 100, 100)

    # Pass 3: Light bilateral for final smoothing
    denoised = cv2.bilateralFilter(denoised, 5, 50, 50)

    return denoised


def denoise_image(img_bgr, strength='auto'):
    """
    Apply aggressive denoising to clean up noisy images.

    Uses multiple denoising techniques:
    1. Non-local means denoising (best for Gaussian noise)
    2. Bilateral filter (preserves edges)
    3. Median filter (good for salt & pepper)
    """
    if strength == 'auto':
        noise_level = estimate_noise_level(img_bgr)
        if noise_level < 10:
            strength = 'light'
        elif noise_level < 25:
            strength = 'medium'
        else:
            strength = 'heavy'

    # Non-local means denoising (best for Gaussian noise)
    # Parameters: src, dst, h, hColor, templateWindowSize, searchWindowSize
    if strength == 'light':
        # Light denoising for clean images
        denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 5, 5, 7, 21)
    elif strength == 'medium':
        # Medium denoising
        denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 10, 10, 7, 21)
    else:
        # Heavy denoising for very noisy images
        # First pass: strong non-local means
        denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 15, 15, 7, 21)
        # Second pass: bilateral filter to preserve edges
        denoised = cv2.bilateralFilter(denoised, 9, 75, 75)

    return denoised


def denoise_bilateral(img_bgr):
    """
    Apply bilateral filter denoising - optimal for face recognition.
    Bilateral filter preserves edges while smoothing noise, making it
    ideal for facial features.
    """
    return cv2.bilateralFilter(img_bgr, 9, 75, 75)


def adaptive_denoise_for_query(img_bgr):
    """
    Adaptive denoising for query images.
    Detects noise level and applies appropriate denoising.
    Uses bilateral filter which works best for face recognition.

    Returns:
        (denoised_image, noise_level, denoising_applied)
    """
    noise_level = estimate_noise_level(img_bgr)

    # Thresholds determined empirically - bilateral filter is best for faces
    # as it preserves edges (facial features) while smoothing noise
    if noise_level < 8:
        # Clean image - no denoising needed
        return img_bgr, noise_level, False
    elif noise_level < 15:
        # Light to medium noise - standard bilateral
        denoised = cv2.bilateralFilter(img_bgr, 9, 75, 75)
        return denoised, noise_level, True
    elif noise_level < 30:
        # Heavy noise - strong bilateral
        denoised = cv2.bilateralFilter(img_bgr, 9, 100, 100)
        return denoised, noise_level, True
    else:
        # Extreme noise - use aggressive multi-pass denoising
        denoised = extreme_denoise(img_bgr)
        return denoised, noise_level, True


def adaptive_enhance_for_query(img_bgr):
    """
    Comprehensive adaptive image enhancement for query images.
    Detects blur, motion blur, and noise, then applies appropriate corrections.

    IMPORTANT: For blur, we only sharpen - no denoising (bilateral causes over-smoothing).
    For noise, we only denoise - no sharpening (amplifies noise).

    Returns:
        (enhanced_image, enhancements_applied: dict)
    """
    enhancements = {
        'blur_corrected': False,
        'motion_blur_corrected': False,
        'noise_reduced': False,
        'blur_level': 0,
        'noise_level': 0
    }

    result = img_bgr.copy()

    # Check blur level (low = more blurry)
    blur_level = estimate_blur_level(img_bgr)
    enhancements['blur_level'] = blur_level

    # Check noise level
    noise_level = estimate_noise_level(img_bgr)
    enhancements['noise_level'] = noise_level

    # Check for motion blur
    is_motion_blur, motion_dir = detect_motion_blur(img_bgr)

    # Determine primary issue - blur and noise don't mix well for correction
    # If both are present, prioritize denoising (noise hurts more than blur)
    is_primarily_noisy = noise_level >= 15
    is_primarily_blurry = blur_level < 80 and noise_level < 15

    if is_primarily_noisy:
        # Handle noise - use denoising only, no sharpening
        if noise_level >= 30:
            # Extreme noise - aggressive denoising
            result = extreme_denoise(result)
        elif noise_level >= 15:
            # Heavy noise
            result = cv2.bilateralFilter(result, 9, 100, 100)
        else:
            # Medium noise
            result = cv2.bilateralFilter(result, 9, 75, 75)
        enhancements['noise_reduced'] = True

    elif is_primarily_blurry:
        # Handle blur - sharpening only, no denoising (would over-smooth)
        if is_motion_blur:
            # Motion blur - directional sharpening
            result = correct_motion_blur(result, motion_dir)
            result = sharpen_image(result, strength=0.8)
            enhancements['motion_blur_corrected'] = True
        elif blur_level < 30:
            # Very blurry - strong sharpening with edge enhancement
            # Use CLAHE + unsharp mask
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            result = sharpen_image(result, strength=2.0)
            enhancements['blur_corrected'] = True
        else:
            # Moderately blurry - light sharpening
            result = sharpen_image(result, strength=1.2)
            enhancements['blur_corrected'] = True
    else:
        # Light noise and not too blurry - light bilateral only
        if noise_level >= 8:
            result = cv2.bilateralFilter(result, 5, 50, 50)
            enhancements['noise_reduced'] = True

    return result, enhancements


def get_arcface_embedding(img_bgr, apply_denoising=True, pre_aligned=False):
    """Get embedding using ArcFace model with optional denoising.

    Args:
        img_bgr: BGR image (should be 112x112 if pre_aligned=True)
        apply_denoising: Whether to apply automatic denoising
        pre_aligned: If True, skip preprocessing (image is already aligned 112x112)
    """
    if apply_denoising and not pre_aligned:
        img_bgr = denoise_image(img_bgr, strength='auto')

    img_input = preprocess_for_arcface(img_bgr)
    embedding = arcface_session.run([arcface_output_name], {arcface_input_name: img_input})[0][0]
    # L2 normalize
    embedding = embedding / np.linalg.norm(embedding)
    return embedding


def get_arcface_embedding_aligned(img_bgr, apply_denoising=True):
    """
    Get ArcFace embedding with automatic face alignment.
    This is the recommended method for best rotation invariance.

    Args:
        img_bgr: BGR image of any size containing a face

    Returns:
        tuple: (embedding, aligned_face, method_used)
               embedding: 512-dim normalized embedding
               aligned_face: 112x112 aligned face image
               method_used: 'mtcnn_5point', 'mtcnn_2point', or 'direct'
    """
    # Apply denoising first if requested
    if apply_denoising:
        img_bgr = denoise_image(img_bgr, strength='auto')

    # Convert to RGB for MTCNN
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(img_rgb)

    # Try to detect face and get landmarks
    try:
        # Use detect() with landmarks=True to get 5-point landmarks
        boxes, probs, landmarks = mtcnn_with_landmarks.detect(pil_image, landmarks=True)

        if boxes is not None and len(boxes) > 0 and landmarks is not None:
            # Get landmarks for first (largest) face
            face_landmarks = landmarks[0]  # Shape: (5, 2)

            # Align face using 5-point landmarks
            aligned = align_face_for_arcface(img_bgr, face_landmarks)

            if aligned is not None:
                emb = get_arcface_embedding(aligned, apply_denoising=False, pre_aligned=True)
                return emb, aligned, 'mtcnn_5point'

            # Fallback: try simple 2-point alignment using eyes only
            left_eye = face_landmarks[0]
            right_eye = face_landmarks[1]
            aligned = align_face_simple(img_bgr, left_eye, right_eye)

            if aligned is not None:
                emb = get_arcface_embedding(aligned, apply_denoising=False, pre_aligned=True)
                return emb, aligned, 'mtcnn_2point'

    except Exception as e:
        print(f"[arcface_aligned] MTCNN detection failed: {e}")

    # Final fallback: direct encoding without alignment
    emb = get_arcface_embedding(img_bgr, apply_denoising=False)
    return emb, None, 'direct'


def get_arcface_embedding_multi(img_bgr):
    """
    Get multiple embeddings from an image using different preprocessing.
    Returns the one with highest quality score.
    """
    embeddings = []

    # Original with denoising
    emb1 = get_arcface_embedding(img_bgr, apply_denoising=True)
    embeddings.append(emb1)

    # Heavy denoising
    denoised_heavy = denoise_image(img_bgr, strength='heavy')
    img_input = preprocess_for_arcface(denoised_heavy)
    emb2 = arcface_session.run([arcface_output_name], {arcface_input_name: img_input})[0][0]
    emb2 = emb2 / np.linalg.norm(emb2)
    embeddings.append(emb2)

    # Average embedding (ensemble)
    avg_emb = np.mean(embeddings, axis=0)
    avg_emb = avg_emb / np.linalg.norm(avg_emb)

    return avg_emb

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
    Uses ArcFace model for superior noise robustness.
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

    # Decode image
    nparr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    # Use ArcFace if available (primary method for noise robustness)
    if USE_ARCFACE:
        try:
            # Check if alignment is requested
            use_alignment = request.args.get('align', 'false').lower() == 'true'
            # Check if adaptive denoising is requested (for noisy query images)
            use_denoise = request.args.get('denoise', 'false').lower()
            # Check if comprehensive enhancement is requested (handles blur, motion blur, noise)
            use_enhance = request.args.get('enhance', 'false').lower()

            # Enhancement info
            enhancements = {}
            noise_level = 0
            denoising_applied = False

            # Apply comprehensive enhancement if requested (includes blur correction + denoising)
            if use_enhance == 'true' or use_enhance == 'auto':
                img_bgr, enhancements = adaptive_enhance_for_query(img_bgr)
                noise_level = enhancements.get('noise_level', 0)
                denoising_applied = enhancements.get('noise_reduced', False)
            # Or just denoising if requested
            elif use_denoise == 'true' or use_denoise == 'auto':
                img_bgr, noise_level, denoising_applied = adaptive_denoise_for_query(img_bgr)

            if use_alignment:
                # Use aligned embedding (better for rotation but worse for noise)
                emb, aligned_face, method = get_arcface_embedding_aligned(img_bgr, apply_denoising=False)
                return jsonify(
                    embedding=emb.tolist(),
                    method=f"arcface_{method}",
                    aligned=aligned_face is not None,
                    noise_level=float(noise_level),
                    denoised=denoising_applied,
                    enhancements=enhancements
                ), 200
            else:
                # Use direct encoding
                emb = get_arcface_embedding(img_bgr, apply_denoising=False)
                return jsonify(
                    embedding=emb.tolist(),
                    method="arcface_direct",
                    noise_level=float(noise_level),
                    denoised=denoising_applied,
                    enhancements=enhancements
                ), 200

        except Exception as e:
            return jsonify(error=f"ArcFace embedding failed: {e}"), 500

    # Fallback to FaceNet
    pil_image = preprocess_image(raw)
    if pil_image is None:
        return jsonify(error=f"Could not decode image from {source} payload."), 400

    try:
        face_tensor = extract_face_mtcnn(pil_image)

        if face_tensor is not None:
            face_tensor = face_tensor.unsqueeze(0).to(device)
            with torch.no_grad():
                emb = model(face_tensor).cpu().numpy()[0]
            return jsonify(embedding=emb.tolist(), method="facenet_mtcnn"), 200
        else:
            face_tensor = preprocess_fallback(pil_image)
            with torch.no_grad():
                emb = model(face_tensor).cpu().numpy()[0]
            return jsonify(embedding=emb.tolist(), method="facenet_fallback"), 200

    except Exception as e:
        return jsonify(error=f"Embedding failed: {e}"), 500


@app.post("/encode_multiple")
def encode_multiple():
    """
    Encode multiple augmented versions of a face.
    Expects JSON with 'images' array of base64 encoded images.
    Returns array of embeddings.
    Uses ArcFace model for superior noise robustness.
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

            # Decode image
            nparr = np.frombuffer(raw, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_bgr is None:
                embeddings.append(None)
                continue

            # Use ArcFace if available
            if USE_ARCFACE:
                # Use aligned embedding for rotation robustness
                emb, _, _ = get_arcface_embedding_aligned(img_bgr, apply_denoising=True)
                embeddings.append(emb.tolist())
            else:
                # Fallback to FaceNet
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
    return jsonify(
        status="ok",
        device=str(device),
        model="arcface" if USE_ARCFACE else "facenet",
        arcface_available=USE_ARCFACE
    ), 200


@app.post("/encode_with_rotation_augmentation")
def encode_with_rotation_augmentation():
    """
    Encode a face with query-time rotation augmentation.
    Returns multiple embeddings for different rotations, useful for matching
    rotated faces against a non-rotated database.

    Returns:
        {
            "embeddings": [
                {"rotation": -30, "embedding": [...]},
                {"rotation": -15, "embedding": [...]},
                {"rotation": 0, "embedding": [...]},
                {"rotation": 15, "embedding": [...]},
                {"rotation": 30, "embedding": [...]}
            ],
            "method": "arcface_rotation_augmented"
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

    if not USE_ARCFACE:
        return jsonify(error="ArcFace not available."), 500

    # Rotation angles to try
    rotations = [-30, -15, 0, 15, 30]
    h, w = img_bgr.shape[:2]
    center = (w // 2, h // 2)

    results = []

    for angle in rotations:
        if angle == 0:
            rotated = img_bgr
        else:
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)  # Negative to counter-rotate
            rotated = cv2.warpAffine(img_bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        try:
            emb = get_arcface_embedding(rotated, apply_denoising=False)
            results.append({
                "rotation": angle,
                "embedding": emb.tolist()
            })
        except Exception as e:
            print(f"[rotation_aug] Failed at {angle}°: {e}")

    return jsonify(
        embeddings=results,
        method="arcface_rotation_augmented",
        rotations_tried=len(results)
    ), 200


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