# app/utils/embedding_client.py
"""
Embedding client for communicating with the FaceNet embedding service.
Supports both full-face and periocular (eye region) embeddings.
"""
import os
import cv2
import base64
import requests
from typing import Optional, Dict, Tuple, List

# Base URL for embedding service
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://127.0.0.1:5001")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", f"{EMBEDDING_SERVICE_URL}/encode")
PERIOCULAR_URL = f"{EMBEDDING_SERVICE_URL}/encode_periocular"
FULL_ENCODE_URL = f"{EMBEDDING_SERVICE_URL}/encode_full"
GLASSES_DETECT_URL = f"{EMBEDDING_SERVICE_URL}/detect_glasses"
DETECT_ALL_FACES_URL = f"{EMBEDDING_SERVICE_URL}/detect_all_faces"

# Timeout for requests (seconds)
REQUEST_TIMEOUT = 40


def _encode_image_to_base64(frame) -> Optional[str]:
    """Encode an OpenCV frame to base64 JPEG."""
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return base64.b64encode(buf).decode("ascii")


def extract_embedding_from_frame(frame) -> Optional[List[float]]:
    """
    Takes a BGR OpenCV frame and returns an embedding list from the embedding service.
    Returns None if encoding/HTTP fails or the service returns no embedding.
    """
    b64 = _encode_image_to_base64(frame)
    if not b64:
        return None

    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        resp = requests.post(EMBEDDING_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    data = resp.json()
    return data.get("embedding")


def extract_periocular_embedding(frame) -> Optional[Dict]:
    """
    Extract periocular (eye region) embedding from a frame.

    Args:
        frame: BGR OpenCV image

    Returns:
        Dict with keys:
            - embedding: List[float] (512-dim) or None
            - glasses_detected: bool
            - glasses_confidence: float
            - glasses_type: str
        Returns None if request fails completely.
    """
    b64 = _encode_image_to_base64(frame)
    if not b64:
        return None

    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        resp = requests.post(PERIOCULAR_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Check if it's a fallback response (periocular extraction failed)
        if data.get("fallback_to_face"):
            return {
                'embedding': None,
                'glasses_detected': False,
                'glasses_confidence': 0.0,
                'glasses_type': 'none',
                'fallback': True
            }

        return {
            'embedding': data.get("embedding"),
            'glasses_detected': data.get("glasses_detected", False),
            'glasses_confidence': data.get("glasses_confidence", 0.0),
            'glasses_type': data.get("glasses_type", "none"),
            'fallback': False
        }

    except requests.RequestException as e:
        print(f"[embedding_client] Periocular embedding request failed: {e}")
        return None


def extract_full_embeddings(frame) -> Optional[Dict]:
    """
    Extract both full-face and periocular embeddings in a single call.

    Args:
        frame: BGR OpenCV image

    Returns:
        Dict with keys:
            - face_embedding: List[float] (512-dim) or None
            - periocular_embedding: List[float] (512-dim) or None
            - glasses_detected: bool
            - glasses_confidence: float
            - glasses_type: str
        Returns None if request fails completely.
    """
    b64 = _encode_image_to_base64(frame)
    if not b64:
        return None

    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        resp = requests.post(FULL_ENCODE_URL, json=payload, timeout=REQUEST_TIMEOUT * 2)
        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        print(f"[embedding_client] Full embedding request failed: {e}")
        return None


def detect_glasses(frame) -> Optional[Dict]:
    """
    Detect if glasses are present in an image.

    Args:
        frame: BGR OpenCV image

    Returns:
        Dict with keys:
            - glasses_detected: bool
            - confidence: float (0-1)
            - type: 'clear', 'tinted', 'sunglasses', or 'none'
        Returns None if request fails.
    """
    b64 = _encode_image_to_base64(frame)
    if not b64:
        return None

    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        resp = requests.post(GLASSES_DETECT_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        print(f"[embedding_client] Glasses detection request failed: {e}")
        return None


def compute_fusion_score(face_distance: float,
                         periocular_distance: float,
                         glasses_detected: bool = False,
                         glasses_confidence: float = 0.0) -> Tuple[float, float]:
    """
    Compute fusion score combining face and periocular distances.

    Uses adaptive weighting:
    - When glasses are detected, trust periocular more
    - When no glasses, trust full-face more

    Args:
        face_distance: Cosine distance from full-face matching
        periocular_distance: Cosine distance from periocular matching
        glasses_detected: Whether glasses were detected in query
        glasses_confidence: Confidence of glasses detection (0-1)

    Returns:
        Tuple of (fused_distance, face_weight)
        fused_distance: Combined distance score (lower = better match)
        face_weight: Weight used for full-face (for debugging)
    """
    # Base weights
    if glasses_detected:
        # Glasses detected - rely more on periocular
        # Scale weight by glasses confidence
        face_weight = max(0.2, 0.5 - (glasses_confidence * 0.3))
    else:
        # No glasses - rely more on full-face
        face_weight = 0.7

    periocular_weight = 1.0 - face_weight

    # Compute weighted fusion
    fused_distance = (face_weight * face_distance) + (periocular_weight * periocular_distance)

    return fused_distance, face_weight


def compute_best_match_with_fusion(
    query_face_emb: Optional[List[float]],
    query_periocular_emb: Optional[List[float]],
    inmate_face_encodings: List[List[float]],
    inmate_periocular_encodings: List[List[float]],
    glasses_detected: bool = False,
    glasses_confidence: float = 0.0
) -> Tuple[float, str]:
    """
    Find best match using fusion of face and periocular embeddings.

    Args:
        query_face_emb: Query full-face embedding (512-dim) or None
        query_periocular_emb: Query periocular embedding (512-dim) or None
        inmate_face_encodings: List of inmate full-face embeddings
        inmate_periocular_encodings: List of inmate periocular embeddings
        glasses_detected: Whether glasses detected in query
        glasses_confidence: Glasses detection confidence

    Returns:
        Tuple of (best_distance, match_method)
        best_distance: Lowest fused distance found
        match_method: 'fusion', 'face_only', or 'periocular_only'
    """
    from scipy.spatial.distance import cosine

    best_distance = float('inf')
    match_method = 'none'

    # Case 1: Both embeddings available - use fusion
    if query_face_emb is not None and query_periocular_emb is not None:
        for face_enc in inmate_face_encodings:
            face_dist = cosine(query_face_emb, face_enc)

            # Try to match periocular if available
            if inmate_periocular_encodings:
                for peri_enc in inmate_periocular_encodings:
                    peri_dist = cosine(query_periocular_emb, peri_enc)
                    fused_dist, _ = compute_fusion_score(
                        face_dist, peri_dist, glasses_detected, glasses_confidence
                    )
                    if fused_dist < best_distance:
                        best_distance = fused_dist
                        match_method = 'fusion'
            else:
                # No periocular encodings for inmate - use face only
                if face_dist < best_distance:
                    best_distance = face_dist
                    match_method = 'face_only'

    # Case 2: Only face embedding - use face matching
    elif query_face_emb is not None:
        for face_enc in inmate_face_encodings:
            face_dist = cosine(query_face_emb, face_enc)
            if face_dist < best_distance:
                best_distance = face_dist
                match_method = 'face_only'

    # Case 3: Only periocular embedding - use periocular matching
    elif query_periocular_emb is not None and inmate_periocular_encodings:
        for peri_enc in inmate_periocular_encodings:
            peri_dist = cosine(query_periocular_emb, peri_enc)
            if peri_dist < best_distance:
                best_distance = peri_dist
                match_method = 'periocular_only'

    return best_distance, match_method


def detect_all_faces(frame) -> Optional[Dict]:
    """
    Detect ALL faces in an image using MTCNN and get embeddings for each.

    Args:
        frame: BGR OpenCV image

    Returns:
        Dict with keys:
            - success: bool
            - total_faces: int
            - faces: List of face data, each containing:
                - face_index: int
                - bbox: {x, y, width, height}
                - confidence: float
                - face_embedding: List[float] (512-dim) or None
                - periocular_embedding: List[float] (512-dim) or None
                - glasses_detected: bool
                - glasses_confidence: float
        Returns None if request fails completely.
    """
    b64 = _encode_image_to_base64(frame)
    if not b64:
        return None

    payload = {"image": f"data:image/jpeg;base64,{b64}"}

    try:
        # Longer timeout for multi-face detection (processing multiple faces)
        resp = requests.post(DETECT_ALL_FACES_URL, json=payload, timeout=REQUEST_TIMEOUT * 3)
        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        print(f"[embedding_client] Multi-face detection request failed: {e}")
        return None