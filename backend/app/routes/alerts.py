# app/routes/alerts.py
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from app.extensions import db
from app.models.alert import Alert
from app.utils.auth_helpers import login_or_jwt_required

alerts_api_bp = Blueprint('alerts_api', __name__, url_prefix='/api/alerts')
alerts_page_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

# =====================
# 🔔 API ROUTES
# =====================

@alerts_api_bp.route('/', methods=['GET'])
@login_or_jwt_required
def get_alerts():
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    return jsonify([
        {
            'id': a.id,
            'message': a.message,
            'level': a.level,
            'timestamp': a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'resolved': a.resolved,
            'inmate_id': a.inmate_id,
            'camera_id': a.camera_id,
            'confidence': a.confidence
        }
        for a in alerts
    ])

@alerts_api_bp.route('/', methods=['POST'])
@login_or_jwt_required
def create_alert():
    data = request.json
    alert = Alert(
        message=data.get('message'),
        level=data.get('level', 'info'),
        inmate_id=data.get('inmate_id'),
        camera_id=data.get('camera_id'),
        confidence=data.get('confidence')
    )
    db.session.add(alert)
    db.session.commit()

    # Emit real-time alert via Socket.IO
    from app import socketio
    socketio.emit('new_alert', {
        'id': alert.id,
        'message': alert.message,
        'level': alert.level,
        'timestamp': alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'resolved': alert.resolved,
        'inmate_id': alert.inmate_id,
        'camera_id': alert.camera_id,
        'confidence': alert.confidence
    })

    return jsonify({'status': 'created', 'id': alert.id}), 201

@alerts_api_bp.route('/<int:alert_id>/resolve', methods=['POST'])
@login_or_jwt_required
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.resolved = True
    db.session.commit()
    return jsonify({'status': 'resolved'})


# =====================
# 📄 HTML PAGE ROUTE
# =====================

@alerts_page_bp.route('/')
@login_required
def alerts_home():
    return render_template('alerts/index.html', title='Alerts & Logs')
