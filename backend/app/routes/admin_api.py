# app/routes/admin_api.py
from flask import Blueprint, jsonify
from sqlalchemy import func

from app import db
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/admin/api")


# ─────────────────────────────────────────────────────────
# ORIGINAL PROTECTED ENDPOINT (kept here for later, not used by React now)
# ─────────────────────────────────────────────────────────
"""
from flask_login import login_required, current_user

@admin_api_bp.route("/stats", methods=["GET"])
@login_required
def stats():
    # Only admins should see this
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

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
    )
"""


# ─────────────────────────────────────────────────────────
# NEW UNPROTECTED ENDPOINT USED BY REACT DASHBOARD
# ─────────────────────────────────────────────────────────
@admin_api_bp.route("/stats2", methods=["GET"])
def stats2():
    """
    Public stats endpoint (no login/role checks) so the React Admin
    Dashboard can load analytics without 401 while you finish the UI.

    Later, once everything works, you can:
      - Switch the frontend back to /admin/api/stats, and
      - Re-enable @login_required + admin checks there.
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
        {"date": row[0].strftime("%Y-%m-%d"), "count": row[1]}
        for row in match_rows
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