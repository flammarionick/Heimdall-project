# app/utils/embedding.py
import torch
from facenet_pytorch import InceptionResnetV1
from torchvision import transforms
import numpy as np
import cv2

# Load model once
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
face_model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize([0.5], [0.5])
])

def extract_embedding_from_frame(frame):
    try:
        face_img = transform(frame).unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = face_model(face_img).cpu().numpy()[0]
        return embedding
    except Exception as e:
        print("Embedding extraction failed:", e)
        return None
