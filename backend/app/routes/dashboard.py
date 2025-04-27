from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.alert import Alert
import base64
import cv2
import numpy as np

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# 📍 This is now handled in frontend JS — OpenCV should not grab webcam here

@dashboard_bp.route('/')
@login_required
def view_dashboard():
    print(f"Dashboard: current_user.is_authenticated = {current_user.is_authenticated}")
    return render_template('dashboard/dashboard.html')


@dashboard_bp.route('/analytics')
@login_required
def dashboard_analytics():
    return render_template('dashboard/analytics.html')


@dashboard_bp.route('/api/analytics')
@login_required
def analytics_data():
    total_alerts = Alert.query.count()
    unique_inmates = db.session.query(Alert.inmate_id).distinct().count()

    alerts_by_camera = db.session.query(
        Alert.camera_id, func.count(Alert.id)
    ).group_by(Alert.camera_id).all()
    camera_data = [{"camera_id": cam_id, "count": count} for cam_id, count in alerts_by_camera]

    today = datetime.utcnow()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    daily_data = []
    for day in last_7_days:
        next_day = day + timedelta(days=1)
        count = Alert.query.filter(Alert.timestamp >= day, Alert.timestamp < next_day).count()
        daily_data.append({
            "date": day.strftime("%b %d"),
            "count": count
        })

    return jsonify({
        "total_alerts": total_alerts,
        "unique_faces": unique_inmates,
        "daily_data": daily_data,
        "camera_data": camera_data
    })


