# backend/app/routes/api/user_routes.py
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User

user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/users')

@user_api_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_api_bp.route('/<int:user_id>/toggle', methods=['PATCH'])
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'message': 'User status updated', 'is_active': user.is_active})

@user_api_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'})
