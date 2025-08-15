import numpy as np
import cv2
from skimage.feature import hog

TARGET_SIZE_WH = (48, 144)  # width, height
PIXELS_PER_CELL = (8, 8)
CELLS_PER_BLOCK = (2, 2)
ORIENTATIONS = 9

def extract_hog_3060(frame_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, TARGET_SIZE_WH, interpolation=cv2.INTER_AREA)

    feat = hog(
        resized,
        orientations=ORIENTATIONS,
        pixels_per_cell=PIXELS_PER_CELL,
        cells_per_block=CELLS_PER_BLOCK,
        block_norm='L2-Hys',
        transform_sqrt=True,
        feature_vector=True,
    ).astype(np.float32)

    if feat.size != 3060:
        # Fallback padding/trim (shouldn’t trigger with these params)
        if feat.size < 3060:
            reps = int(np.ceil(3060 / max(1, feat.size)))
            feat = np.tile(feat, reps)[:3060]
        else:
            feat = feat[:3060]
    return feat