# app/routes/admin_api.py

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from app import db
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/admin/api")


# ─────────────────────────────────────────────
# Public stats endpoint for React dashboard
# ─────────────────────────────────────────────
@admin_api_bp.route("/stats2", methods=["GET"])
def stats2():
    """
    Public stats endpoint (no login/role checks) so the React Admin
    Dashboard can load analytics without 401s while you finish the UI.
    """

    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()

    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    # Matches over time (for line chart)
    match_rows = (
        db.session.query(func.date(Match.timestamp), func.count())
        .group_by(func.date(Match.timestamp))
        .order_by(func.date(Match.timestamp))
        .all()
    )
    matches_over_time = [
        {"date": row[0].strftime("%Y-%m-%d"), "count": row[1]} for row in match_rows
    ]

    # Inmate status distribution (for pie chart)
    in_custody = Inmate.query.filter_by(status="in_custody").count()
    released = Inmate.query.filter_by(status="released").count()
    inmate_status = [
        {"name": "Released", "value": released},
        {"name": "In Custody", "value": in_custody},
    ]

    # Simple camera stats – labels & counts (placeholder counts = 1)
    cameras = Camera.query.all()
    camera_labels = [c.name for c in cameras]
    camera_counts = [1 for _ in cameras]

    return (
        jsonify(
            {
                "total_users": total_users,
                "active_users": active_users,
                "suspended_users": suspended_users,
                "total_cameras": total_cameras,
                "total_alerts": total_alerts,
                "total_inmates": total_inmates,
                "matches_over_time": matches_over_time,
                "inmate_status": inmate_status,
                "camera_labels": camera_labels,
                "camera_counts": camera_counts,
            }
        ),
        200,
    )


# ─────────────────────────────────────────────
# Admin guard
# ─────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Not logged in at all → 401
        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 401

        # Logged in but not admin → 403
        if not getattr(current_user, "is_admin", False):
            return jsonify({"error": "Forbidden – admin only"}), 403

        return f(*args, **kwargs)

    return decorated_function


# NOTE:
# /auth/api/me (who-am-I endpoint) MUST stay in app.routes.api_auth
# with prefix `/auth/api`. Do NOT define it again here or it will
# become /admin/api/auth/api/me and the frontend calls won’t match.


# ─────────────────────────────────────────────
# List users (admin only)
# GET /admin/api/users
# ─────────────────────────────────────────────
@admin_api_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def get_users():
    users = User.query.all()
    return jsonify(
        {
            "users": [
                {
                    "id": user.id,
                    # Frontend expects "name"
                    "name": getattr(user, "username", None) or user.email,
                    "email": user.email,
                    "is_admin": bool(user.is_admin),
                    # Frontend expects is_active – derived from !is_suspended
                    "is_active": not bool(getattr(user, "is_suspended", False)),
                    "last_login": user.last_login.isoformat()
                    if getattr(user, "last_login", None)
                    else None,
                }
                for user in users
            ]
        }
    )


# ─────────────────────────────────────────────
# Create user (admin only)
# POST /admin/api/users
# body: { name, email, password, is_admin? }
# ─────────────────────────────────────────────
@admin_api_bp.route("/users", methods=["POST"])
@login_required
@admin_required
def create_user():
    data = request.get_json() or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    is_admin = bool(data.get("is_admin", False))

    if not name or not email or not password:
        return (
            jsonify({"error": "Name, email, and password are required"}),
            400,
        )

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    new_user = User(
        username=name,  # map "name" from UI to username field
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
        is_suspended=False,
    )

    db.session.add(new_user)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "User created successfully",
                "user": {
                    "id": new_user.id,
                    "name": new_user.username,
                    "email": new_user.email,
                    "is_admin": bool(new_user.is_admin),
                    "is_active": not bool(new_user.is_suspended),
                },
            }
        ),
        201,
    )


# ─────────────────────────────────────────────
# Update user (admin only)
# PUT /admin/api/users/<id>
# body: { name?, email?, password?, is_admin? }
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    # Update name -> username
    if "name" in data:
        user.username = data["name"]

    # Update email with uniqueness check
    if "email" in data:
        new_email = data["email"]
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != user_id:
            return jsonify({"error": "Email already exists"}), 400
        user.email = new_email

    # Update password if provided (non-empty)
    if "password" in data and data["password"]:
        user.password_hash = generate_password_hash(data["password"])

    # Update admin flag
    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])

    db.session.commit()

    return jsonify(
        {
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "name": user.username,
                "email": user.email,
                "is_admin": bool(user.is_admin),
                "is_active": not bool(user.is_suspended),
            },
        }
    )


# ─────────────────────────────────────────────
# Toggle user status (activate/suspend)
# PUT /admin/api/users/<id>/toggle-status
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>/toggle-status", methods=["PUT"])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent admin from suspending themselves
    if user.id == current_user.id:
        return (
            jsonify({"error": "You cannot suspend your own account"}),
            400,
        )

    # Flip is_suspended flag
    user.is_suspended = not bool(user.is_suspended)
    db.session.commit()

    return jsonify(
        {
            "message": f'User {"activated" if not user.is_suspended else "suspended"} successfully',
            "is_active": not bool(user.is_suspended),
        }
    )


# ─────────────────────────────────────────────
# Delete user (admin only)
# DELETE /admin/api/users/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        return (
            jsonify({"error": "You cannot delete your own account"}),
            400,
        )

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted successfully"})