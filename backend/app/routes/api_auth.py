# app/routes/api_auth.py
from app.utils.jwt import generate_jwt
from app.utils.auth_helpers import login_or_jwt_required

from flask import Blueprint, request, jsonify

api_auth_bp = Blueprint('api_auth_bp', __name__)

@api_auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    input_value = data.get('email')
    password = data.get('password')

    user = User.query.filter(
        (User.username == input_value) | (User.email == input_value)
    ).first()

    if user and user.check_password(password):
        token = generate_jwt(user.id, user.is_admin)
        return jsonify({
            "message": "Login successful",
            "token": token,
            "role": "admin" if user.is_admin else "user"
        }), 200

    return jsonify({"message": "Invalid credentials"}), 401