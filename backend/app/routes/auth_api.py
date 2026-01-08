from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user
from app.models.user import User
from app.extensions import db

auth_api_bp = Blueprint("auth_api", __name__, url_prefix="/auth/api")

@auth_api_bp.post("/login")
def api_login():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if user.is_suspended:
        return jsonify({"error": "Account suspended"}), 403

    login_user(user)
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Include is_admin at root level for frontend compatibility
    response = user.to_public_dict()
    response["ok"] = True
    return jsonify(response), 200


@auth_api_bp.post("/logout")
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({"ok": True}), 200


@auth_api_bp.get("/me")
def api_me():
    if not current_user.is_authenticated:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(current_user.to_public_dict()), 200