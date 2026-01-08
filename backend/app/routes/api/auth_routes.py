# backend/app/routes/api/auth_routes.py
"""
Legacy auth routes - kept for backward compatibility.
The main auth API is in app/routes/auth_api.py
"""

from flask import Blueprint, request, jsonify
from flask_login import login_user, current_user
from app.models.user import User
from app.extensions import db
from datetime import datetime

auth_api_bp = Blueprint('auth_api_legacy', __name__, url_prefix='/api/auth')


@auth_api_bp.route('/login', methods=['POST'])
def login():
    """Alternative login endpoint at /api/auth/login"""
    data = request.get_json(silent=True) or {}

    # Support both email and username login
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not password:
        return jsonify({'error': 'Password required'}), 400

    # Try to find user by email or username
    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    if not user and username:
        user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 401

    if not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.is_suspended:
        return jsonify({'error': 'Account suspended'}), 403

    login_user(user)
    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'ok': True,
        'is_admin': user.is_admin,
        'user': user.to_public_dict()
    })


@auth_api_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user info."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(current_user.to_public_dict())
