# app/routes/admin_api.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match
from sqlalchemy import func

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

@admin_api_bp.route('/stats', methods=['GET'])
@login_required
def admin_stats():
    # only allow admins
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "unauthorized"}), 403

    # Basic counts
    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()
    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    # Matches by date (last 90 days)
    match_q = (db.session.query(func.date(Match.timestamp).label("date"), func.count().label("count"))
               .group_by(func.date(Match.timestamp))
               .order_by(func.date(Match.timestamp).desc())
               .limit(90))
    matches = [{"date": str(r.date), "count": int(r.count)} for r in match_q.all()]

    # Inmate status counts
    in_custody = Inmate.query.filter_by(status='in_custody').count()
    released = Inmate.query.filter_by(status='released').count()

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "total_cameras": total_cameras,
        "total_alerts": total_alerts,
        "total_inmates": total_inmates,
        "matches_over_time": matches,  # list of {date, count}
        "inmate_status": [
            {"name": "In custody", "value": in_custody},
            {"name": "Released", "value": released}
        ]
    })