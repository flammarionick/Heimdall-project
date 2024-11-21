import sqlite3
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image

# Load your trained model
model = load_model("C:/Users/Nicholas Eke/Desktop/Heimdall-project/models/efficientnet_b4_finetuned.h5")

# Connect to the database
connection = sqlite3.connect("C:/Users/Nicholas Eke/Desktop/Heimdall-project/instance/users_database.db")
cursor = connection.cursor()

# Fetch all inmates
cursor.execute("SELECT id, face_image FROM inmates")
rows = cursor.fetchall()

for row in rows:
    inmate_id, face_image_path = row
    
    # Load and preprocess the image
    try:
        image = Image.open(face_image_path).convert("L")
        image = image.resize((96, 96))  # Match model input size
        image_array = img_to_array(image)
        image_array = np.expand_dims(image_array, axis=0) / 255.0  # Normalize
        
        # Generate the face encoding
        face_encoding = model.predict(image_array)[0].tolist()  # Convert to list
        
        # Update the database with the encoding
        cursor.execute("""
            UPDATE inmates
            SET face_encoding = ?
            WHERE id = ?
        """, (str(face_encoding), inmate_id))
        print(f"Updated encoding for inmate ID {inmate_id}")
    
    except Exception as e:
        print(f"Error processing inmate ID {inmate_id}: {e}")

# Commit changes and close the connection
connection.commit()
connection.close()
