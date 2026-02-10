# backend/app/utils/image_preprocessing.py
"""
Robust image preprocessing for facial recognition.
Handles distortions like rotation, grayscale, exposure changes.
"""

import cv2
import numpy as np
from PIL import Image
import io


def ensure_rgb(image):
    """
    Ensure image is in RGB format.
    Handles grayscale and RGBA images.

    Args:
        image: numpy array (BGR or grayscale) or PIL Image

    Returns:
        numpy array in BGR format (for OpenCV compatibility)
    """
    if isinstance(image, Image.Image):
        # Convert PIL to numpy
        if image.mode == 'L':
            # Grayscale - convert to RGB then BGR
            image = image.convert('RGB')
        elif image.mode == 'RGBA':
            image = image.convert('RGB')
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        image = np.array(image)
        # PIL is RGB, OpenCV expects BGR
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        return image

    # numpy array
    if len(image.shape) == 2:
        # Grayscale - convert to BGR
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        # RGBA - convert to BGR
        return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    elif image.shape[2] == 3:
        # Already 3 channels (assume BGR)
        return image

    return image


def apply_clahe(image, clip_limit=2.0, tile_grid_size=(8, 8)):
    """
    Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).
    Improves contrast while preventing over-amplification.

    Args:
        image: BGR image
        clip_limit: Threshold for contrast limiting
        tile_grid_size: Size of grid for histogram equalization

    Returns:
        Enhanced BGR image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l = clahe.apply(l)

    # Merge channels back
    lab = cv2.merge([l, a, b])
    result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return result


def normalize_exposure(image, target_brightness=127):
    """
    Normalize image exposure/brightness.

    Args:
        image: BGR image
        target_brightness: Target mean brightness (0-255)

    Returns:
        Exposure-normalized BGR image
    """
    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # Calculate current mean brightness
    current_brightness = np.mean(v)

    if current_brightness < 10:
        # Very dark image - boost significantly
        alpha = 2.0
        beta = 50
    elif current_brightness > 240:
        # Very bright image - reduce
        alpha = 0.7
        beta = -30
    else:
        # Normal adjustment
        alpha = target_brightness / max(current_brightness, 1)
        alpha = np.clip(alpha, 0.5, 2.0)  # Limit adjustment range
        beta = 0

    # Apply adjustment to V channel
    v = cv2.convertScaleAbs(v, alpha=alpha, beta=beta)

    # Merge and convert back
    hsv = cv2.merge([h, s, v])
    result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return result


def reduce_noise(image, strength=10):
    """
    Apply noise reduction while preserving edges.

    Args:
        image: BGR image
        strength: Denoising strength (higher = more smoothing)

    Returns:
        Denoised BGR image
    """
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)


def aggressive_denoise(image):
    """
    Apply aggressive noise reduction for heavily noisy images.
    Uses multiple passes and bilateral filtering.

    Args:
        image: BGR image

    Returns:
        Heavily denoised BGR image
    """
    # First pass: fast NL means with high strength
    denoised = cv2.fastNlMeansDenoisingColored(image, None, 15, 15, 7, 21)

    # Second pass: bilateral filter preserves edges better
    denoised = cv2.bilateralFilter(denoised, 9, 75, 75)

    return denoised


def deblur_image(image):
    """
    Apply sharpening to counteract blur.
    Uses unsharp masking technique.

    Args:
        image: BGR image

    Returns:
        Sharpened BGR image
    """
    # Create Gaussian blur
    blurred = cv2.GaussianBlur(image, (0, 0), 3)

    # Unsharp mask: original + (original - blurred) * amount
    sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

    return sharpened


def strong_deblur(image):
    """
    Apply stronger sharpening for heavily blurred images.

    Args:
        image: BGR image

    Returns:
        Strongly sharpened BGR image
    """
    # Sharpening kernel
    kernel = np.array([
        [-1, -1, -1],
        [-1,  9, -1],
        [-1, -1, -1]
    ])

    sharpened = cv2.filter2D(image, -1, kernel)
    return sharpened


def auto_rotate_face(image, face_cascade=None):
    """
    Attempt to detect and correct face rotation.
    Uses eye detection to estimate rotation angle.

    Args:
        image: BGR image
        face_cascade: Optional pre-loaded cascade classifier

    Returns:
        Rotation-corrected BGR image, rotation_angle
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Load eye cascade
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_eye.xml'
    )

    # Try to detect eyes
    eyes = eye_cascade.detectMultiScale(gray, 1.1, 5, minSize=(20, 20))

    if len(eyes) >= 2:
        # Sort by x coordinate to get left and right eyes
        eyes = sorted(eyes, key=lambda e: e[0])

        # Get eye centers
        left_eye = eyes[0]
        right_eye = eyes[1]

        left_center = (left_eye[0] + left_eye[2] // 2, left_eye[1] + left_eye[3] // 2)
        right_center = (right_eye[0] + right_eye[2] // 2, right_eye[1] + right_eye[3] // 2)

        # Calculate rotation angle
        dy = right_center[1] - left_center[1]
        dx = right_center[0] - left_center[0]
        angle = np.degrees(np.arctan2(dy, dx))

        # Only rotate if angle is significant but not too extreme
        if abs(angle) > 2 and abs(angle) < 45:
            # Get image center
            h, w = image.shape[:2]
            center = (w // 2, h // 2)

            # Rotate image
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                      borderMode=cv2.BORDER_REPLICATE)
            return rotated, angle

    return image, 0


def preprocess_for_recognition(image, apply_rotation=True, apply_clahe_flag=True,
                                apply_exposure=True, apply_denoise=False):
    """
    Full preprocessing pipeline for facial recognition.

    Args:
        image: Input image (BGR numpy array, PIL Image, or bytes)
        apply_rotation: Whether to attempt rotation correction
        apply_clahe_flag: Whether to apply CLAHE
        apply_exposure: Whether to normalize exposure
        apply_denoise: Whether to apply noise reduction

    Returns:
        Preprocessed BGR image ready for face detection/recognition
    """
    # Handle different input types
    if isinstance(image, bytes):
        # Convert bytes to PIL Image then to numpy
        pil_image = Image.open(io.BytesIO(image))
        image = np.array(pil_image.convert('RGB'))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    elif isinstance(image, Image.Image):
        image = ensure_rgb(image)

    # Ensure RGB/BGR format
    image = ensure_rgb(image)

    # Apply preprocessing steps
    if apply_rotation:
        image, angle = auto_rotate_face(image)

    if apply_exposure:
        image = normalize_exposure(image)

    if apply_clahe_flag:
        image = apply_clahe(image)

    if apply_denoise:
        image = reduce_noise(image)

    return image


# =============================================================================
# SELECTIVE PREPROCESSING - Detect quality before applying fixes
# =============================================================================

def estimate_noise_level(image):
    """
    Estimate the noise level in an image using Laplacian variance difference.

    Higher values indicate more noise.

    Args:
        image: BGR image

    Returns:
        float: Estimated noise level (0-100+ scale, higher = more noisy)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Method: Compare original Laplacian variance with blurred version
    # Noise adds high-frequency components that blur removes
    laplacian_original = cv2.Laplacian(gray, cv2.CV_64F)

    # Blur to remove noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    laplacian_blurred = cv2.Laplacian(blurred, cv2.CV_64F)

    # Noise estimate = difference in variance
    var_original = laplacian_original.var()
    var_blurred = laplacian_blurred.var()

    # Normalize to 0-100 scale (approximate)
    noise_estimate = (var_original - var_blurred) / max(var_blurred, 1) * 10

    return max(0, noise_estimate)


def estimate_blur_level(image):
    """
    Estimate blur level using Laplacian variance.

    Lower values indicate more blur (less sharp edges).

    Args:
        image: BGR image

    Returns:
        float: Blur score (higher = sharper, lower = more blurry)
               Typical values: <50 = very blurry, 50-100 = moderate, >100 = sharp
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Laplacian variance - standard blur detection
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    return laplacian_var


def selective_preprocess(image, noise_threshold=15, blur_threshold=50):
    """
    Intelligently preprocess image based on detected quality.

    Only applies denoising if noise is detected.
    Only applies sharpening if blur is detected.
    Does NOT modify clean images.

    Args:
        image: BGR image
        noise_threshold: Apply denoising if noise level exceeds this (default 15)
        blur_threshold: Apply sharpening if blur score below this (default 50)

    Returns:
        tuple: (processed_image, applied_operations dict)
    """
    result = image.copy()
    operations = {
        "noise_detected": False,
        "noise_level": 0,
        "blur_detected": False,
        "blur_level": 0,
        "denoising_applied": False,
        "sharpening_applied": False
    }

    # Estimate noise level
    noise_level = estimate_noise_level(image)
    operations["noise_level"] = round(noise_level, 2)

    # Estimate blur level
    blur_level = estimate_blur_level(image)
    operations["blur_level"] = round(blur_level, 2)

    # Apply denoising if noise detected
    if noise_level > noise_threshold:
        operations["noise_detected"] = True
        # Scale denoising strength based on noise level
        if noise_level > 40:
            result = aggressive_denoise(result)
        else:
            # Moderate denoising
            strength = min(int(noise_level / 2), 15)
            result = cv2.fastNlMeansDenoisingColored(result, None, strength, strength, 7, 21)
        operations["denoising_applied"] = True

    # Apply sharpening if blur detected (but NOT if we just denoised heavily)
    # Sharpening after denoising can re-introduce noise
    if blur_level < blur_threshold and not (noise_level > 30):
        operations["blur_detected"] = True
        if blur_level < 25:
            # Heavy blur - strong sharpening
            result = strong_deblur(result)
        else:
            # Moderate blur - light sharpening
            result = deblur_image(result)
        operations["sharpening_applied"] = True

    return result, operations


def add_gaussian_noise(image, sigma):
    """
    Add Gaussian noise to image for augmentation.

    Args:
        image: BGR numpy array
        sigma: Standard deviation of noise (higher = more noise)

    Returns:
        Noisy BGR image
    """
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


def generate_augmentations(image, include_rotations=True, include_brightness=True,
                           include_grayscale=True, include_noise=True, include_blur=True):
    """
    Generate augmented versions of an image for robust encoding.

    Args:
        image: BGR numpy array
        include_rotations: Include rotated versions (±15°, ±30°)
        include_brightness: Include brightness variations
        include_grayscale: Include grayscale version
        include_noise: Include noisy versions (CRITICAL for noise robustness)
        include_blur: Include blurred versions

    Returns:
        List of (augmented_image, augmentation_name) tuples
    """
    augmentations = [
        (image.copy(), 'original')
    ]

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    if include_rotations:
        for angle in [-30, -15, 15, 30]:
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            augmentations.append((rotated, f'rotate_{angle}'))

    if include_brightness:
        # Darker version
        darker = cv2.convertScaleAbs(image, alpha=0.7, beta=-20)
        augmentations.append((darker, 'darker'))

        # Brighter version
        brighter = cv2.convertScaleAbs(image, alpha=1.3, beta=30)
        augmentations.append((brighter, 'brighter'))

        # High contrast
        high_contrast = cv2.convertScaleAbs(image, alpha=1.5, beta=0)
        augmentations.append((high_contrast, 'high_contrast'))

        # Low contrast
        low_contrast = cv2.convertScaleAbs(image, alpha=0.6, beta=50)
        augmentations.append((low_contrast, 'low_contrast'))

    if include_grayscale:
        # Convert to grayscale then back to BGR (simulates B&W image)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        augmentations.append((gray_bgr, 'grayscale'))

    # === NOISE AUGMENTATION (Critical for noise robustness) ===
    if include_noise:
        # Light noise (sigma=10) - model breaks at sigma=10, so train on this
        noisy_light = add_gaussian_noise(image, 10)
        augmentations.append((noisy_light, 'noise_10'))

        # Medium noise (sigma=20)
        noisy_medium = add_gaussian_noise(image, 20)
        augmentations.append((noisy_medium, 'noise_20'))

        # Heavy noise (sigma=30) - where model currently fails badly
        noisy_heavy = add_gaussian_noise(image, 30)
        augmentations.append((noisy_heavy, 'noise_30'))

        # Combined: rotation + noise (common real-world scenario)
        M = cv2.getRotationMatrix2D(center, 15, 1.0)
        rotated_noisy = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        rotated_noisy = add_gaussian_noise(rotated_noisy, 15)
        augmentations.append((rotated_noisy, 'rotate_noise'))

    # === BLUR AUGMENTATION ===
    if include_blur:
        # Light blur (kernel 5x5)
        blur_light = cv2.GaussianBlur(image, (5, 5), 0)
        augmentations.append((blur_light, 'blur_5'))

        # Medium blur (kernel 9x9)
        blur_medium = cv2.GaussianBlur(image, (9, 9), 0)
        augmentations.append((blur_medium, 'blur_9'))

    return augmentations
