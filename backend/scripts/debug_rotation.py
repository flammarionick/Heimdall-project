#!/usr/bin/env python3
"""Debug script to check if MTCNN detects rotated faces."""

import os
import sys
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import torch
from facenet_pytorch import MTCNN

device = torch.device('cpu')
mtcnn = MTCNN(
    image_size=160,
    margin=20,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=False,
    select_largest=True,
    keep_all=False,
    device=device
)

def test_rotation_detection():
    # Get a sample image
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    import sqlite3
    db_path = os.path.join(backend_dir, 'instance', 'heimdall.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT mugshot_path FROM inmate WHERE mugshot_path IS NOT NULL LIMIT 5")
    paths = cursor.fetchall()
    conn.close()

    print("Testing MTCNN face detection at various rotations...")
    print("=" * 60)

    for path_tuple in paths:
        mugshot_path = path_tuple[0]
        clean_path = mugshot_path.lstrip('/')
        full_path = os.path.join(backend_dir, 'app', clean_path)

        if not os.path.exists(full_path):
            full_path = os.path.join(backend_dir, 'app', 'static', 'inmate_images',
                                     os.path.basename(mugshot_path))

        if not os.path.exists(full_path):
            continue

        image = cv2.imread(full_path)
        if image is None:
            continue

        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        print(f"\nImage: {os.path.basename(full_path)}")

        for angle in [0, 15, 30, 45, 60]:
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

            img_rgb = cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)

            try:
                boxes, probs, landmarks = mtcnn.detect(pil_image, landmarks=True)

                if boxes is not None and len(boxes) > 0:
                    conf = probs[0] if probs is not None else 0
                    has_landmarks = landmarks is not None and len(landmarks) > 0
                    print(f"  {angle:3d}°: DETECTED (conf={conf:.3f}, landmarks={'YES' if has_landmarks else 'NO'})")

                    if has_landmarks:
                        lm = landmarks[0]
                        left_eye = lm[0]
                        right_eye = lm[1]
                        dx = right_eye[0] - left_eye[0]
                        dy = right_eye[1] - left_eye[1]
                        eye_angle = np.degrees(np.arctan2(dy, dx))
                        print(f"       Eye angle: {eye_angle:.1f}° (should be ~{angle}°)")
                else:
                    print(f"  {angle:3d}°: NOT DETECTED")
            except Exception as e:
                print(f"  {angle:3d}°: ERROR - {e}")

        break  # Just test one image for now


if __name__ == '__main__':
    test_rotation_detection()
