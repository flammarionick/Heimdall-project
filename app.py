import os
import cv2
import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify, session, abort, redirect, render_template
from flask_mail import Mail, Message
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, redirect, session, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session handling

# Ensure database path consistency
DATABASE_PATH = 'inmate_database.db'



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
    conn = sqlite3.connect('inmate_database.db')
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


# Admin route to perform actions on users (e.g., delete, suspend)
@app.route('/admin/user_action', methods=['POST'])
def user_action():
    if not is_default_admin():
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    username = data.get('username')
    action = data.get('action')  # 'edit', 'suspend', or 'delete'

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    if action == 'delete':
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    elif action == 'suspend':
        cursor.execute("UPDATE users SET status = 'suspended' WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'User {username} {action}d successfully.'})



# Route to serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Initialize database and create default admin
if __name__ == '__main__':
    init_db()  # This should create the 'users' table and any others if not already created
    verify_or_add_admin()  # Now we can safely verify or add the default admin
    app.run(debug=True)