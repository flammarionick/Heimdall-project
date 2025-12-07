# app/routes/admin_api.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/admin/api")


@admin_api_bp.route("/stats", methods=["GET"])
@login_required
def stats():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "forbidden"}), 403

    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(is_suspended=False).count()
        suspended_users = User.query.filter_by(is_suspended=True).count()

        total_cameras = Camera.query.count()
        total_alerts = Alert.query.count()
        total_inmates = Inmate.query.count()

        # Matches over time (daily)
        match_data = (
            db.session.query(func.date(Match.timestamp), func.count())
            .group_by(func.date(Match.timestamp))
            .order_by(func.date(Match.timestamp))
            .all()
        )
        matches_over_time = [
            {"date": str(row[0]), "count": row[1]} for row in match_data
        ]

        # Inmate status distribution
        in_custody = Inmate.query.filter_by(status="in_custody").count()
        released = Inmate.query.filter_by(status="released").count()
        inmate_status = [
            {"name": "Active", "value": in_custody},
            {"name": "Released", "value": released},
        ]

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
            }
        )
    except Exception as e:
        # Fallback so React still gets JSON
        return jsonify({"error": "internal_error", "details": str(e)}), 500