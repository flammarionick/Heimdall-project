# app/routes/admin_dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match
from sqlalchemy import func
from app import db

admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


@admin_dashboard_bp.route('/dashboard')
@login_required
def dashboard_view():
    """
    Server-rendered admin dashboard (keeps existing Jinja template behavior).
    """
    if not current_user.is_admin:
        return "Unauthorized", 403

    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()

    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    # Chart data (match counts by day)
    match_data = (
        db.session.query(func.date(Match.timestamp), func.count())
        .group_by(func.date(Match.timestamp))
        .order_by(func.date(Match.timestamp))
        .all()
    )
    match_labels = [str(row[0]) for row in match_data]
    match_counts = [row[1] for row in match_data]

    # Inmate status counts
    in_custody = Inmate.query.filter_by(status='in_custody').count()
    released = Inmate.query.filter_by(status='released').count()
    inmate_status_counts = [released, in_custody]

    # Dummy camera labels (replace with real camera data if needed)
    camera_labels = [camera.name for camera in Camera.query.all()]
    camera_counts = [1 for _ in camera_labels]  # Placeholder count data

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        suspended_users=suspended_users,
        total_cameras=total_cameras,
        total_alerts=total_alerts,
        total_inmates=total_inmates,
        match_labels=match_labels,
        match_counts=match_counts,
        inmate_status_counts=inmate_status_counts,
        camera_labels=camera_labels,
        camera_counts=camera_counts
    )


@admin_dashboard_bp.route('/api/stats')
@login_required
def dashboard_stats():
    """
    JSON API endpoint for the React frontend to fetch live dashboard stats.
    Returns: {
      total_users, active_users, suspended_users,
      total_cameras, total_alerts, total_inmates,
      matches_over_time: [{date, count}, ...],
      inmate_status: [{name, value}, ...],
      camera_labels, camera_counts
    }
    """
    if not current_user.is_admin:
        return jsonify({"error": "unauthorized"}), 403

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
    matches_over_time = [{"date": str(r[0]), "count": r[1]} for r in match_rows]

    in_custody = Inmate.query.filter_by(status='in_custody').count()
    released = Inmate.query.filter_by(status='released').count()
    inmate_status = [
        {"name": "Released", "value": released},
        {"name": "In Custody", "value": in_custody},
    ]

    camera_rows = Camera.query.all()
    camera_labels = [c.name for c in camera_rows]
    camera_counts = [1 for _ in camera_rows]

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "suspended_users": suspended_users,
        "total_cameras": total_cameras,
        "total_alerts": total_alerts,
        "total_inmates": total_inmates,
        "matches_over_time": matches_over_time,
        "inmate_status": inmate_status,
        "camera_labels": camera_labels,
        "camera_counts": camera_counts
    })