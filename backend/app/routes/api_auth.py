# app/routes/api_auth.py
from flask import Blueprint, request, jsonify
from flask_login import login_user
from app.models.user import User

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api')

@api_auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()

    if user and user.check_password(data.get('password')):
        login_user(user)
        return jsonify({ "role": "admin" if user.is_admin else "user" }), 200
    return jsonify({ "error": "Invalid credentials" }), 401
