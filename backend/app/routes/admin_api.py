# app/routes/admin_api.py
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from app.extensions import db
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
    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()

    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    match_rows = (
        db.session.query(func.date(Match.timestamp), func.count())
        .group_by(func.date(Match.timestamp))
        .order_by(func.date(Match.timestamp))
        .all()
    )
    matches_over_time = [
        {"date": row[0].strftime("%Y-%m-%d"), "count": row[1]} for row in match_rows
    ]

    # Use correct capitalized status values from database
    in_custody = Inmate.query.filter_by(status="Incarcerated").count()
    released = Inmate.query.filter_by(status="Released").count()
    escaped = Inmate.query.filter(func.lower(Inmate.status) == 'escaped').count()
    inmate_status = [
        {"name": "Released", "value": released},
        {"name": "In Custody", "value": in_custody},
        {"name": "Escaped", "value": escaped},
    ]

    cameras = Camera.query.all()
    camera_labels = [c.name for c in cameras]
    camera_counts = [1 for _ in cameras]  # placeholder

    return jsonify(
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
    ), 200


# ─────────────────────────────────────────────
# Admin guard
# ─────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Not logged in → 401
        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 401

        # Logged in but not admin → 403
        if not bool(getattr(current_user, "is_admin", False)):
            return jsonify({"error": "Forbidden – admin only"}), 403

        return f(*args, **kwargs)

    return decorated_function


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
                    "id": u.id,
                    "name": getattr(u, "username", None) or u.email,
                    "email": u.email,
                    "is_admin": bool(getattr(u, "is_admin", False)),
                    "is_active": not bool(getattr(u, "is_suspended", False)),
                    "last_login": u.last_login.isoformat()
                    if getattr(u, "last_login", None)
                    else None,
                }
                for u in users
            ]
        }
    ), 200


# ─────────────────────────────────────────────
# Create user (admin only)
# POST /admin/api/users
# ─────────────────────────────────────────────
@admin_api_bp.route("/users", methods=["POST"])
@login_required
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    is_admin = bool(data.get("is_admin", False))

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    # Adjust these field names if your User model differs
    new_user = User(
        username=name,
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=is_admin,
        is_suspended=False,
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify(
        {
            "message": "User created successfully",
            "user": {
                "id": new_user.id,
                "name": getattr(new_user, "username", None) or new_user.email,
                "email": new_user.email,
                "is_admin": bool(getattr(new_user, "is_admin", False)),
                "is_active": not bool(getattr(new_user, "is_suspended", False)),
            },
        }
    ), 201


# ─────────────────────────────────────────────
# Update user (admin only)
# PUT /admin/api/users/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "name" in data:
        user.username = data["name"]

    if "email" in data:
        new_email = data["email"]
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != user_id:
            return jsonify({"error": "Email already exists"}), 400
        user.email = new_email

    if "password" in data and data["password"]:
        user.password_hash = generate_password_hash(data["password"])

    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])

    db.session.commit()

    return jsonify(
        {
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "name": getattr(user, "username", None) or user.email,
                "email": user.email,
                "is_admin": bool(getattr(user, "is_admin", False)),
                "is_active": not bool(getattr(user, "is_suspended", False)),
            },
        }
    ), 200


# ─────────────────────────────────────────────
# Toggle user status (activate/suspend)
# PUT /admin/api/users/<id>/toggle-status
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>/toggle-status", methods=["PUT"])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({"error": "You cannot suspend your own account"}), 400

    user.is_suspended = not bool(getattr(user, "is_suspended", False))
    db.session.commit()

    return jsonify(
        {
            "message": f'User {"activated" if not user.is_suspended else "suspended"} successfully',
            "is_active": not bool(user.is_suspended),
        }
    ), 200


# ─────────────────────────────────────────────
# Delete user (admin only)
# DELETE /admin/api/users/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted successfully"}), 200


# ─────────────────────────────────────────────
# Create inmate (all authenticated users)
# POST /admin/api/inmates
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates", methods=["POST"])
@login_required
def create_inmate():
    import os
    import uuid
    from datetime import datetime
    from werkzeug.utils import secure_filename

    # Handle multipart form data (with image upload)
    name = request.form.get("name")
    age = request.form.get("age")
    crime = request.form.get("crime")
    risk_level = request.form.get("riskLevel", "Medium")
    location = request.form.get("location")
    status = request.form.get("status", "Incarcerated")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    # Generate unique inmate ID
    inmate_id = f"CDJ-{uuid.uuid4().hex[:6].upper()}"
    while Inmate.query.filter_by(inmate_id=inmate_id).first():
        inmate_id = f"CDJ-{uuid.uuid4().hex[:6].upper()}"

    # Handle image upload
    mugshot_path = None
    face_encoding = None

    if "mugshot" in request.files:
        file = request.files["mugshot"]
        if file and file.filename:
            # Ensure upload directory exists
            upload_folder = os.path.join("app", "static", "inmate_images")
            os.makedirs(upload_folder, exist_ok=True)

            # Save file with unique name
            filename = secure_filename(file.filename)
            unique_filename = f"{inmate_id}_{filename}"
            save_path = os.path.join(upload_folder, unique_filename)
            file.save(save_path)
            mugshot_path = f"/static/inmate_images/{unique_filename}"

            # Extract FaceNet embedding for face recognition
            try:
                import cv2
                from app.utils.embedding_client import extract_embedding_from_frame

                img = cv2.imread(save_path)
                if img is not None:
                    # FaceNet works best with 160x160 but embedding service handles resizing
                    face_encoding = extract_embedding_from_frame(img)
                    if face_encoding is not None:
                        print(f"[create_inmate] Successfully extracted FaceNet embedding with {len(face_encoding)} features")
                    else:
                        print("[create_inmate] Warning: Embedding service returned None. Is it running on port 5001?")
            except Exception as e:
                print(f"[create_inmate] Error extracting face encoding: {e}")
                import traceback
                traceback.print_exc()
                # Continue without face encoding - it can be added later

    if not mugshot_path:
        return jsonify({"error": "Mugshot image is required"}), 400

    # Create inmate record
    inmate = Inmate(
        inmate_id=inmate_id,
        name=name,
        mugshot_path=mugshot_path,
        age=int(age) if age else None,
        crime=crime,
        risk_level=risk_level,
        location=location,
        status=status,
        face_encoding=face_encoding,
        registered_by=current_user.id,
        created_at=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )

    db.session.add(inmate)
    db.session.commit()

    return jsonify({
        "message": "Inmate created successfully",
        "inmate": inmate.to_dict()
    }), 201


# ─────────────────────────────────────────────
# List inmates (all authenticated users)
# GET /admin/api/inmates
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates", methods=["GET"])
@login_required
def get_inmates():
    inmates = Inmate.query.order_by(Inmate.created_at.desc()).all()
    return jsonify({
        "inmates": [inmate.to_dict() for inmate in inmates]
    }), 200


# ─────────────────────────────────────────────
# Get escaped inmates with locations (for map)
# GET /admin/api/inmates/escaped
# NOTE: This route MUST be defined BEFORE /inmates/<int:inmate_id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates/escaped", methods=["GET"])
@login_required
def get_escaped_inmates():
    # Use case-insensitive query to handle both "Escaped" and "escaped"
    escaped = Inmate.query.filter(
        func.lower(Inmate.status) == 'escaped'
    ).all()
    return jsonify({
        "inmates": [inmate.to_dict() for inmate in escaped]
    }), 200


# ─────────────────────────────────────────────
# Get single inmate (all authenticated users)
# GET /admin/api/inmates/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates/<int:inmate_id>", methods=["GET"])
@login_required
def get_inmate(inmate_id):
    inmate = Inmate.query.get_or_404(inmate_id)
    return jsonify({"inmate": inmate.to_dict()}), 200


# ─────────────────────────────────────────────
# Update inmate (registrant or admin only)
# PUT /admin/api/inmates/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates/<int:inmate_id>", methods=["PUT"])
@login_required
def update_inmate(inmate_id):
    from datetime import datetime

    inmate = Inmate.query.get_or_404(inmate_id)

    # Permission check: only admin OR the registrant can edit
    if not current_user.is_admin and inmate.registered_by != current_user.id:
        return jsonify({"error": "You can only edit inmates you registered"}), 403

    data = request.get_json(silent=True) or {}

    if "name" in data:
        inmate.name = data["name"]
    if "age" in data:
        inmate.age = data["age"]
    if "status" in data:
        old_status = inmate.status
        inmate.status = data["status"]
        # If status changed to Escaped, set escape date
        if data["status"] == "Escaped" and old_status != "Escaped":
            inmate.escape_date = datetime.utcnow()
    if "location" in data:
        inmate.location = data["location"]
    if "crime" in data:
        inmate.crime = data["crime"]
    if "riskLevel" in data:
        inmate.risk_level = data["riskLevel"]
    # Handle escape location fields
    if "escapeLatitude" in data:
        inmate.escape_latitude = data["escapeLatitude"]
    if "escapeLongitude" in data:
        inmate.escape_longitude = data["escapeLongitude"]

    db.session.commit()

    return jsonify({
        "message": "Inmate updated successfully",
        "inmate": inmate.to_dict()
    }), 200


# ─────────────────────────────────────────────
# Delete inmate (admin only)
# DELETE /admin/api/inmates/<id>
# ─────────────────────────────────────────────
@admin_api_bp.route("/inmates/<int:inmate_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_inmate(inmate_id):
    inmate = Inmate.query.get_or_404(inmate_id)
    db.session.delete(inmate)
    db.session.commit()

    return jsonify({"message": "Inmate deleted successfully"}), 200