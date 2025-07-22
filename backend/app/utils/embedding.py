# app/utils/embedding.py
import torch
from facenet_pytorch import InceptionResnetV1
from torchvision import transforms
from facenet_pytorch import MTCNN, InceptionResnetV1
import numpy as np
import cv2

# Load models once
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def extract_embedding_from_frame(frame):
    try:
        # Convert BGR (OpenCV) to RGB
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face and crop
        face = mtcnn(img_rgb)
        if face is None:
            print("[Embedding] No face detected.")
            return None

        # Expand batch dim and move to device
        face = face.unsqueeze(0).to(device)

        # Extract embedding
        embedding = resnet(face).detach().cpu().numpy()[0]
        return embedding
    except Exception as e:
        print("[Embedding Error]:", e)
        return None
