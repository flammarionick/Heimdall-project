from functools import wraps
from flask import request, jsonify
from app.utils.jwt import decode_jwt

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Token missing'}), 401

        token = auth_header.split(" ")[1]
        payload = decode_jwt(token)
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401

        # Inject user_id and role into kwargs if needed
        return f(*args, **kwargs)
    return decorated_function
