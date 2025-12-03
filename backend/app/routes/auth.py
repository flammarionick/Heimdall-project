# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required
from app.models.user import User
from app.forms import LoginForm
from app import db, login_manager

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")  # change if needed


# 🎯 Route for frontend React API login
@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        print("Received data from frontend:", data)

        input_value = data.get('email')
        password = data.get('password')

        if not input_value or not password:
            return jsonify({"message": "Missing credentials"}), 400

        user = User.query.filter(
            (User.username == input_value) | (User.email == input_value)
        ).first()

        print("Matched user:", user.username if user else "None")

        if user and user.check_password(password):
            print("Password matched.")
            login_user(user)
            return jsonify({
                "message": "Login successful",
                "role": "admin" if user.is_admin else "user"
            }), 200

        print("Invalid login attempt.")
        return jsonify({"message": "Invalid credentials"}), 401

    except Exception as e:
        print("Login error:", str(e))
        return jsonify({"message": "Server error"}), 500


# 🧾 Traditional server-rendered login (e.g. if you still use Jinja forms)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # 🔁 Redirect straight to React AdminDashboard.jsx
            return redirect(f"{FRONTEND_URL}/admin/dashboard")
        else:
            flash('Invalid credentials', 'danger')
    return render_template('auth/login.html', form=form)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
