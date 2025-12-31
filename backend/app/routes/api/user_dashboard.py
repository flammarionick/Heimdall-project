# backend/app/routes/api/user_dashboard.py
"""
User Dashboard API - provides stats, activity, and system health for regular users.
"""

import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from app.extensions import db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.match import Match
from app.models.inmate import Inmate

user_dashboard_bp = Blueprint('user_dashboard_api', __name__, url_prefix='/api/user')


@user_dashboard_bp.route('/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get dashboard statistics for the current user."""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # Today's matches count
    today_matches = Match.query.filter(Match.timestamp >= today_start).count()

    # Active (unresolved) alerts count
    active_alerts = Alert.query.filter_by(resolved=False).count()

    # Active cameras count
    active_cameras = Camera.query.filter_by(status=True).count()
    total_cameras = Camera.query.count()

    # Total inmates
    total_inmates = Inmate.query.count()

    # Calculate camera uptime percentage
    camera_uptime = (active_cameras / total_cameras * 100) if total_cameras > 0 else 100.0

    # System status based on weighted alert scoring
    # danger = 10 points, warning = 3 points, info = 1 point
    danger_alerts = Alert.query.filter_by(resolved=False, level='danger').count()
    warning_alerts = Alert.query.filter_by(resolved=False, level='warning').count()
    info_alerts = Alert.query.filter_by(resolved=False, level='info').count()

    alert_score = (danger_alerts * 10) + (warning_alerts * 3) + (info_alerts * 1)

    # Critical: score >= 20 (e.g., 2+ danger alerts, or 1 danger + 4 warnings)
    # Warning: score 5-19 (e.g., 1 danger, or 2 warnings)
    # Operational: score < 5
    if alert_score >= 20:
        system_status = 'critical'
    elif alert_score >= 5:
        system_status = 'warning'
    else:
        system_status = 'operational'

    return jsonify({
        'today_matches': today_matches,
        'active_alerts': active_alerts,
        'active_cameras': active_cameras,
        'total_cameras': total_cameras,
        'total_inmates': total_inmates,
        'system_status': system_status,
        'camera_uptime': round(camera_uptime, 1),
    })


@user_dashboard_bp.route('/activity', methods=['GET'])
@login_required
def get_recent_activity():
    """Get recent activity (alerts, matches) for the dashboard."""
    # Get recent alerts (last 20)
    recent_alerts = Alert.query.order_by(desc(Alert.timestamp)).limit(20).all()

    # Get recent matches (last 20)
    recent_matches = Match.query.order_by(desc(Match.timestamp)).limit(20).all()

    # Combine and format activity
    activity = []

    for alert in recent_alerts:
        # Get related inmate name if available
        inmate_name = None
        if alert.inmate_id:
            inmate = Inmate.query.get(alert.inmate_id)
            if inmate:
                inmate_name = inmate.name

        # Get camera name if available
        camera_name = None
        if alert.camera_id:
            camera = Camera.query.get(alert.camera_id)
            if camera:
                camera_name = camera.name

        activity.append({
            'id': f'alert-{alert.id}',
            'type': 'alert',
            'message': alert.message or f'Alert: {alert.level}',
            'level': 'success' if alert.resolved else ('warning' if alert.level == 'warning' else 'danger' if alert.level == 'danger' else 'info'),
            'timestamp': alert.timestamp.isoformat() if alert.timestamp else None,
            'time': format_time_ago(alert.timestamp),
            'resolved': alert.resolved,
            'inmate_name': inmate_name,
            'camera_name': camera_name,
        })

    for match in recent_matches:
        inmate = Inmate.query.get(match.inmate_id) if match.inmate_id else None
        activity.append({
            'id': f'match-{match.id}',
            'type': 'match',
            'message': f'Match detected: {inmate.name if inmate else "Unknown"}',
            'level': 'warning',
            'timestamp': match.timestamp.isoformat() if match.timestamp else None,
            'time': format_time_ago(match.timestamp),
            'inmate_name': inmate.name if inmate else None,
        })

    # Sort by timestamp descending
    activity.sort(key=lambda x: x['timestamp'] or '', reverse=True)

    # Return top 10
    return jsonify({
        'activity': activity[:10],
        'total_count': len(activity),
    })


@user_dashboard_bp.route('/health', methods=['GET'])
@login_required
def get_system_health():
    """Get system health metrics."""
    # Camera statistics
    total_cameras = Camera.query.count()
    active_cameras = Camera.query.filter_by(status=True).count()
    camera_uptime = (active_cameras / total_cameras * 100) if total_cameras > 0 else 100.0

    # Alert statistics (last 24 hours)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    alerts_24h = Alert.query.filter(Alert.timestamp >= last_24h).count()
    resolved_24h = Alert.query.filter(Alert.timestamp >= last_24h, Alert.resolved == True).count()
    resolution_rate = (resolved_24h / alerts_24h * 100) if alerts_24h > 0 else 100.0

    # Match statistics (last 24 hours)
    matches_24h = Match.query.filter(Match.timestamp >= last_24h).count()

    # Calculate REAL average response time by measuring DB query performance
    start_time = time.time()
    db.session.execute(db.text('SELECT COUNT(*) FROM alert'))
    avg_response_time = round(time.time() - start_time, 3)

    # Calculate REAL recognition accuracy from actual Alert confidence scores
    alerts_with_confidence = Alert.query.filter(
        Alert.timestamp >= last_24h,
        Alert.confidence.isnot(None)
    ).all()

    if alerts_with_confidence:
        total_confidence = sum(a.confidence for a in alerts_with_confidence)
        recognition_accuracy = round(total_confidence / len(alerts_with_confidence), 1)
    else:
        recognition_accuracy = 0.0  # No recognition data in last 24h

    # Database health check
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception:
        db_status = 'unhealthy'

    # System status based on weighted alert scoring (same logic as /stats)
    danger_alerts = Alert.query.filter_by(resolved=False, level='danger').count()
    warning_alerts = Alert.query.filter_by(resolved=False, level='warning').count()
    info_alerts = Alert.query.filter_by(resolved=False, level='info').count()
    alert_score = (danger_alerts * 10) + (warning_alerts * 3) + (info_alerts * 1)

    if alert_score >= 20:
        system_status = 'critical'
    elif alert_score >= 5:
        system_status = 'warning'
    else:
        system_status = 'operational'

    return jsonify({
        'camera_uptime': round(camera_uptime, 1),
        'recognition_accuracy': round(recognition_accuracy, 1),
        'avg_response_time': round(avg_response_time, 2),
        'resolution_rate': round(resolution_rate, 1),
        'alerts_24h': alerts_24h,
        'matches_24h': matches_24h,
        'db_status': db_status,
        'active_cameras': active_cameras,
        'total_cameras': total_cameras,
        'system_status': system_status,
        'alert_score': alert_score,
    })


def format_time_ago(dt):
    """Format a datetime as a human-readable 'time ago' string."""
    if not dt:
        return 'Unknown'

    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f'{mins} min{"s" if mins != 1 else ""} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} day{"s" if days != 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')
