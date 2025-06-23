# app/routes/admin_dashboard.py
from flask import Blueprint, render_template
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
    if not current_user.is_admin:
        return "Unauthorized", 403

    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()

    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    # Chart data
    match_data = db.session.query(func.date(Match.timestamp), func.count()).group_by(func.date(Match.timestamp)).all()
    match_labels = [str(row[0]) for row in match_data]
    match_counts = [row[1] for row in match_data]

    # Inmate status
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
