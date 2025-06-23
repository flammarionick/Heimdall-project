# backend/app/routes/api/auth_routes.py
from flask import Blueprint, request, jsonify
# backend/app/routes/api/auth_routes.py
from flask import Blueprint, request, jsonify
from app.models.user import User
from werkzeug.security import check_password_hash

auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/auth')

@auth_api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password, data['password']):
        return jsonify({'role': user.role})
    return jsonify({'error': 'Unauthorized'}), 401
