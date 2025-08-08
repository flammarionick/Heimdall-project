from flask import Flask, request, jsonify
from facenet_pytorch import InceptionResnetV1
import torch
import numpy as np
from PIL import Image
import io
import cv2

app = Flask(__name__)

# Load model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = np.array(img)
    img = cv2.resize(img, (160, 160)) / 255.0
    img = torch.tensor(img).permute(2, 0, 1).unsqueeze(0).float()
    return img.to(device)

@app.route('/encode', methods=['POST'])
def encode():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    image = request.files['image'].read()
    img_tensor = preprocess_image(image)
    with torch.no_grad():
        embedding = model(img_tensor).cpu().numpy().flatten().tolist()
    return jsonify({"embedding": embedding})

if __name__ == '__main__':
    app.run(port=5001)