# app/routes/api_auth.py
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required

from app.extensions import db
from app.models.user import User

api_auth_bp = Blueprint("api_auth", __name__, url_prefix="/auth/api")


@api_auth_bp.route("/login", methods=["POST"])
def api_login():
    """
    JSON login endpoint for the React frontend.
    Body:
    {
      "email": "...",
      "password": "..."
    }
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    if getattr(user, "is_suspended", False):
        return jsonify({"error": "Account is suspended"}), 403

    login_user(user)

    # Record last_login if your model has it
    if hasattr(user, "last_login"):
        from datetime import datetime

        user.last_login = datetime.utcnow()
        db.session.commit()

    return jsonify(
        {
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": bool(getattr(user, "is_admin", False)),
                "is_suspended": bool(getattr(user, "is_suspended", False)),
            },
            "role": "admin" if getattr(user, "is_admin", False) else "user",
        }
    ), 200


@api_auth_bp.route("/me", methods=["GET"])
@login_required
def api_me():
    """
    Return current logged-in user as JSON.
    Used by React (e.g. Manage Users) to check session and role.
    """
    user = current_user

    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": bool(getattr(user, "is_admin", False)),
            "is_suspended": bool(getattr(user, "is_suspended", False)),
        }
    ), 200


@api_auth_bp.route("/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200