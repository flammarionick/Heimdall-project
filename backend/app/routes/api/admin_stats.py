from flask import Blueprint, jsonify
from app.models.user import User
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.camera import Camera
from sqlalchemy import func
from app.extensions import db

admin_stats_api = Blueprint('admin_stats_api', __name__, url_prefix='/api/admin')

@admin_stats_api.route('/dashboard-stats')
def dashboard_stats():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_suspended=False).count()
    suspended_users = User.query.filter_by(is_suspended=True).count()
    total_cameras = Camera.query.count()
    total_alerts = Alert.query.count()
    total_inmates = Inmate.query.count()

    match_stats = db.session.query(
        func.strftime('%Y-%m-%d', Alert.timestamp).label('date'),
        func.count(Alert.id)
    ).group_by('date').all()

    status_stats = db.session.query(
        Inmate.status,
        func.count(Inmate.id)
    ).group_by(Inmate.status).all()

    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'total_cameras': total_cameras,
        'total_alerts': total_alerts,
        'total_inmates': total_inmates,
        'matches_over_time': [{'date': date, 'count': count} for date, count in match_stats],
        'inmate_status_counts': {status: count for status, count in status_stats}
    })
