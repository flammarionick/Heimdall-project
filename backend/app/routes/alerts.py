# app/routes/alerts.py
from flask import Blueprint, jsonify, request
from app import db
from app.models.alert import Alert

alerts_bp = Blueprint('alerts_api', __name__, url_prefix='/api/alerts')

@alerts_bp.route('/', methods=['GET'])
def get_alerts():
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    return jsonify([{
        'id': a.id,
        'message': a.message,
        'level': a.level,
        'timestamp': a.timestamp.isoformat(),
        'resolved': a.resolved,
        'inmate_id': a.inmate_id
    } for a in alerts])

@alerts_bp.route('/', methods=['POST'])
def create_alert():
    data = request.json
    alert = Alert(
        message=data.get('message'),
        level=data.get('level', 'info'),
        inmate_id=data.get('inmate_id')  # you mentioned re-adding this
    )
    db.session.add(alert)
    db.session.commit()

    # Emit real-time alert via Socket.IO
    from run import socketio
    socketio.emit('new_alert', {
        'id': alert.id,
        'message': alert.message,
        'level': alert.level,
        'timestamp': alert.timestamp.isoformat(),
        'inmate_id': alert.inmate_id
    })

    return jsonify({'status': 'created', 'id': alert.id}), 201

@alerts_bp.route('/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.resolved = True
    db.session.commit()
    return jsonify({'status': 'resolved'})
