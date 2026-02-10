import torch
import numpy as np
import sqlite3
from facenet_pytorch import InceptionResnetV1
from retinaface import RetinaFace
from PIL import Image
import cv2

# Path to your SQLite DB
db_path = r"C:\Users\Nicholas Eke\Downloads\Heimdall-project\backend\migrations\heimdall.db"

# Load embedding model (keep facenet for embeddings)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Path of test image (the one you uploaded for recognition)
test_img_path = r"C:\Users\Nicholas Eke\Downloads\Heimdall-project\backend\app\static\inmate_images\AA-9E4092_1.jpg"

def get_embedding(img_path):
    img = cv2.imread(img_path)
    detections = RetinaFace.detect_faces(img)
    if isinstance(detections, dict) and len(detections) > 0:
        # Take the first detected face
        face_key = list(detections.keys())[0]
        facial_area = detections[face_key]["facial_area"]  # [x1, y1, x2, y2]
        x1, y1, x2, y2 = facial_area
        face = img[y1:y2, x1:x2]
        face = cv2.resize(face, (160, 160))  # resize to Facenet input
        face = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
        face_tensor = torch.tensor(np.array(face)).permute(2, 0, 1).unsqueeze(0).float()
        face_tensor = (face_tensor - 127.5) / 128.0  # normalize
        emb = resnet(face_tensor.to(device)).detach().cpu().numpy()[0]
        return emb
    else:
        print(f"⚠️ No face detected in {img_path}")
        return None

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Step 1: Generate embedding for test image
test_emb = get_embedding(test_img_path)
if test_emb is None:
    exit()

# Step 2: Fetch embeddings from SQLite DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, feace_encoding FROM inmate")
rows = cursor.fetchall()

for inmate_id, emb_blob in rows:
    try:
        db_emb = np.frombuffer(emb_blob, dtype=np.float32)
    except Exception as e:
        print(f"⚠️ Failed to decode embedding for inmate {inmate_id}: {e}")
        continue

    sim = cosine_similarity(test_emb, db_emb)
    print(f"Compared with inmate {inmate_id} → similarity = {sim:.4f}")

    if sim > 0.65:  # threshold
        print(f"✅ MATCH FOUND with inmate {inmate_id} (similarity={sim:.4f})")

conn.close()