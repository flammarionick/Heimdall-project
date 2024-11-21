import os
import cv2
import numpy as np
import tensorflow as tf
from flask import Flask, Response, flash, request, jsonify, session, abort, redirect, render_template
from flask_mail import Mail, Message
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, session, url_for
import sqlite3
from datetime import datetime
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array, load_img
import random
import string
import tensorflow as tf
from PIL import Image
from scipy.spatial.distance import cosine



# Set up Flask application and database configuration
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session handling

# Load the EfficientNet-B4 model
MODEL_PATH = 'models/efficientnet_b4_finetuned.h5'  # Correct relative path
model = load_model(MODEL_PATH)

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'inmate_database.db')  # Replace 'database.db' with your database file name


# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'inmate_database.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Folder to store uploaded images
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

   
# Preprocess function
def preprocess_image(image):
    img = load_img(image, target_size=(380, 380))  # Match EfficientNet-B4 input size
    img_array = img_to_array(img) / 255.0  # Normalize to [0, 1]
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array


class User(db.Model):
    __tablename__ = 'users'  # Table name for the User model
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Role-based access like 'admin' or 'user'
    status = db.Column(db.String(20), nullable=False, default='active')  # Status: 'active' or 'suspended'

    def __repr__(self):
        return f'<User {self.username}>'
    
    # Initialize database and create tables if they don't exist
with app.app_context():
    db.create_all()

# Database setup: Creates tables if they don't exist
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       username TEXT NOT NULL UNIQUE,
                       password TEXT NOT NULL,
                       role TEXT NOT NULL,
                       user_id TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inmates
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       inmate_id TEXT NOT NULL UNIQUE,
                       status TEXT,
                       face_image TEXT)''')
    conn.commit()
    conn.close()

# Create a default admin user with a hashed password, ensuring no duplicate entries
def verify_or_add_admin():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Delete any existing admin user entry to avoid conflicts
    cursor.execute("DELETE FROM users WHERE username = ?", ("Admin",))
    conn.commit()

    # Insert the new admin credentials with hashed password
    hashed_password = generate_password_hash("admin123")
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("Admin", hashed_password, "admin"))
    conn.commit()
    print("Default admin account created with username 'Admin' and hashed password:", hashed_password)

    conn.close()


# Check if user is default admin
def is_default_admin():
    return session.get('username') == "Admin" and session.get('role') == "admin"


# Function to retrieve user role from the database
def get_user_from_db(username, password):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user  # Returns None if user not found, otherwise returns (username, role)



# Folder to store uploaded images
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATABASE_PATH = 'inmate_database.db'  # SQLite database path


# Login: Verifies user credentials and sets session variables
# Flask backend login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        db_username, db_password, db_role = user
        print("Database password hash:", db_password)  # Debugging print
        print("Entered password hash:", generate_password_hash(password))  # Debugging print for comparison

        if check_password_hash(db_password, password):
            session['username'] = db_username
            session['role'] = db_role

            # Redirect based on role
            if db_role == 'admin':
                return jsonify({'redirect_url': '/admin-dashboard', 'username': db_username, 'isAdmin': True}), 200
            else:
                return jsonify({'redirect_url': '/landing', 'username': db_username, 'isAdmin': False}), 200
        else:
            print("Password hash did not match.")  # Debugging print
            return jsonify({'error': 'Invalid credentials'}), 401
    else:
        print("User not found.")  # Debugging print
        return jsonify({'error': 'Invalid credentials'}), 401

# Admin route to display the admin dashboard
@app.route('/admin-dashboard')
def admin_dashboard():
    if not is_default_admin():  # Check if the user is the default admin
        return redirect(url_for('login'))  # Redirect to login if not the default admin

    # Retrieve all users to display on the admin dashboard
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, status FROM users WHERE role != 'admin'")
    users = [{'username': row[0], 'role': row[1], 'status': row[2]} for row in cursor.fetchall()]
    conn.close()

    # Render the admin dashboard template, passing in the users list
    return render_template('admin_dashboard.html', users=users)


# Register a new user with hashed password
@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.get_json()  # Get JSON data from the request
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    user_id = f'USER-{int(datetime.now().timestamp())}'

    if not username or not password or not role:
        return jsonify({'error': 'Invalid input. All fields are required.'}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        return jsonify({'error': 'Username already exists'}), 409

    hashed_password = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password, role, user_id) VALUES (?, ?, ?, ?)',
                   (username, hashed_password, role, user_id))
    conn.commit()
    conn.close()
    return jsonify({'message': f"User {username} registered successfully with ID {user_id}"}), 201


def generate_inmate_id():
    """Generate a unique inmate ID."""
    prefix = "IM"  # You can change this prefix if needed
    unique_id = ''.join(random.choices(string.digits, k=6))  # Generates a 6-digit unique ID
    return f"{prefix}{unique_id}"

@app.route('/register_inmate', methods=['POST'])
def register_inmate():
    try:
        name = request.form['name']
        status = request.form['status']
        face_image = request.files['face_image']

        # Save the face image securely
        filename = secure_filename(face_image.filename)
        image_path = os.path.join('static/uploads', filename)
        face_image.save(image_path)

        # Load and preprocess the image
        image = Image.open(image_path).convert("L")
        image = image.resize((96, 96))  # Match model input size
        image_array = img_to_array(image)
        image_array = np.expand_dims(image_array, axis=0) / 255.0  # Normalize

        # Generate the face encoding
        face_encoding = model.predict(image_array)[0].tolist()

        # Generate a unique inmate ID
        inmate_id = generate_inmate_id()

        # Insert into the database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO inmates (name, inmate_id, status, face_image_path, face_encoding) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, inmate_id, status, image_path, str(face_encoding)),
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Inmate registered successfully!'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


        return jsonify({"message": "Inmate registered successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# AI Prediction Route
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Check if a file is part of the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join('static/uploads', filename)
        file.save(file_path)

        # Load and preprocess the image
        image = Image.open(file_path).convert("L")
        image = image.resize((96, 96))  # Resize to match model input size
        image_array = img_to_array(image)
        image_array = np.expand_dims(image_array, axis=0) / 255.0  # Normalize

        # Debug: Print image array shape
        print(f"Image array shape: {image_array.shape}")

        # Generate the embedding using the model
        embedding = model.predict(image_array)[0].tolist()  # Convert prediction to list

        # Debug: Print predictions
        print(f"Predictions: {embedding}")

        # Connect to the database and retrieve stored embeddings
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, face_encoding, status FROM inmates")
        rows = cursor.fetchall()
        conn.close()

        # Initialize variables to find the closest match
        min_distance = float('inf')
        best_match = None

        # Compare embedding with stored embeddings
        for row in rows:
            inmate_id, name, face_encoding, status = row
            stored_embedding = np.array(eval(face_encoding))  # Convert string back to array
            distance = cosine(embedding, stored_embedding)  # Calculate cosine similarity

            # Debug: Print distance for each comparison
            print(f"Comparing with {name}: Distance = {distance}")

            # Find the closest match
            if distance < min_distance:
                min_distance = distance
                best_match = {
                    'id': inmate_id,
                    'name': name,
                    'status': status,
                    'distance': distance
                }

        # Define a similarity threshold
        threshold = 0.5  # Adjust based on testing and model performance

        if best_match and min_distance < threshold:
            return jsonify({
                'status': 'Match found',
                'inmate': best_match
            }), 200
        else:
            return jsonify({'status': 'No match found'}), 200

    except Exception as e:
        app.logger.error(f"Error during prediction: {str(e)}")
        return jsonify({'error': f"Error processing image: {str(e)}"}), 500
    


@app.route('/video_feed')
def video_feed():
    def generate_frames():
        video = cv2.VideoCapture(0)  # Access the webcam
        while True:
            success, frame = video.read()
            if not success:
                break

            # Preprocess frame (resize, convert to grayscale, etc.)
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized_frame = cv2.resize(gray_frame, (96, 96))
            frame_array = np.expand_dims(resized_frame, axis=-1)
            frame_array = np.expand_dims(frame_array, axis=0) / 255.0

            # Generate embedding
            embedding = model.predict(frame_array)[0]

            # Connect to database and retrieve stored embeddings
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, face_encoding FROM inmates")
            rows = cursor.fetchall()
            conn.close()

            # Find the best match
            min_distance = float('inf')
            best_match = None
            for row in rows:
                inmate_id, name, face_encoding = row
                stored_embedding = np.array(eval(face_encoding))  # Convert string to array
                distance = cosine(embedding, stored_embedding)
                if distance < min_distance:  # Find closest match
                    min_distance = distance
                    best_match = {
                        'id': inmate_id,
                        'name': name,
                        'distance': distance
                    }

            # Define a threshold for matching
            threshold = 0.5  # Adjust based on your model's performance

            # Annotate frame with match result if a match is found
            if best_match and min_distance < threshold:
                text = f"Match: {best_match['name']}"
                cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No Match", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Encode the frame for streaming
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



# Route to retrieve all non-admin users (admin-only)
@app.route('/admin/get_users', methods=['GET'])
def get_users():
    print("Session Data:", session)  # Print session data for debugging
    if not is_default_admin():
        return jsonify({'error': 'Unauthorized access'}), 403

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users WHERE role != 'admin'")
    users = [{'username': row[0], 'role': row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(users), 200


# Function to retrieve a user by username
def get_user_by_username(username):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        if user_data:
            # Adjust as necessary to match column order in your database
            user = {
                "id": user_data[0],
                "username": user_data[1],
                "password": user_data[2],
                "role": user_data[3],
                "status": user_data[4]
            }
            return user
        return None
    except sqlite3.Error as e:
        print("Database error:", e)
        return None
    finally:
        conn.close()

# Function to update user information in the database
def update_user_in_database(username, new_username, new_password):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if we need to update both username and password
        if new_username and new_password:
            hashed_password = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET username = ?, password = ? WHERE username = ?",
                (new_username, hashed_password, username)
            )
        elif new_username:
            cursor.execute(
                "UPDATE users SET username = ? WHERE username = ?",
                (new_username, username)
            )
        elif new_password:
            hashed_password = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hashed_password, username)
            )
        else:
            return False  # No update made if no new values are provided

        conn.commit()
        return cursor.rowcount > 0  # Returns True if the update was successful
    except sqlite3.Error as e:
        print("Database error:", e)
        return False
    finally:
        conn.close()


@app.route('/admin/get_user/<string:username>', methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return jsonify(username=user.username, role=user.role)


# Admin route to display the edit user page
@app.route('/admin/edit_user/<string:username>', methods=['GET', 'POST'])
def edit_user(username):
     # Print all users to verify database connectivity
    users = User.query.all()
    print("All users in database:", users)
    # Fetch the user by username or return a 404 error if not found
    user = User.query.filter_by(username=username).first_or_404()
    print(user)

    if request.method == 'POST':
        # Fetch updated data from the form
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        new_role = request.form.get('role')  # Assuming role is part of the form

        # Update fields if they are provided
        if new_username:
            user.username = new_username
        if new_password:
            user.password = generate_password_hash(new_password)
        if new_role:
            user.role = new_role

        # Commit changes to the database
        db.session.commit()
        flash(f'User {user.username} has been updated successfully.', 'success')
        
        # Redirect to the admin dashboard
        return redirect(url_for('admin_dashboard'))  # Replace 'admin_dashboard' with the actual route name for the dashboard

    # Render the edit user template if the method is GET
    return render_template('edit_user.html', user=user)


@app.route('/admin/update_user/<string:username>', methods=['POST'])
def modify_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    data = request.get_json()
    if "role" in data:
        user.role = data["role"]

    db.session.commit()
    return jsonify({"message": f"User {user.username} updated successfully."})


# Admin route to update user information
@app.route('/admin/update_user', methods=['POST'])
def update_user():
    data = request.json
    username = data.get("username")
    new_username = data.get("new_username")
    new_password = data.get("new_password")

    # Perform the update in the database
    success = update_user_in_database(username, new_username, new_password)
    if success:
        return jsonify({"message": "User updated successfully"})
    else:
        return jsonify({"error": "Failed to update user"}), 400

@app.route('/admin/suspend_user/<int:user_id>', methods=['POST'])
def suspend_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.status = 'suspended' if user.status == 'active' else 'active'  # Toggle status
        db.session.commit()
        status_message = "suspended" if user.status == 'suspended' else "active"
        return jsonify({"message": f"User {status_message} successfully"}), 200
    return jsonify({"error": "User not found"}), 404

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    return jsonify({"error": "User not found"}), 404


# Route to serve the main page
@app.route('/')
def index():
    username = request.args.get('username')  # Get 'username' from query parameters
    
    user = None  # Default to None if no user is found
    if username:
        user = get_user_by_username(username)  # Attempt to fetch user by username
    
    return render_template('index.html', user=user)  # Pass user (either valid or None)

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()  # Example query to fetch user by username


# Initialize database and create default admin
if __name__ == '__main__':
    init_db()  # This should create the 'users' table and any others if not already created
    verify_or_add_admin()  # Now we can safely verify or add the default admin
    app.run(debug=True)