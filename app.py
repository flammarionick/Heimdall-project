import os
import sqlite3
import cv2
import tensorflow as tf
from flask import Flask, request, render_template

app = Flask(__name__)

# Folder to store uploaded images
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize the SQLite database to store inmate data
def init_db():
    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS inmates
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       inmate_id TEXT NOT NULL UNIQUE,
                       status TEXT,
                       face_image TEXT)''')
    conn.commit()
    conn.close()

# Function to store inmate data in the database
def store_inmate_data(name, inmate_id, status, file_path):
    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO inmates (name, inmate_id, status, face_image)
                      VALUES (?, ?, ?, ?)''', (name, inmate_id, status, file_path))
    conn.commit()
    conn.close()

# Homepage route (inmate registration form)
@app.route('/')
def index():
    return render_template('index.html')

# Register inmate route
@app.route('/register', methods=['POST'])
def register_inmate():
    name = request.form.get('name')
    inmate_id = request.form.get('inmate_id')
    status = request.form.get('status')
    file = request.files['file']

    if file.filename == '':
        return "No file selected"

    # Save the uploaded face image
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Process the image with the AI model (facial recognition)
    recognition_result = process_image(file_path)

    # Store inmate data in the database
    store_inmate_data(name, inmate_id, status, file_path)

    return f"Inmate {name} (ID: {inmate_id}, Status: {status}) registered successfully with recognition result: {recognition_result}"

# Dummy image processing (facial recognition) function
def process_image(file_path):
    # Load the image and preprocess it
    image = cv2.imread(file_path)
    processed_image = preprocess_for_model(image)  # Preprocessing logic here

    # Load your trained AI face recognition model
    model = tf.keras.models.load_model('path_to_model.h5')

    # Run the image through the model for facial recognition
    result = model.predict(processed_image)

    return result

# Dummy preprocessing function for AI model input
def preprocess_for_model(image):
    resized_image = cv2.resize(image, (224, 224))  # Assuming model takes 224x224 input
    processed_image = resized_image / 255.0  # Normalize
    return processed_image.reshape(1, 224, 224, 3)  # Add batch dimension

# Initialize the database when the app starts
if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)