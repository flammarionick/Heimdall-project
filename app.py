import os
import sqlite3
import cv2
import tensorflow as tf
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)

# Configure email notifications
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_password'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize SQLite database to store data
def init_db():
    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    # Create tables for inmates, users, and activity logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'user')) NOT NULL,
            user_id TEXT UNIQUE
        )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inmates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        inmate_id TEXT NOT NULL UNIQUE,
        status TEXT,
        face_image TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Register a new user with a unique ID
@app.route('/register_user', methods=['POST'])
def register_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    user_id = f'USER-{int(datetime.now().timestamp())}'

    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password, role, user_id) VALUES (?, ?, ?, ?)',
                   (username, password, role, user_id))
    conn.commit()
    conn.close()
    return f"User {username} registered successfully with ID {user_id}"

# Authentication route
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify(success=True, user_id=user[4], role=user[3])  # Returning user ID and role
    return jsonify(success=False)

# Log activity
def log_activity(user_id, action):
    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO activity_log (user_id, action) VALUES (?, ?)', (user_id, action))
    conn.commit()
    conn.close()

# Send email notification
def send_notification(email, subject, message):
    msg = Message(subject, sender='your_email@example.com', recipients=[email])
    msg.body = message
    mail.send(msg)

# Register inmate and store profile
@app.route('/register_inmate', methods=['POST'])
def register_inmate():
    # Existing code to register inmate...
    # Log activity
    log_activity(user_id="admin", action="Registered new inmate")

    # Send notification example
    send_notification("stakeholder@example.com", "New Inmate Registered",
                      f"Inmate {name} has been successfully registered.")
    return f"Inmate {name} registered successfully."

# Generate report (e.g., PDF or CSV)
@app.route('/generate_report', methods=['GET'])
def generate_report():
    conn = sqlite3.connect('inmate_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inmates")
    inmates = cursor.fetchall()
    conn.close()
    # Implement export functionality
    return jsonify(inmates)

# Initialize database
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
