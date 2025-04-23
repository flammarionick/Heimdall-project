# backend/app/routes/alerts.py
from flask import Blueprint, render_template, request, redirect, url_for
from app import db
from app.models.alert import Alert

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')

@alerts_bp.route('/')
def view_alerts():
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    return render_template('alerts/index.html', alerts=alerts)

@alerts_bp.route('/resolve/<int:alert_id>', methods=['POST'])
def resolve_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.resolved = True
    db.session.commit()
    return redirect(url_for('alerts.view_alerts'))
