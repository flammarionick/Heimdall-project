from flask import Blueprint, jsonify
from app import socketio
from datetime import datetime

api_alert = Blueprint('api_alert', __name__, url_prefix='/api')

@api_alert.route('/test-alert', methods=['GET'])
def test_alert():
    alert_data = {
        'message': 'Test alert from backend!',
        'level': 'info',
        'timestamp': datetime.utcnow().isoformat()
    }
    socketio.emit('new_alert', alert_data)
    return jsonify({"status": "emitted", "data": alert_data})
