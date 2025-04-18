from flask import Blueprint
from flask_login import login_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def settings_home():
    return "<h3>Settings Page Coming Soon</h3>"
