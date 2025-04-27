# app/routes/admin.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import User, Inmate, Camera, Alert

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        abort(403)  # Forbidden if not admin

    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(suspended=False).count(),
        'suspended_users': User.query.filter_by(suspended=True).count(),
        'total_inmates': Inmate.query.count(),
        'total_cameras': Camera.query.count(),
        'total_alerts': Alert.query.count(),
        'total_matches': Alert.query.filter(Alert.level == 'match').count()
    }
    return render_template('admin/dashboard.html', stats=stats)
