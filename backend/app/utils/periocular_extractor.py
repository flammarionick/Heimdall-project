# backend/app/utils/periocular_extractor.py
"""
Periocular Region Extraction Module

Extracts the eye region (periocular area) from face images for robust
recognition when full-face matching fails (e.g., glasses, masks, occlusions).

Uses MediaPipe Face Mesh for precise 468-point landmark detection.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List

# MediaPipe Face Mesh landmark indices for eye regions
# Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png

# Left eye landmarks (as seen in image - actually person's right eye)
LEFT_EYE_LANDMARKS = [
    # Upper eyelid
    246, 161, 160, 159, 158, 157, 173,
    # Lower eyelid
    33, 7, 163, 144, 145, 153, 154, 155, 133,
    # Eye corners
    130, 247, 30, 29, 27, 28, 56, 190,
]

# Right eye landmarks (as seen in image - actually person's left eye)
RIGHT_EYE_LANDMARKS = [
    # Upper eyelid
    466, 388, 387, 386, 385, 384, 398,
    # Lower eyelid
    263, 249, 390, 373, 374, 380, 381, 382, 362,
    # Eye corners
    359, 467, 260, 259, 257, 258, 286, 414,
]

# Extended periocular region (includes eyebrows)
LEFT_PERIOCULAR_EXTENDED = [
    # Eyebrow
    70, 63, 105, 66, 107, 55, 65, 52, 53, 46,
    # Under eye / cheek upper
    111, 117, 118, 119, 120, 121, 128, 245,
] + LEFT_EYE_LANDMARKS

RIGHT_PERIOCULAR_EXTENDED = [
    # Eyebrow
    300, 293, 334, 296, 336, 285, 295, 282, 283, 276,
    # Under eye / cheek upper
    340, 346, 347, 348, 349, 350, 357, 465,
] + RIGHT_EYE_LANDMARKS

# Nose bridge landmarks (for glasses detection)
NOSE_BRIDGE_LANDMARKS = [6, 197, 195, 5, 4, 1, 19, 94, 2]

# Glasses frame typical landmarks
GLASSES_FRAME_LANDMARKS = [
    # Left side
    130, 247, 30, 29, 27, 28, 56, 190, 243, 112, 26, 22, 23, 24, 110, 25,
    # Right side
    359, 467, 260, 259, 257, 258, 286, 414, 463, 341, 256, 252, 253, 254, 339, 255,
    # Bridge
    6, 197, 195, 5, 4,
]


class PeriocularExtractor:
    """
    Extracts periocular (eye region) features from face images.

    Uses MediaPipe Face Mesh for landmark detection and extracts
    normalized eye region crops suitable for embedding generation.
    """

    def __init__(self, static_image_mode: bool = True,
                 max_num_faces: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """
        Initialize the periocular extractor.

        Args:
            static_image_mode: If True, treats each image independently (better for photos)
            max_num_faces: Maximum number of faces to detect
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for landmark tracking
        """
        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=static_image_mode,
                max_num_faces=max_num_faces,
                refine_landmarks=True,  # Enables iris landmarks
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
            self.mp_drawing = mp.solutions.drawing_utils
            self.initialized = True
        except ImportError:
            print("[PeriocularExtractor] MediaPipe not installed. Run: pip install mediapipe")
            self.initialized = False
        except Exception as e:
            print(f"[PeriocularExtractor] Error initializing: {e}")
            self.initialized = False

    def extract_landmarks(self, image: np.ndarray) -> Optional[List[Tuple[float, float, float]]]:
        """
        Extract 468 facial landmarks from an image.

        Args:
            image: BGR image (OpenCV format)

        Returns:
            List of (x, y, z) normalized coordinates, or None if no face detected
        """
        if not self.initialized:
            return None

        # Convert BGR to RGB for MediaPipe
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image
        results = self.face_mesh.process(rgb_image)

        if not results.multi_face_landmarks:
            return None

        # Get first face landmarks
        face_landmarks = results.multi_face_landmarks[0]

        # Convert to list of tuples
        landmarks = []
        for lm in face_landmarks.landmark:
            landmarks.append((lm.x, lm.y, lm.z))

        return landmarks

    def get_landmark_points(self, landmarks: List[Tuple[float, float, float]],
                           indices: List[int],
                           image_shape: Tuple[int, int]) -> np.ndarray:
        """
        Convert normalized landmark coordinates to pixel coordinates.

        Args:
            landmarks: List of normalized (x, y, z) coordinates
            indices: List of landmark indices to extract
            image_shape: (height, width) of the image

        Returns:
            numpy array of (x, y) pixel coordinates
        """
        h, w = image_shape[:2]
        points = []
        for idx in indices:
            if idx < len(landmarks):
                x = int(landmarks[idx][0] * w)
                y = int(landmarks[idx][1] * h)
                points.append([x, y])
        return np.array(points, dtype=np.int32)

    def extract_periocular_region(self, image: np.ndarray,
                                   landmarks: List[Tuple[float, float, float]],
                                   eye: str = 'both',
                                   padding: float = 0.3,
                                   output_size: Tuple[int, int] = (128, 64)) -> Dict:
        """
        Extract the periocular region(s) from an image.

        Args:
            image: BGR image
            landmarks: Facial landmarks from extract_landmarks()
            eye: 'left', 'right', or 'both'
            padding: Relative padding around eye region (0.3 = 30%)
            output_size: (width, height) of output crop

        Returns:
            Dict with keys:
                - 'left_eye': cropped left eye region (or None)
                - 'right_eye': cropped right eye region (or None)
                - 'combined': both eyes side by side (or None)
                - 'left_bbox': bounding box for left eye
                - 'right_bbox': bounding box for right eye
        """
        h, w = image.shape[:2]
        result = {
            'left_eye': None,
            'right_eye': None,
            'combined': None,
            'left_bbox': None,
            'right_bbox': None
        }

        if landmarks is None:
            return result

        def extract_eye_crop(landmark_indices: List[int]) -> Tuple[Optional[np.ndarray], Optional[Tuple]]:
            """Extract and normalize a single eye region."""
            points = self.get_landmark_points(landmarks, landmark_indices, (h, w))

            if len(points) < 3:
                return None, None

            # Get bounding box
            x_min, y_min = points.min(axis=0)
            x_max, y_max = points.max(axis=0)

            # Add padding
            width = x_max - x_min
            height = y_max - y_min
            pad_x = int(width * padding)
            pad_y = int(height * padding)

            x1 = max(0, x_min - pad_x)
            y1 = max(0, y_min - pad_y)
            x2 = min(w, x_max + pad_x)
            y2 = min(h, y_max + pad_y)

            # Crop and resize
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                return None, None

            # Resize to standard size (half width for single eye)
            resized = cv2.resize(crop, (output_size[0] // 2, output_size[1]))

            return resized, (x1, y1, x2, y2)

        # Extract left eye (as seen in image)
        if eye in ['left', 'both']:
            left_crop, left_bbox = extract_eye_crop(LEFT_PERIOCULAR_EXTENDED)
            result['left_eye'] = left_crop
            result['left_bbox'] = left_bbox

        # Extract right eye (as seen in image)
        if eye in ['right', 'both']:
            right_crop, right_bbox = extract_eye_crop(RIGHT_PERIOCULAR_EXTENDED)
            result['right_eye'] = right_crop
            result['right_bbox'] = right_bbox

        # Combine both eyes side by side
        if eye == 'both' and result['left_eye'] is not None and result['right_eye'] is not None:
            result['combined'] = np.hstack([result['left_eye'], result['right_eye']])

        return result

    def detect_glasses(self, image: np.ndarray,
                       landmarks: Optional[List[Tuple[float, float, float]]] = None) -> Dict:
        """
        Detect if the person is wearing glasses.

        Uses multiple heuristics:
        1. Edge detection on nose bridge area
        2. Reflection detection in eye region
        3. Frame edge detection around eyes

        Args:
            image: BGR image
            landmarks: Optional pre-computed landmarks

        Returns:
            Dict with:
                - 'glasses_detected': bool
                - 'confidence': float (0-1)
                - 'type': 'clear', 'tinted', 'sunglasses', or 'none'
        """
        result = {
            'glasses_detected': False,
            'confidence': 0.0,
            'type': 'none'
        }

        if landmarks is None:
            landmarks = self.extract_landmarks(image)

        if landmarks is None:
            return result

        h, w = image.shape[:2]

        # Method 1: Check nose bridge for horizontal edges (glasses frame)
        bridge_points = self.get_landmark_points(landmarks, NOSE_BRIDGE_LANDMARKS, (h, w))
        if len(bridge_points) >= 2:
            x_min, y_min = bridge_points.min(axis=0)
            x_max, y_max = bridge_points.max(axis=0)

            # Expand region slightly
            pad = 10
            x1 = max(0, x_min - pad)
            y1 = max(0, y_min - pad)
            x2 = min(w, x_max + pad)
            y2 = min(h, y_max + pad)

            bridge_region = image[y1:y2, x1:x2]
            if bridge_region.size > 0:
                # Convert to grayscale and detect edges
                gray = cv2.cvtColor(bridge_region, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size

                # High edge density on nose bridge suggests glasses frame
                if edge_density > 0.15:
                    result['confidence'] += 0.4

        # Method 2: Check for reflections/glare in eye regions
        left_points = self.get_landmark_points(landmarks, LEFT_EYE_LANDMARKS, (h, w))
        right_points = self.get_landmark_points(landmarks, RIGHT_EYE_LANDMARKS, (h, w))

        for eye_points in [left_points, right_points]:
            if len(eye_points) >= 3:
                x_min, y_min = eye_points.min(axis=0)
                x_max, y_max = eye_points.max(axis=0)

                eye_region = image[max(0,y_min):min(h,y_max), max(0,x_min):min(w,x_max)]
                if eye_region.size > 0:
                    # Check for bright spots (reflections)
                    gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
                    bright_pixels = np.sum(gray > 220) / gray.size

                    if bright_pixels > 0.05:
                        result['confidence'] += 0.15

                    # Check for uniform dark regions (tinted/sunglasses)
                    dark_pixels = np.sum(gray < 50) / gray.size
                    if dark_pixels > 0.3:
                        result['confidence'] += 0.2
                        result['type'] = 'tinted'

        # Method 3: Check frame edges around eyes
        frame_points = self.get_landmark_points(landmarks, GLASSES_FRAME_LANDMARKS, (h, w))
        if len(frame_points) >= 10:
            # Create convex hull and check for strong edges along it
            hull = cv2.convexHull(frame_points)
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [hull], 0, 255, 2)

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 30, 100)

            # Check edge overlap with expected frame location
            overlap = cv2.bitwise_and(edges, mask)
            if np.sum(mask > 0) > 0:
                overlap_ratio = np.sum(overlap > 0) / np.sum(mask > 0)
                if overlap_ratio > 0.3:
                    result['confidence'] += 0.3

        # Determine final result
        result['confidence'] = min(1.0, result['confidence'])
        result['glasses_detected'] = result['confidence'] > 0.5

        if result['glasses_detected']:
            if result['type'] == 'none':
                result['type'] = 'clear'
            # Check if sunglasses (very dark eye region)
            if result['type'] == 'tinted' and result['confidence'] > 0.7:
                result['type'] = 'sunglasses'

        return result

    def process_image(self, image: np.ndarray,
                      output_size: Tuple[int, int] = (128, 64)) -> Dict:
        """
        Full processing pipeline: extract landmarks, periocular regions, and detect glasses.

        Args:
            image: BGR image
            output_size: Size of periocular crop (width, height)

        Returns:
            Dict with all extracted features and metadata
        """
        result = {
            'success': False,
            'landmarks': None,
            'periocular': None,
            'glasses': None,
            'error': None
        }

        if not self.initialized:
            result['error'] = 'PeriocularExtractor not initialized (MediaPipe missing?)'
            return result

        try:
            # Extract landmarks
            landmarks = self.extract_landmarks(image)
            if landmarks is None:
                result['error'] = 'No face detected'
                return result

            result['landmarks'] = landmarks

            # Extract periocular regions
            periocular = self.extract_periocular_region(
                image, landmarks, eye='both', output_size=output_size
            )
            result['periocular'] = periocular

            # Detect glasses
            glasses = self.detect_glasses(image, landmarks)
            result['glasses'] = glasses

            result['success'] = periocular['combined'] is not None

        except Exception as e:
            result['error'] = str(e)

        return result

    def close(self):
        """Release resources."""
        if self.initialized and hasattr(self, 'face_mesh'):
            self.face_mesh.close()


# Singleton instance for reuse
_extractor_instance = None

def get_periocular_extractor() -> PeriocularExtractor:
    """Get or create singleton PeriocularExtractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = PeriocularExtractor()
    return _extractor_instance


def extract_periocular_from_image(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Convenience function to extract combined periocular region from an image.

    Args:
        image: BGR image

    Returns:
        Combined periocular region (128x64) or None if extraction failed
    """
    extractor = get_periocular_extractor()
    result = extractor.process_image(image)

    if result['success'] and result['periocular']:
        return result['periocular']['combined']
    return None


def detect_glasses_in_image(image: np.ndarray) -> Dict:
    """
    Convenience function to detect glasses in an image.

    Args:
        image: BGR image

    Returns:
        Dict with glasses detection results
    """
    extractor = get_periocular_extractor()
    landmarks = extractor.extract_landmarks(image)
    return extractor.detect_glasses(image, landmarks)
